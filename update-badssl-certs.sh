#!/bin/bash

# Convenience wrapper to update badssl certificates
# This script just calls the actual update script in the certs directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CERT_UPDATE_SCRIPT="${SCRIPT_DIR}/test/core/root_cert/certs/update-certs.sh"

if [ ! -f "${CERT_UPDATE_SCRIPT}" ]; then
    echo "Error: Certificate update script not found at ${CERT_UPDATE_SCRIPT}"
    exit 1
fi

echo "Running certificate update script..."
echo ""

"${CERT_UPDATE_SCRIPT}" "$@"
