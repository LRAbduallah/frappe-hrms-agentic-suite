#!/bin/bash

set -Eeuo pipefail

BENCH_DIR="/home/frappe/frappe-bench"
SITE_NAME="hrms.localhost"

MARIADB_ROOT_PASSWORD="123"
ADMIN_PASSWORD="admin"

echo "======================================"
echo "Starting Frappe initialization"
echo "======================================"

# --------------------------------------------------
# Configure Node.js path
# --------------------------------------------------

if [ -n "${NVM_DIR:-}" ] && [ -n "${NODE_VERSION_DEVELOP:-}" ]; then
    NODE_BIN="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin"

    if [ -d "${NODE_BIN}" ]; then
        export PATH="${NODE_BIN}:${PATH}"
    fi
fi

cd /home/frappe

# --------------------------------------------------
# Case 1: Bench already exists
# --------------------------------------------------

if [ -d "${BENCH_DIR}/apps/frappe" ]; then
    echo "======================================"
    echo "Existing Frappe bench found"
    echo "Skipping initialization"
    echo "======================================"

    cd "${BENCH_DIR}"

    # Ensure the correct site is selected.
    if [ -d "${BENCH_DIR}/sites/${SITE_NAME}" ]; then
        bench use "${SITE_NAME}"
    fi

    echo "Starting existing Frappe bench..."
    exec bench start
fi

# --------------------------------------------------
# Case 2: Detect incomplete bench
# --------------------------------------------------

if [ -e "${BENCH_DIR}/apps" ] || [ -e "${BENCH_DIR}/sites" ]; then
    echo "======================================"
    echo "ERROR: Incomplete Frappe bench detected"
    echo "======================================"
    echo "Bench directory: ${BENCH_DIR}"
    echo
    echo "Remove the frappe-home-data Docker volume and restart."
    exit 1
fi

# --------------------------------------------------
# Case 3: Initialize a new bench
# --------------------------------------------------

echo "======================================"
echo "Creating new Frappe bench"
echo "======================================"

bench init \
    --skip-redis-config-generation \
    frappe-bench

cd "${BENCH_DIR}"

# --------------------------------------------------
# Configure MariaDB and Redis
# --------------------------------------------------

echo "======================================"
echo "Configuring MariaDB and Redis"
echo "======================================"

bench set-mariadb-host mariadb

bench set-redis-cache-host redis://redis:6379

bench set-redis-queue-host redis://redis:6379

bench set-redis-socketio-host redis://redis:6379

# Redis and file watching are managed outside
# the standard local development setup.
sed -i '/redis/d' Procfile
sed -i '/watch/d' Procfile

# --------------------------------------------------
# Download ERPNext and HRMS
# --------------------------------------------------

echo "======================================"
echo "Downloading ERPNext"
echo "======================================"

bench get-app erpnext

echo "======================================"
echo "Downloading HRMS"
echo "======================================"

bench get-app hrms

# --------------------------------------------------
# Create the HRMS site
# --------------------------------------------------

echo "======================================"
echo "Creating HRMS site"
echo "======================================"

bench new-site "${SITE_NAME}" \
    --force \
    --mariadb-root-password "${MARIADB_ROOT_PASSWORD}" \
    --admin-password "${ADMIN_PASSWORD}" \
    --no-mariadb-socket

# --------------------------------------------------
# Install HRMS
# --------------------------------------------------

echo "======================================"
echo "Installing HRMS app"
echo "======================================"

bench --site "${SITE_NAME}" install-app hrms

# --------------------------------------------------
# Configure the site
# --------------------------------------------------

echo "======================================"
echo "Configuring HRMS site"
echo "======================================"

bench --site "${SITE_NAME}" set-config developer_mode 1

bench --site "${SITE_NAME}" enable-scheduler

bench --site "${SITE_NAME}" clear-cache

bench use "${SITE_NAME}"

echo "======================================"
echo "Frappe initialization completed"
echo "======================================"

cd "${BENCH_DIR}"

# Start the Frappe development server
exec bench start