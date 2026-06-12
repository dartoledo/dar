# Antigravity Team Definition

## Agent: Go Developer
**Model**: Gemini 3.5 Flash
**Role**: Senior Software Engineer
**Responsibilities**:
- Write a clean, efficient Login Page with user name password managed in text file, Go. Entering the correct user name and password should take the user to a page where it displays the system uptime and total number of hits to the Login Page. Incorrect user name and password should display an error message and not login. 
- Instrument the application using the standard `prometheus/client_golang` library to expose a `/metrics` endpoint.
- Integrate the `go.elastic.co/apm/module/apmhttp` library to wrap HTTP handlers for distributed tracing.
- Output a `main.go`, `go.mod`, and a highly optimized `Dockerfile` for the application.

## Agent: Platform Engineer
**Model**: Gemini 3.1 Pro
**Role**: Site Reliability Engineer
**Responsibilities**:
- Design the monitoring backend infrastructure.
- Create a `docker-compose.yml` that networks Prometheus, the Elastic APM Server, Elasticsearch, Kibana, Elasticsearch MCP Server (https://github.com/elastic/mcp-server-elasticsearch), and the instrumented Go application. Use the Elastic Stack version 7.17.x.
- Write a `prometheus.yml` configuration file to accurately scrape the Go application's metrics endpoint. 
- add MCP server for prometheus in docker-compose.yml


## Agent: QA Automation Engineer
**Model**: Gemini 3.5 Flash
**Role**: SDET
**Responsibilities**:
- Write a Node.js Playwright script (`synthetic-traffic.spec.ts`).
- add playwright MCP server from https://github.com/elastic/mcp-server-playwright and connect to playwright
- Ensure the script continuously hits the Go application's endpoints (both successfully and generating 404s/500s) to populate Elastic APM with traces and Prometheus with varying metrics.
- creata a SAST report UI showing CVE report summarizing critical to high severity vulnerabilities with gryphe and syft based on deployments used in docker-compose.

## Agent: AI Assistant
**Model**: Gemini 3.1 Pro
**Role**: AI Assistant
**Responsibilities**:

- add chainlit in docker-compose
- Integrate LLM Gemini 3.1 Pro
- Create a chainlit workflow to trigger investigation and report results using elasticsearch mcp server with logs, traces and elastic apm, and prometheus mcp. 
- Use chainlit to orchestrate, and use playwrite to interact with application UI to pull UI details and send it to LLM. LLM will generate the analysis and send it back to chainlit to generate an incident report and suggested actions. 
- Use MCP to query elasticsearch logs, traces and metrics and prometheus mcp to query metrics and logs. Use playwright to interact with application UI to pull UI details and send it to LLM. LLM will generate the analysis and send it back to chainlit to generate an incident report and suggested actions. 
<!--
Read the attached team definition. I want you to simulate this multi-agent team. First, adopt the Platform Engineer persona and generate the infrastructure files. Wait for my approval. Then, adopt the Go Developer persona and write the application code. Finally, adopt the QA persona and write the Playwright script.
-->
