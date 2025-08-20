# Base image for admission controller
FROM alpine:3.18

# Install required packages
RUN apk add --no-cache \
    ca-certificates \
    curl \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1000 admission && \
    adduser -D -u 1000 -G admission admission

# Set working directory
WORKDIR /app

# Copy admission controller binary (placeholder)
# In real implementation, this would copy the actual binary
COPY admission-controller /app/admission-controller

# Copy configuration files
COPY config/ /app/config/

# Change ownership to non-root user
RUN chown -R admission:admission /app

# Switch to non-root user
USER admission

# Expose port for admission webhook
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f https://localhost:8443/healthz || exit 1

# Default command
ENTRYPOINT ["/app/admission-controller"]
CMD ["--port=8443", "--cert-dir=/app/certs", "--config=/app/config/admission.yaml"]