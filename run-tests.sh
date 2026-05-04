#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
HTTPBIN_PORT=8000
HTTPBIN_IMAGE="kennethreitz/httpbin"
HTTPBIN_CONTAINER_NAME="dothttp-httpbin"
TEST_IMAGE="dothttp-test-runner"
CLEANUP_HTTPBIN=false

# Function to check if a port is in use
is_port_in_use() {
    nc -z localhost "$1" 2>/dev/null
}

# Function to check if httpbin container is running
is_httpbin_running() {
    docker ps --filter "name=${HTTPBIN_CONTAINER_NAME}" --filter "status=running" --format "{{.Names}}" | grep -q "${HTTPBIN_CONTAINER_NAME}"
}

# Function to start httpbin
start_httpbin() {
    echo -e "${YELLOW}Starting httpbin container...${NC}"
    docker run -d \
        --name "${HTTPBIN_CONTAINER_NAME}" \
        -p "${HTTPBIN_PORT}:80" \
        "${HTTPBIN_IMAGE}" > /dev/null

    echo -e "${GREEN}Waiting for httpbin to be ready...${NC}"
    sleep 3

    # Wait up to 30 seconds for httpbin to be ready
    for i in {1..30}; do
        if is_port_in_use "${HTTPBIN_PORT}"; then
            echo -e "${GREEN}httpbin is ready on port ${HTTPBIN_PORT}${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}httpbin failed to start${NC}"
    return 1
}

# Function to stop httpbin
stop_httpbin() {
    if [ "${CLEANUP_HTTPBIN}" = true ]; then
        echo -e "${YELLOW}Stopping httpbin container...${NC}"
        docker stop "${HTTPBIN_CONTAINER_NAME}" > /dev/null 2>&1 || true
        docker rm "${HTTPBIN_CONTAINER_NAME}" > /dev/null 2>&1 || true
    fi
}

# Function to build test image
build_test_image() {
    echo -e "${YELLOW}Building test runner image...${NC}"
    docker build -t "${TEST_IMAGE}" -f Dockerfile.test .
}

# Trap to ensure cleanup on exit
trap stop_httpbin EXIT INT TERM

# Check if httpbin is already running
if is_httpbin_running; then
    echo -e "${GREEN}httpbin container is already running${NC}"
elif is_port_in_use "${HTTPBIN_PORT}"; then
    echo -e "${GREEN}httpbin is already available on port ${HTTPBIN_PORT}${NC}"
else
    start_httpbin
    CLEANUP_HTTPBIN=true
fi

# Build test image if it doesn't exist or if Dockerfile.test is newer
if [ ! "$(docker images -q ${TEST_IMAGE} 2> /dev/null)" ] || [ Dockerfile.test -nt "$(docker inspect -f '{{.Created}}' ${TEST_IMAGE} 2>/dev/null || echo '1970-01-01')" ]; then
    build_test_image
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run tests in docker container
echo -e "${YELLOW}Running tests in Python 3.11 container...${NC}"
docker run --rm \
    --network host \
    -v "${SCRIPT_DIR}:/app" \
    -w /app \
    "${TEST_IMAGE}" \
    poetry run pytest "$@"

# Capture exit code
TEST_EXIT_CODE=$?

if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}Tests passed!${NC}"
else
    echo -e "${RED}Tests failed with exit code ${TEST_EXIT_CODE}${NC}"
fi

exit ${TEST_EXIT_CODE}
