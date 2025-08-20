# Build stage
FROM golang:1.21-alpine AS builder

# Set working directory
WORKDIR /workspace

# Install dependencies
RUN apk add --no-cache git ca-certificates

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy the source code
COPY . .

# Build the operator
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o manager main.go

# Runtime stage
FROM gcr.io/distroless/static:nonroot

# Copy the operator binary from builder
COPY --from=builder /workspace/manager .

# Use nonroot user
USER 65532:65532

# Expose metrics port
EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["/manager"]