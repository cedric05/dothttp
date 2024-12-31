import pytest
import subprocess
import time

@pytest.fixture(scope='session', autouse=True)
def start_httpbin_container():
    # Setup: Start the Docker container
    try:
        container_id = subprocess.check_output(
            ["docker", "run", "-d", "-p", "8000:80", "kennethreitz/httpbin"]
        ).decode().strip()
        # Wait for the container to be ready
        time.sleep(5)  # Adjust the sleep time as needed

        yield

        # Teardown: Stop and remove the Docker container
        subprocess.run(["docker", "stop", container_id])
        subprocess.run(["docker", "rm", container_id])
    except:
        pass