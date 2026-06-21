# Build stage
FROM golang:1.21-alpine@sha256:2414035b086e3c42b99654c8b26e6f5b1b1598080d65fd03c7f499552ff4dc94 AS builder

WORKDIR /app

# Enable CGO_ENABLED=0 early so it applies to go build
ENV CGO_ENABLED=0
ENV GOOS=linux

# Download dependencies
COPY go.mod main.go ./
# To prevent failure if there's no go.sum, we run go mod tidy inside the container
RUN go mod tidy
RUN go mod download

# Build the application
RUN go build -o server main.go

# Run stage
FROM alpine:latest@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11
LABEL org.opencontainers.image.source="https://github.com/dartoledo/dar"
WORKDIR /app

# Ensure we have CA certificates if needed for external calls
RUN apk --no-cache add ca-certificates

COPY --from=builder /app/server .
COPY users.txt .

EXPOSE 8080
CMD ["./server"]
