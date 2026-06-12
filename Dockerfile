# Build stage
FROM golang:1.21-alpine AS builder

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
FROM alpine:latest
WORKDIR /app

# Ensure we have CA certificates if needed for external calls
RUN apk --no-cache add ca-certificates

COPY --from=builder /app/server .
COPY users.txt .

EXPOSE 8080
CMD ["./server"]
