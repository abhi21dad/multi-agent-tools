# Pytest configuration shared fixtures
import pytest


@pytest.fixture(scope='session')
def base_url():
    """Base URL for testing."""
    return 'http://localhost'


@pytest.fixture(scope='session')
def file_server_url(base_url):
    """File server URL."""
    return f'{base_url}:5002'


@pytest.fixture(scope='session')
def gmail_server_url(base_url):
    """Gmail server URL."""
    return f'{base_url}:5004'


@pytest.fixture(scope='session')
def gdrive_server_url(base_url):
    """Google Drive server URL."""
    return f'{base_url}:5003'


@pytest.fixture(scope='session')
def twitter_server_url(base_url):
    """Twitter server URL."""
    return f'{base_url}:5001'
