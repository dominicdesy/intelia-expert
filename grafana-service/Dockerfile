# Grafana Web Service for Digital Ocean App Platform
# Configured with allow_embedding for iframe integration
# Build version: 1.0.1

FROM grafana/grafana:latest

# Copy datasource configuration
# The official Grafana image already has the right directories and permissions
COPY --chown=472:0 provisioning/datasources/prometheus.yml /etc/grafana/provisioning/datasources/

# Environment variables (can be overridden in App Platform)
ENV GF_SECURITY_ALLOW_EMBEDDING=true \
    GF_AUTH_ANONYMOUS_ENABLED=false \
    GF_SERVER_ROOT_URL=https://grafana-intelia.ondigitalocean.app \
    GF_SECURITY_COOKIE_SAMESITE=none \
    GF_SECURITY_COOKIE_SECURE=true

# Expose Grafana port
EXPOSE 3000
