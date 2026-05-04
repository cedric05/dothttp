# Testing Guide

This document describes how to run tests for the dothttp project.

## Running Tests

### Quick Start

Run all tests using the Docker-based test runner:

```bash
./run-tests.sh
```

Run specific tests:

```bash
# Run a specific test file
./run-tests.sh test/core/test_payload.py

# Run a specific test
./run-tests.sh test/core/test_payload.py::PayLoadTest::test_data_multi_payload_triple

# Run with verbose output
./run-tests.sh -v

# Run and stop on first failure
./run-tests.sh -x --maxfail=1
```

### Test Environment

Tests run in a Docker container with:
- Python 3.11
- All project dependencies installed via Poetry
- httpbin container for HTTP testing
- Isolated network with host access

The test runner (`run-tests.sh`) automatically:
1. Checks if httpbin is already running
2. Starts httpbin if needed
3. Builds the test Docker image if needed
4. Runs pytest with all arguments forwarded
5. Cleans up httpbin on exit

## Certificate Tests

Certificate tests use client certificates from [badssl.com](https://badssl.com/) to test SSL/TLS client authentication.

### Updating Certificates

When certificate tests fail due to expired certificates, update them:

```bash
# From project root
./update-badssl-certs.sh

# Or directly
cd test/core/root_cert/certs
./update-certs.sh
```

The update script will:
- Download latest certificates from badssl.com
- Process them into required formats
- Verify certificate validity
- Create backups of existing certificates
- Install new certificates

After updating, verify the tests pass:

```bash
./run-tests.sh test/core/test_certs.py
```

### Automated Certificate Updates

A GitHub Actions workflow (`.github/workflows/update-badssl-certs.yml`) runs monthly to:
1. Check if certificates expire within 30 days
2. Download and install new certificates
3. Run certificate tests
4. Create a Pull Request with the updates

You can also trigger this workflow manually from the GitHub Actions tab.

## Test Categories

### Core Tests (`test/core/`)
- HTTP request/response handling
- Authentication (AWS, Azure, Basic, Digest, NTLM, Hawk)
- Certificates (client certificates, p12 files)
- Payload handling (JSON, multipart, files)
- Script execution (Python, JavaScript)
- Property substitution

### Extension Tests (`test/extensions/`)
- Command handlers
- Content processing
- File system handlers
- HTTP to HAR conversion
- HTTP to Postman conversion
- Script execution integration

## Skipped Tests

Some tests are intentionally skipped:

### Platform-Specific Tests
- Windows-only tests (multiline curl) - Skip on Linux/macOS
- Linux-only tests (NTLM auth) - Skip on Windows/macOS

### External Dependencies
- NTLM authentication - Requires running local NTLM test server
- Hawk authentication - Requires external Hawk auth service
- Node.js require tests - Requires Node.js installation

### Environment-Specific
- Write permission tests - Skip when running as root (Docker)
- Path-specific tests - Skip when paths don't match CI environment

## Continuous Integration

### GitHub Actions
The project uses GitHub Actions for CI:
- Run tests on every push and pull request
- Test on multiple Python versions (3.11, 3.12)
- Generate test coverage reports
- Automated certificate updates

### Docker
Tests can run in Docker for consistency:
```bash
# Build test image
docker build -f Dockerfile.test -t dothttp-test-runner .

# Run tests
docker run --rm --network host \
    -v "$(pwd):/app" \
    -w /app \
    dothttp-test-runner \
    poetry run pytest
```

## Troubleshooting

### httpbin Connection Issues
If tests fail with httpbin connection errors:

```bash
# Check if httpbin is running
docker ps | grep httpbin

# Stop old containers
docker stop dothttp-httpbin
docker rm dothttp-httpbin

# Run tests again (will start fresh httpbin)
./run-tests.sh
```

### Certificate Errors
If certificate tests fail:

1. Check certificate expiration:
   ```bash
   cd test/core/root_cert/certs
   openssl x509 -in cert.crt -noout -dates
   ```

2. Update certificates:
   ```bash
   ./update-badssl-certs.sh
   ```

3. Verify badssl.com is accessible:
   ```bash
   curl -I https://client.badssl.com/
   ```

### Python Version Issues
The project requires Python 3.11 for full test compatibility:
- Python 3.12: js2py has compatibility issues
- Python 3.10: Some features may not work

If using Python 3.12, some JavaScript execution tests may fail.

### Docker Image Issues
If the test Docker image has issues:

```bash
# Remove old image
docker rmi dothttp-test-runner

# Rebuild on next test run
./run-tests.sh
```

### Permission Issues in Docker
When running as root in Docker, some permission-based tests are skipped. This is expected and normal.

## Writing Tests

### Test Structure
```python
from test import TestBase

class MyTest(TestBase):
    def test_something(self):
        req = self.get_req_comp(
            "path/to/file.http",
            target="request-name"
        )
        resp = req.get_response()
        self.assertEqual(200, resp.status_code)
```

### Test Fixtures
- `TestBase` - Base class with helper methods
- `httpbin` - HTTP testing service (auto-started)
- `tempdir` - Temporary directory for file tests

### Useful Patterns
```python
# Test with properties
req = self.get_req_comp(
    filename,
    properties={"key": "value"}
)

# Test with environment
req = self.get_req_comp(
    filename,
    env=["dev", "test"]
)

# Skip platform-specific tests
@unittest.skipUnless(sys.platform.startswith("linux"), "requires linux")
def test_linux_only(self):
    pass

# Skip external dependency tests
@pytest.mark.skip("requires external service")
def test_external(self):
    pass
```

## Performance

Average test run times:
- All tests: ~15-20 seconds
- Core tests only: ~5-8 seconds
- Certificate tests only: ~4-6 seconds

The Docker-based test runner adds ~2-3 seconds for image building/startup (cached after first run).
