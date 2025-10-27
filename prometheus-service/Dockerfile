# Prometheus Service for Digital Ocean App Platform
# Scrapes metrics from Intelia Expert backend
# Version: 1.1.0 - Internal networking

FROM prom/prometheus:latest

# Build arguments for version tracking
ARG BUILD_VERSION=unknown
ARG BUILD_DATE=unknown
ARG COMMIT_SHA=unknown

# Set as environment variables
ENV BUILD_VERSION=${BUILD_VERSION} \
    BUILD_DATE=${BUILD_DATE} \
    COMMIT_SHA=${COMMIT_SHA}

# Install Python for version exporter
USER root
RUN apk add --no-cache python3

# Copy Prometheus configuration
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Copy version exporter and entrypoint
COPY version_exporter.py /version_exporter.py
COPY entrypoint.sh /entrypoint.sh

# Make scripts executable
RUN chmod +x /version_exporter.py /entrypoint.sh

# Switch back to prometheus user
USER nobody

# Expose Prometheus port (9090) and version exporter port (9091)
EXPOSE 9090 9091

# Use custom entrypoint that starts both Prometheus and version exporter
ENTRYPOINT ["/entrypoint.sh"]
