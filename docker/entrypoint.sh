#!/bin/bash
set -e

# ===========================================
# Install mitmproxy CA certificate for HTTPS inspection
# ===========================================
install_mitmproxy_ca() {
    echo "[entrypoint] Waiting for mitmproxy CA certificate..."
    local cert_path="/mitmproxy-certs/mitmproxy-ca-cert.pem"
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if [ -f "$cert_path" ]; then
            echo "[entrypoint] Found mitmproxy CA certificate"
            cp "$cert_path" /usr/local/share/ca-certificates/mitmproxy-ca.crt
            update-ca-certificates
            # Also set curl CA bundle for PHP
            echo "curl.cainfo=/etc/ssl/certs/ca-certificates.crt" > /usr/local/etc/php/conf.d/curl-ca.ini
            echo "[entrypoint] mitmproxy CA certificate installed successfully"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    echo "[entrypoint] WARNING: Could not find mitmproxy CA cert after ${max_attempts}s"
    echo "[entrypoint] HTTPS traffic logging may not work properly"
    return 0
}

# Try to install mitmproxy CA cert (non-blocking on failure)
install_mitmproxy_ca &

# Fix permissions for WHMCS writable directories
WRITABLE_DIRS=(
    /var/www/html/templates_c
    /var/www/html/downloads
    /var/www/html/attachments
)

for dir in "${WRITABLE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        chown -R www-data:www-data "$dir"
        chmod -R 755 "$dir"
    fi
done

# Ensure configuration.php is writable during install
if [ -f /var/www/html/configuration.php ]; then
    chown www-data:www-data /var/www/html/configuration.php
    chmod 644 /var/www/html/configuration.php
fi

# Setup WHMCS cron job (every 5 minutes)
echo "*/5 * * * * /usr/local/bin/php -q /var/www/html/crons/cron.php >> /var/log/whmcs-cron.log 2>&1" | crontab -
service cron start

echo "[entrypoint] Cron job started (every 5 minutes)"

# Run the original command (apache2-foreground)
exec "$@"
