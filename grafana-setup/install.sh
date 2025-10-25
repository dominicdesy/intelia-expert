#!/bin/bash
set -e

echo "=========================================="
echo "Installation Grafana + Prometheus"
echo "Pour Intelia Expert Monitoring"
echo "=========================================="

# Update system
echo "📦 Mise à jour du système..."
apt-get update
apt-get upgrade -y

# Install Docker
echo "🐳 Installation Docker..."
apt-get install -y ca-certificates curl gnupg lsb-release
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify Docker
docker --version

# Create directories
echo "📁 Création des répertoires..."
mkdir -p /opt/monitoring/{grafana,prometheus}
cd /opt/monitoring

# Create Prometheus config
echo "⚙️ Configuration Prometheus..."
cat > prometheus/prometheus.yml <<'EOF'
global:
  scrape_interval: 60s
  evaluation_interval: 60s

scrape_configs:
  - job_name: 'intelia-backend'
    scheme: https
    basic_auth:
      username: 'grafana'
      password: 'I#kmd9$kuZnO!dZXF9z8ZTF8'
    static_configs:
      - targets: ['expert.intelia.com']
    metrics_path: '/api/metrics'
    scrape_interval: 60s
    scrape_timeout: 30s
EOF

# Create Grafana config
echo "⚙️ Configuration Grafana..."
mkdir -p grafana/provisioning/datasources
cat > grafana/provisioning/datasources/prometheus.yml <<'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

# Create docker-compose.yml
echo "🐳 Création docker-compose.yml..."
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_SECURITY_ALLOW_EMBEDDING=true
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_SERVER_ROOT_URL=http://146.190.241.191:3000
      - GF_SECURITY_COOKIE_SAMESITE=none
      - GF_SECURITY_COOKIE_SECURE=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    restart: unless-stopped
    networks:
      - monitoring
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:

networks:
  monitoring:
    driver: bridge
EOF

# Start services
echo "🚀 Démarrage des services..."
docker compose up -d

# Wait for services
echo "⏳ Attente du démarrage des services (30s)..."
sleep 30

# Check status
echo "✅ Vérification du statut..."
docker compose ps

echo ""
echo "=========================================="
echo "✅ Installation terminée!"
echo "=========================================="
echo ""
echo "Grafana accessible à: http://146.190.241.191:3000"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "Prometheus accessible à: http://146.190.241.191:9090"
echo ""
echo "⚠️  IMPORTANT: Changez le mot de passe admin après connexion!"
echo ""
