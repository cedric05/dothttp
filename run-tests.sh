#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TEST_IMAGE="dothttp-test-runner"

# Function to build test image
build_test_image() {
    echo -e "${YELLOW}Building test runner image...${NC}"
    docker build -t "${TEST_IMAGE}" -f Dockerfile.test .
}

# Build test image if it doesn't exist or if Dockerfile.test is newer
if [ ! "$(docker images -q ${TEST_IMAGE} 2> /dev/null)" ] || [ Dockerfile.test -nt "$(docker inspect -f '{{.Created}}' ${TEST_IMAGE} 2>/dev/null || echo '1970-01-01')" ]; then
    build_test_image
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run tests in docker container
# httpbin server is started automatically by pytest conftest.py
echo -e "${YELLOW}Running tests in Python 3.14 container ...${NC}"
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
