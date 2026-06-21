FROM python:3.11-alpine@sha256:f417205fec4ccb0d5023fdb5ecb4c8eba31c1834f94dcbcd1a2e8325fa7a7b89
LABEL org.opencontainers.image.source="https://github.com/dartoledo/dar"

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
