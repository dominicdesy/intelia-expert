# Prometheus Service for Digital Ocean App Platform
# Scrapes metrics from Intelia Expert backend

FROM prom/prometheus:latest

# Copy Prometheus configuration
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Expose Prometheus port
EXPOSE 9090

# Use default Prometheus entrypoint with our config
# Configure route prefix for /prometheus path
CMD ["--config.file=/etc/prometheus/prometheus.yml", \
     "--storage.tsdb.path=/prometheus", \
     "--storage.tsdb.retention.time=30d", \
     "--web.console.libraries=/usr/share/prometheus/console_libraries", \
     "--web.console.templates=/usr/share/prometheus/consoles", \
     "--web.external-url=https://expert.intelia.com/prometheus", \
     "--web.route-prefix=/"]
