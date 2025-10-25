# Grafana Web Service for Digital Ocean App Platform
# Configured with allow_embedding for iframe integration

FROM grafana/grafana:latest

# Switch to root to install dependencies
USER root

# Create provisioning directories
RUN mkdir -p /etc/grafana/provisioning/datasources

# Copy datasource configuration
COPY provisioning/datasources/prometheus.yml /etc/grafana/provisioning/datasources/

# Set permissions
RUN chown -R grafana:grafana /etc/grafana/provisioning

# Switch back to grafana user
USER grafana

# Expose Grafana port
EXPOSE 3000

# Environment variables (can be overridden in App Platform)
ENV GF_SECURITY_ALLOW_EMBEDDING=true \
    GF_AUTH_ANONYMOUS_ENABLED=false \
    GF_SERVER_ROOT_URL=https://grafana-intelia.ondigitalocean.app \
    GF_SECURITY_COOKIE_SAMESITE=none \
    GF_SECURITY_COOKIE_SECURE=true

# Start Grafana
CMD ["grafana-server", "--homepath=/usr/share/grafana", "--config=/etc/grafana/grafana.ini"]
