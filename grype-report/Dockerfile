FROM python:3.11-alpine

# Install Docker CLI to query the socket
RUN apk add --no-cache docker-cli curl

# Install Syft (SBOM generator)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Install Grype (Vulnerability Scanner)
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

WORKDIR /app
COPY scanner.py .

# Run the scanner script which also hosts the HTTP server
CMD ["python", "-u", "scanner.py"]
