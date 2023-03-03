import os
import subprocess


import pytest


@pytest.fixture
def test_setup_and_teardown():
    subprocess.run(["pip", "uninstall", "xattr", "-y"])
    cwd = os.getcwd()
    os.chdir(os.path.dirname(__file__))
    yield
    os.chdir(cwd)
    subprocess.run(["pip", "install", "xattr"])


@pytest.mark.serial
async def test_filesystem_without_xattr(test_setup_and_teardown):
    result = subprocess.run(["pytest", "./test_filesystem_component.py"])
    assert result.returncode == 0
