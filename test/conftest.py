import pytest
import subprocess
import time
import socket
import sys

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@pytest.fixture(scope='session', autouse=True)
def start_httpbin_server():
    """Start httpbin server using gunicorn for tests."""
    # Check if httpbin is already running on port 8000
    if is_port_in_use(8000):
        print("httpbin is already running on port 8000, skipping server start")
        yield
        return

    # Setup: Start the gunicorn server with httpbin
    process = None
    try:
        # Start gunicorn with httpbin app
        process = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", "-b", "127.0.0.1:8000", "httpbin:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for the server to be ready
        max_attempts = 30
        for _ in range(max_attempts):
            if is_port_in_use(8000):
                print("httpbin server started successfully on port 8000")
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Failed to start httpbin server")

        yield

    finally:
        # Teardown: Stop the gunicorn server if we started it
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            print("httpbin server stopped")