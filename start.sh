#!/bin/bash
set -e
export RUNTIME=local
export INSTALL_DOCKER=0

# Ensure nginx config is linked and start reverse proxy
ln -sf /etc/nginx/sites-available/openhands /etc/nginx/sites-enabled/openhands
nginx -s stop 2>/dev/null || true
sleep 1
nginx

exec make run
