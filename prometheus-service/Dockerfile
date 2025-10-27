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

# Copy Prometheus configuration
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Copy version metadata file
RUN echo "VERSION=${BUILD_VERSION}" > /etc/prometheus/version.txt && \
    echo "BUILD_DATE=${BUILD_DATE}" >> /etc/prometheus/version.txt && \
    echo "COMMIT_SHA=${COMMIT_SHA}" >> /etc/prometheus/version.txt

# Expose Prometheus port
EXPOSE 9090

# Use default Prometheus entrypoint with our config
# Version info available via environment variables
CMD ["--config.file=/etc/prometheus/prometheus.yml", \
     "--storage.tsdb.path=/prometheus", \
     "--storage.tsdb.retention.time=30d", \
     "--web.console.libraries=/usr/share/prometheus/console_libraries", \
     "--web.console.templates=/usr/share/prometheus/consoles"]
