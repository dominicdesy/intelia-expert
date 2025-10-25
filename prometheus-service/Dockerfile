# Prometheus Service for Digital Ocean App Platform
# Scrapes metrics from Intelia Expert backend
# Version: 1.1.0 - Internal networking

FROM prom/prometheus:latest

# Copy Prometheus configuration
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Expose Prometheus port
EXPOSE 9090

# Use default Prometheus entrypoint with our config
# Internal networking only - no public routes needed
CMD ["--config.file=/etc/prometheus/prometheus.yml", \
     "--storage.tsdb.path=/prometheus", \
     "--storage.tsdb.retention.time=30d", \
     "--web.console.libraries=/usr/share/prometheus/console_libraries", \
     "--web.console.templates=/usr/share/prometheus/consoles"]
