#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CERT_DIR="${SCRIPT_DIR}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}BadSSL Certificate Updater${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to download a file
download_file() {
    local url=$1
    local output=$2
    local description=$3

    echo -e "${YELLOW}Downloading ${description}...${NC}"
    if curl -s -f "${url}" -o "${output}"; then
        echo -e "${GREEN}✓ Downloaded ${description}${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to download ${description}${NC}"
        return 1
    fi
}

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap "rm -rf ${TMP_DIR}" EXIT

echo -e "${BLUE}Step 1: Downloading certificates from badssl.com${NC}"
echo ""

# Download the combined PEM file (certificate + encrypted private key)
download_file \
    "https://badssl.com/certs/badssl.com-client.pem" \
    "${TMP_DIR}/badssl-client-encrypted.pem" \
    "client certificate with encrypted key"

# Download the P12 file
download_file \
    "https://badssl.com/certs/badssl.com-client.p12" \
    "${TMP_DIR}/badssl.com-client.p12" \
    "P12 certificate"

echo ""
echo -e "${BLUE}Step 2: Processing certificates${NC}"
echo ""

# Extract certificate only
echo -e "${YELLOW}Extracting certificate...${NC}"
openssl x509 -in "${TMP_DIR}/badssl-client-encrypted.pem" \
    -out "${TMP_DIR}/cert.crt" 2>/dev/null
echo -e "${GREEN}✓ Extracted certificate to cert.crt${NC}"

# Extract encrypted private key and decrypt it
echo -e "${YELLOW}Extracting and decrypting private key...${NC}"
openssl pkey -in "${TMP_DIR}/badssl-client-encrypted.pem" \
    -passin pass:badssl.com \
    -out "${TMP_DIR}/key.key" 2>/dev/null
echo -e "${GREEN}✓ Extracted private key to key.key${NC}"

# Create unencrypted combined PEM file (cert + unencrypted key)
echo -e "${YELLOW}Creating combined certificate with unencrypted key...${NC}"
cat "${TMP_DIR}/cert.crt" "${TMP_DIR}/key.key" > "${TMP_DIR}/no-password.pem"
echo -e "${GREEN}✓ Created no-password.pem${NC}"

echo ""
echo -e "${BLUE}Step 3: Verifying certificates${NC}"
echo ""

# Verify certificate
echo -e "${YELLOW}Verifying certificate validity...${NC}"
CERT_SUBJECT=$(openssl x509 -in "${TMP_DIR}/cert.crt" -noout -subject 2>/dev/null)
CERT_ISSUER=$(openssl x509 -in "${TMP_DIR}/cert.crt" -noout -issuer 2>/dev/null)
CERT_DATES=$(openssl x509 -in "${TMP_DIR}/cert.crt" -noout -dates 2>/dev/null)

echo -e "${GREEN}Certificate Details:${NC}"
echo -e "  ${CERT_SUBJECT}"
echo -e "  ${CERT_ISSUER}"
echo -e "  ${CERT_DATES}"

# Verify the key matches the certificate
echo ""
echo -e "${YELLOW}Verifying key matches certificate...${NC}"
CERT_MODULUS=$(openssl x509 -noout -modulus -in "${TMP_DIR}/cert.crt" 2>/dev/null | openssl md5)
KEY_MODULUS=$(openssl rsa -noout -modulus -in "${TMP_DIR}/key.key" 2>/dev/null | openssl md5)

if [ "${CERT_MODULUS}" = "${KEY_MODULUS}" ]; then
    echo -e "${GREEN}✓ Private key matches certificate${NC}"
else
    echo -e "${RED}✗ Private key does NOT match certificate!${NC}"
    exit 1
fi

# Test P12 file
echo ""
echo -e "${YELLOW}Verifying P12 file...${NC}"
# P12 file uses legacy encryption (RC2-40-CBC), need to enable legacy provider for OpenSSL 3.x
if openssl pkcs12 -in "${TMP_DIR}/badssl.com-client.p12" -passin pass:badssl.com -noout -legacy 2>/dev/null || \
   openssl pkcs12 -in "${TMP_DIR}/badssl.com-client.p12" -passin pass:badssl.com -noout 2>/dev/null; then
    echo -e "${GREEN}✓ P12 file is valid${NC}"
else
    echo -e "${YELLOW}⚠ Could not verify P12 file (may use legacy encryption)${NC}"
    echo -e "${YELLOW}  This is expected with OpenSSL 3.x - the file should still work${NC}"
fi

echo ""
echo -e "${BLUE}Step 4: Installing certificates${NC}"
echo ""

# Backup existing certificates
if [ -f "${CERT_DIR}/no-password.pem" ]; then
    BACKUP_DIR="${CERT_DIR}/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${BACKUP_DIR}"
    echo -e "${YELLOW}Creating backup of existing certificates...${NC}"
    cp "${CERT_DIR}"/*.{pem,crt,key,p12} "${BACKUP_DIR}/" 2>/dev/null || true
    echo -e "${GREEN}✓ Backed up to ${BACKUP_DIR}${NC}"
    echo ""
fi

# Copy new certificates
echo -e "${YELLOW}Installing new certificates...${NC}"
cp "${TMP_DIR}/no-password.pem" "${CERT_DIR}/no-password.pem"
echo -e "${GREEN}✓ Installed no-password.pem${NC}"

cp "${TMP_DIR}/cert.crt" "${CERT_DIR}/cert.crt"
echo -e "${GREEN}✓ Installed cert.crt${NC}"

cp "${TMP_DIR}/key.key" "${CERT_DIR}/key.key"
echo -e "${GREEN}✓ Installed key.key${NC}"

cp "${TMP_DIR}/badssl.com-client.p12" "${CERT_DIR}/badssl.com-client.p12"
echo -e "${GREEN}✓ Installed badssl.com-client.p12${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Certificate update completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Files updated:${NC}"
echo -e "  • ${CERT_DIR}/no-password.pem"
echo -e "  • ${CERT_DIR}/cert.crt"
echo -e "  • ${CERT_DIR}/key.key"
echo -e "  • ${CERT_DIR}/badssl.com-client.p12"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Run tests: ${BLUE}cd /Users/skesavarapu/projects/personal/cedric05/dothttp && ./run-tests.sh test/core/test_certs.py${NC}"
echo -e "  2. If tests pass, commit the changes: ${BLUE}git add test/core/root_cert/certs/ && git commit -m \"Update badssl certificates\"${NC}"
echo ""
