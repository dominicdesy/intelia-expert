#!/bin/sh
# Prometheus Service Entrypoint
# Version: 1.4.1
# Last modified: 2025-10-26
#
# Starts both Prometheus and the version exporter

echo "=== Prometheus Service Starting ==="
echo "Build Version: ${BUILD_VERSION:-unknown}"
echo "Build Date: ${BUILD_DATE:-unknown}"
echo "Commit SHA: ${COMMIT_SHA:-unknown}"
echo "=================================="

# Start version exporter in background on port 9091
python3 /version_exporter.py &
VERSION_EXPORTER_PID=$!

echo "Version exporter started (PID: $VERSION_EXPORTER_PID)"

# Start Prometheus (this will run in foreground)
exec /bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/prometheus \
    --storage.tsdb.retention.time=30d \
    --web.console.libraries=/usr/share/prometheus/console_libraries \
    --web.console.templates=/usr/share/prometheus/consoles
