import subprocess
import json
import http.server
import socketserver
import os

PORT = 8081

def generate_report():
    print("Generating Premium Grype/Syft SAST report...")
    try:
        # Get all running container images
        result = subprocess.run(["docker", "ps", "--format", "{{.Image}}"], capture_output=True, text=True)
        images = result.stdout.strip().split("\n")
        images = list(set([img for img in images if img]))
        
        all_cves = []
        
        for img in images:
            print(f"Scanning image: {img}...")
            # Step 1: Use Syft to generate SBOM
            sbom_file = f"sbom_{img.replace('/', '_').replace(':', '_')}.json"
            subprocess.run(["syft", img, "-o", f"cyclonedx-json={sbom_file}", "-q"], capture_output=True)
            
            # Step 2: Use Grype to scan the SBOM
            if os.path.exists(sbom_file):
                scan = subprocess.run(["grype", f"sbom:{sbom_file}", "-o", "json", "-q"], capture_output=True, text=True)
                try:
                    if scan.stdout:
                        data = json.loads(scan.stdout)
                        for match in data.get("matches", []):
                            vuln = match.get("vulnerability", {})
                            artifact = match.get("artifact", {})
                            # Filter only High and Critical
                            if vuln.get("severity") in ["Critical", "High"]:
                                all_cves.append({
                                    "image": img,
                                    "id": vuln.get("id"),
                                    "severity": vuln.get("severity"),
                                    "package": artifact.get("name"),
                                    "version": artifact.get("version")
                                })
                except Exception as e:
                    print(f"Error parsing grype output for {img}: {e}")
                
                # Cleanup SBOM file
                try:
                    os.remove(sbom_file)
                except:
                    pass

        # Sort CVEs by severity (Critical first)
        severity_order = {"Critical": 0, "High": 1}
        all_cves.sort(key=lambda x: severity_order.get(x["severity"], 2))

        # Count stats
        total_images = len(images)
        total_vulns = len(all_cves)
        critical_count = sum(1 for c in all_cves if c["severity"] == "Critical")
        high_count = sum(1 for c in all_cves if c["severity"] == "High")

        # Generate Premium HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Premium SAST Vulnerability Report</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg-dark: #0f172a;
                    --panel-bg: rgba(255, 255, 255, 0.03);
                    --panel-border: rgba(255, 255, 255, 0.08);
                    --text-primary: #f8fafc;
                    --text-secondary: #94a3b8;
                    --critical-bg: linear-gradient(135deg, #ef4444, #b91c1c);
                    --high-bg: linear-gradient(135deg, #f97316, #c2410c);
                }}
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Inter', sans-serif;
                    background-color: var(--bg-dark);
                    color: var(--text-primary);
                    padding: 40px 20px;
                    min-height: 100vh;
                    background-image: 
                        radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.15), transparent 25%),
                        radial-gradient(circle at 85% 30%, rgba(236, 72, 153, 0.15), transparent 25%);
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    animation: fadeIn 0.8s ease-out;
                }}

                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(20px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}

                header {{
                    text-align: center;
                    margin-bottom: 50px;
                }}

                h1 {{
                    font-size: 3rem;
                    font-weight: 800;
                    background: linear-gradient(to right, #3b82f6, #8b5cf6, #ec4899);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 10px;
                }}

                p.subtitle {{
                    color: var(--text-secondary);
                    font-size: 1.1rem;
                }}

                .dashboard-cards {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 50px;
                }}

                .card {{
                    background: var(--panel-bg);
                    border: 1px solid var(--panel-border);
                    border-radius: 16px;
                    padding: 30px;
                    text-align: center;
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    transition: all 0.3s ease;
                }}

                .card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                    border-color: rgba(255, 255, 255, 0.15);
                }}

                .card h3 {{
                    color: var(--text-secondary);
                    font-size: 1rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 15px;
                }}

                .card .value {{
                    font-size: 3.5rem;
                    font-weight: 800;
                }}
                
                .val-total {{ color: #e2e8f0; }}
                .val-critical {{ background: var(--critical-bg); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                .val-high {{ background: var(--high-bg); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}

                .table-container {{
                    background: var(--panel-bg);
                    border: 1px solid var(--panel-border);
                    border-radius: 16px;
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th, td {{
                    padding: 16px 24px;
                    text-align: left;
                }}

                th {{
                    background-color: rgba(255,255,255,0.02);
                    color: var(--text-secondary);
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 0.85rem;
                    letter-spacing: 1px;
                    border-bottom: 1px solid var(--panel-border);
                }}

                tr {{
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                    transition: background-color 0.2s ease;
                }}

                tr:last-child {{
                    border-bottom: none;
                }}

                tr:hover {{
                    background-color: rgba(255,255,255,0.05);
                }}

                td {{
                    font-size: 0.95rem;
                }}

                .badge {{
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.8rem;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                }}

                .badge.Critical {{
                    background: var(--critical-bg);
                    color: white;
                }}

                .badge.High {{
                    background: var(--high-bg);
                    color: white;
                }}
                
                .pkg-name {{
                    font-family: monospace;
                    background: rgba(0,0,0,0.3);
                    padding: 4px 8px;
                    border-radius: 4px;
                    color: #93c5fd;
                }}

                .footer {{
                    text-align: center;
                    margin-top: 50px;
                    color: var(--text-secondary);
                    font-size: 0.9rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Security Posture Analytics</h1>
                    <p class="subtitle">Powered by Syft & Grype • Live Docker Compose Analysis</p>
                </header>

                <div class="dashboard-cards">
                    <div class="card">
                        <h3>Images Scanned</h3>
                        <div class="value val-total">{total_images}</div>
                    </div>
                    <div class="card">
                        <h3>Critical CVEs</h3>
                        <div class="value val-critical">{critical_count}</div>
                    </div>
                    <div class="card">
                        <h3>High CVEs</h3>
                        <div class="value val-high">{high_count}</div>
                    </div>
                </div>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Target Image</th>
                                <th>Vulnerability ID</th>
                                <th>Severity Level</th>
                                <th>Affected Package</th>
                                <th>Version</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        if len(all_cves) == 0:
            html += f"""
                            <tr>
                                <td colspan="5" style="text-align: center; padding: 40px; color: #10b981; font-weight: 600; font-size: 1.1rem;">
                                    🎉 No Critical or High vulnerabilities found! Your infrastructure is clean.
                                </td>
                            </tr>
            """
        else:
            for cve in all_cves:
                html += f"""
                            <tr>
                                <td>{cve['image']}</td>
                                <td><strong>{cve['id']}</strong></td>
                                <td><span class="badge {cve['severity']}">{cve['severity']}</span></td>
                                <td><span class="pkg-name">{cve['package']}</span></td>
                                <td>{cve['version']}</td>
                            </tr>
                """
                
        html += """
                        </tbody>
                    </table>
                </div>
                
                <div class="footer">
                    Generated dynamically from the current cluster state.
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("index.html", "w") as f:
            f.write(html)
        print(f"Report generated successfully. Found {len(all_cves)} severe vulnerabilities.")
            
    except Exception as e:
        print(f"Failed to generate report: {e}")

if __name__ == "__main__":
    generate_report()
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
            
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving CVE HTML report on port {PORT}...")
        httpd.serve_forever()
