import pytest
import subprocess
import time
import socket

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@pytest.fixture(scope='session', autouse=True)
def start_httpbin_container():
    # Check if httpbin is already running on port 8000
    if is_port_in_use(8000):
        print("httpbin is already running on port 8000, skipping container start")
        yield
        return

    # Setup: Start the Docker container
    container_id = None
    try:
        container_id = subprocess.check_output(
            ["docker", "run", "-d", "-p", "8000:80", "kennethreitz/httpbin"]
        ).decode().strip()
        # Wait for the container to be ready
        time.sleep(5)  # Adjust the sleep time as needed

        yield

    finally:
        # Teardown: Stop and remove the Docker container if we started it
        if container_id:
            subprocess.run(["docker", "stop", container_id], capture_output=True)
            subprocess.run(["docker", "rm", container_id], capture_output=True)