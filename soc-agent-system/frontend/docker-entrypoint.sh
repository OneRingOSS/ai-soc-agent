#!/bin/sh
# =============================================================================
# SOC Agent Frontend — Docker Entrypoint Script
# =============================================================================
# Substitutes environment variables in nginx.conf.template and starts nginx
# =============================================================================

set -e

# Default values
BACKEND_HOST=${BACKEND_HOST:-backend}
BACKEND_PORT=${BACKEND_PORT:-8000}

echo "Configuring nginx with BACKEND_HOST=${BACKEND_HOST} BACKEND_PORT=${BACKEND_PORT}"

# Substitute environment variables in nginx.conf.template
envsubst '${BACKEND_HOST} ${BACKEND_PORT}' < /etc/nginx/conf.d/nginx.conf.template > /etc/nginx/conf.d/default.conf

echo "Nginx configuration generated:"
cat /etc/nginx/conf.d/default.conf

# Start nginx
# -g 'daemon off;' keeps nginx in foreground for container
# PID file location configured in /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'

