package main

import (
	"bufio"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.elastic.co/apm/module/apmhttp/v2"
	"go.elastic.co/apm/v2"
	"errors"
)

var (
	startTime     time.Time
	loginHits     int
	loginHitsMu   sync.Mutex
	users         map[string][]string
	httpRequests  = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"path", "status"},
	)
)

func init() {
	startTime = time.Now()
	users = make(map[string][]string)
	loadUsers("users.txt")
}

func loadUsers(filename string) {
	file, err := os.Open(filename)
	if err != nil {
		log.Printf("Warning: failed to open %s: %v", filename, err)
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) == 2 {
			users[strings.TrimSpace(parts[0])] = append(users[strings.TrimSpace(parts[0])], strings.TrimSpace(parts[1]))
		}
	}
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	loginHitsMu.Lock()
	loginHits++
	loginHitsMu.Unlock()

	if r.Method == "GET" {
		httpRequests.WithLabelValues("/login", "200").Inc()
		renderLogin(w, "")
		return
	}

	if r.Method == "POST" {
		if err := r.ParseForm(); err != nil {
			http.Error(w, "Bad Request", http.StatusBadRequest)
			return
		}
		username := r.FormValue("username")
		password := r.FormValue("password")

		// Intentionally injected bug: Trigger 500 error if password contains "!"
		if strings.Contains(password, "!") {
			errMsg := fmt.Sprintf("FATAL: Unexpected character '!' in password processing for user '%s' (simulated bug)", username)
			log.Printf(errMsg)
			
			// Explicitly capture the error so it shows up in APM traces
			e := apm.CaptureError(r.Context(), errors.New(errMsg))
			e.Send()

			httpRequests.WithLabelValues("/login", "500").Inc()
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
			return
		}

		expectedPasswords, ok := users[username]
		isValid := false
		if ok {
			for _, expectedPassword := range expectedPasswords {
				if password == expectedPassword {
					isValid = true
					break
				}
			}
		}

		if isValid {
			log.Printf("Login event: SUCCESS for user '%s'", username)
			httpRequests.WithLabelValues("/login", "302").Inc()
			http.Redirect(w, r, "/dashboard", http.StatusFound)
			return
		}
		
		log.Printf("Login event: FAILED for user '%s' (Invalid password or user not found)", username)
		httpRequests.WithLabelValues("/login", "401").Inc()
		w.WriteHeader(http.StatusUnauthorized)
		renderLogin(w, "Invalid username or password.")
		return
	}
    
	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func dashboardHandler(w http.ResponseWriter, r *http.Request) {
	httpRequests.WithLabelValues("/dashboard", "200").Inc()
	uptime := time.Since(startTime)
	
	loginHitsMu.Lock()
	hits := loginHits
	loginHitsMu.Unlock()

	w.Header().Set("Content-Type", "text/html")
	fmt.Fprintf(w, `
		<html>
		<head><title>Dashboard</title></head>
		<body style="font-family: sans-serif; padding: 2rem; background: #f9fafb;">
			<div style="max-width: 600px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
				<h2 style="color: #111827;">System Dashboard</h2>
				<p><strong>System Uptime:</strong> %s</p>
				<p><strong>Total Hits to Login Page:</strong> %d</p>
				<hr style="margin: 2rem 0; border: none; border-top: 1px solid #e5e7eb;" />
				<a href="/login" style="color: #2563eb; text-decoration: none;">&larr; Back to Login</a>
			</div>
		</body>
		</html>
	`, uptime.Round(time.Second), hits)
}

func renderLogin(w http.ResponseWriter, errorMsg string) {
	w.Header().Set("Content-Type", "text/html")
	html := `
		<html>
		<head><title>Login</title></head>
		<body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f3f4f6; margin: 0;">
			<div style="background: white; border: 1px solid #e5e7eb; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 320px;">
				<h2 style="margin-top: 0; color: #111827;">Sign In</h2>
				{{if .Error}}<p style="color: #dc2626; background: #fef2f2; padding: 0.5rem; border-radius: 4px; font-size: 0.875rem;">{{.Error}}</p>{{end}}
				<form method="POST" action="/login" style="margin: 0;">
					<div style="margin-bottom: 1rem;">
						<label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; color: #374151;">Username</label>
						<input type="text" name="username" required style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px; box-sizing: border-box;" />
					</div>
					<div style="margin-bottom: 1.5rem;">
						<label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; color: #374151;">Password</label>
						<input type="password" name="password" required style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px; box-sizing: border-box;" />
					</div>
					<button type="submit" style="width: 100%; background: #2563eb; color: white; border: none; padding: 0.75rem; border-radius: 4px; cursor: pointer; font-weight: bold;">Login</button>
				</form>
			</div>
		</body>
		</html>
	`
	tmpl, _ := template.New("login").Parse(html)
	tmpl.Execute(w, struct{ Error string }{errorMsg})
}

func main() {
	mux := http.NewServeMux()
	
	mux.HandleFunc("/login", loginHandler)
	mux.HandleFunc("/dashboard", dashboardHandler)
	mux.Handle("/metrics", promhttp.Handler())
	
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			httpRequests.WithLabelValues(r.URL.Path, "404").Inc()
			http.NotFound(w, r)
			return
		}
		http.Redirect(w, r, "/login", http.StatusFound)
	})

	// Wrap handlers with Elastic APM
	handler := apmhttp.Wrap(mux)

	port := "8080"
	log.Printf("Server listening on :%s", port)
	if err := http.ListenAndServe(":"+port, handler); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
