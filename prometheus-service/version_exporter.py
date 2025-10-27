#!/usr/bin/env python3
"""
Prometheus Version Exporter
Version: 1.4.1
Last modified: 2025-10-26

Simple HTTP server that exposes version information as Prometheus metrics
and provides a JSON endpoint for version details.
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


def get_version_info():
    """
    Get version information from environment variables (set by Docker build)

    Returns:
        dict: Version information including version, build_date, commit_sha
    """
    version = os.getenv("BUILD_VERSION", "unknown")
    build_date = os.getenv("BUILD_DATE", "unknown")
    commit_sha = os.getenv("COMMIT_SHA", "unknown")

    # Short commit SHA (first 7 characters)
    short_sha = commit_sha[:7] if commit_sha != "unknown" else "unknown"

    return {
        "version": version,
        "build_date": build_date,
        "commit": short_sha,
        "commit_full": commit_sha,
        "service": "prometheus",
        "timestamp": datetime.utcnow().isoformat()
    }


class VersionHandler(BaseHTTPRequestHandler):
    """HTTP request handler for version endpoints"""

    def log_message(self, format, *args):
        """Suppress default logging to avoid cluttering Prometheus logs"""
        pass

    def do_GET(self):
        """Handle GET requests"""
        version_info = get_version_info()

        if self.path == '/version':
            # JSON endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps(version_info, indent=2)
            self.wfile.write(response.encode('utf-8'))

        elif self.path == '/metrics':
            # Prometheus metrics format
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()

            # Build info metric (follows Prometheus convention)
            metrics = f"""# HELP prometheus_build_info Build information about Prometheus
# TYPE prometheus_build_info gauge
prometheus_build_info{{version="{version_info['version']}",commit="{version_info['commit']}",build_date="{version_info['build_date']}"}} 1
# HELP prometheus_version_info Version information
# TYPE prometheus_version_info gauge
prometheus_version_info{{version="{version_info['version']}"}} 1
"""
            self.wfile.write(metrics.encode('utf-8'))

        elif self.path == '/health':
            # Health check endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')

        else:
            # 404 for other paths
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')


def run_server(port=9091):
    """
    Run the version exporter HTTP server

    Args:
        port: Port to listen on (default: 9091, Prometheus runs on 9090)
    """
    server_address = ('', port)
    httpd = HTTPServer(server_address, VersionHandler)

    version_info = get_version_info()
    print(f"Prometheus Version Exporter starting on port {port}")
    print(f"Version: {version_info['version']}")
    print(f"Commit: {version_info['commit']}")
    print(f"Build Date: {version_info['build_date']}")
    print(f"Endpoints:")
    print(f"  - http://localhost:{port}/version (JSON)")
    print(f"  - http://localhost:{port}/metrics (Prometheus format)")
    print(f"  - http://localhost:{port}/health (Health check)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down version exporter...")
        httpd.shutdown()


if __name__ == '__main__':
    run_server()
