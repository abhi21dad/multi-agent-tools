"""
Basic integration tests for LangGraph chatbot microservices.

Tests health endpoints and basic functionality of each service.
Run with: pytest tests/test_services.py -v
"""

import pytest
import requests
import os
import time

# Service URLs
SERVICES = {
    'file': 'http://localhost:5002',
    'gdrive': 'http://localhost:5003',
    'gmail': 'http://localhost:5004',
    'twitter': 'http://localhost:5001',
}

# Auth tokens from environment
FILE_AUTH_TOKEN = os.getenv('FILE_SERVER_AUTH_TOKEN', 'FilePass123!@#')
GMAIL_AUTH_TOKEN = os.getenv('GMAIL_SERVER_AUTH_TOKEN', 'GmailPass123!@#')
GDRIVE_AUTH_TOKEN = os.getenv('GOOGLE_DRIVE_SERVER_AUTH_TOKEN', 'abhi21dad')
TWITTER_AUTH_TOKEN = os.getenv('AUTH_TOKEN', 'abhi21dad')


class TestHealthEndpoints:
    """Test health check endpoints for all services."""
    
    def test_file_server_health(self):
        """Test file server health endpoint."""
        try:
            response = requests.get(f"{SERVICES['file']}/health", timeout=2)
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'file_server'
            assert 'metrics' in data
        except requests.exceptions.ConnectionError:
            pytest.skip("File server not running")
    
    def test_gmail_server_health(self):
        """Test Gmail server health endpoint."""
        try:
            response = requests.get(f"{SERVICES['gmail']}/health", timeout=2)
            # Accept both 200 (healthy) and 503 (degraded - no token)
            assert response.status_code in [200, 503]
            data = response.json()
            assert data['service'] == 'gmail_server'
            assert 'gmail_token_exists' in data
        except requests.exceptions.ConnectionError:
            pytest.skip("Gmail server not running")


class TestFileServer:
    """Test file server functionality."""
    
    def test_write_and_read_file(self):
        """Test writing and reading a file."""
        try:
            # Write a test file
            write_payload = {
                'token': FILE_AUTH_TOKEN,
                'path': 'test_file.txt',
                'content': 'Hello, World!',
                'mode': 'overwrite'
            }
            
            response = requests.post(
                f"{SERVICES['file']}/write",
                json=write_payload,
                timeout=5
            )
            assert response.status_code == 200
            assert response.json()['success'] is True
            
            # Read the file back
            read_payload = {
                'token': FILE_AUTH_TOKEN,
                'path': 'test_file.txt'
            }
            
            response = requests.post(
                f"{SERVICES['file']}/read",
                json=read_payload,
                timeout=5
            )
            assert response.status_code == 200
            assert response.json()['content'] == 'Hello, World!'
            
        except requests.exceptions.ConnectionError:
            pytest.skip("File server not running")
    
    def test_list_files(self):
        """Test listing files in sandbox."""
        try:
            payload = {
                'token': FILE_AUTH_TOKEN,
                'path': '.'
            }
            
            response = requests.post(
                f"{SERVICES['file']}/list",
                json=payload,
                timeout=5
            )
            assert response.status_code == 200
            assert 'items' in response.json()
            
        except requests.exceptions.ConnectionError:
            pytest.skip("File server not running")
    
    def test_unauthorized_request(self):
        """Test that requests without valid token are rejected."""
        try:
            payload = {
                'token': 'invalid_token',
                'path': '.'
            }
            
            response = requests.post(
                f"{SERVICES['file']}/list",
                json=payload,
                timeout=5
            )
            assert response.status_code == 401
            
        except requests.exceptions.ConnectionError:
            pytest.skip("File server not running")


class TestMetrics:
    """Test that services track metrics properly."""
    
    def test_file_server_metrics(self):
        """Test that file server tracks request metrics."""
        try:
            # Make a few requests
            for _ in range(3):
                requests.get(f"{SERVICES['file']}/health", timeout=2)
            
            # Check metrics
            response = requests.get(f"{SERVICES['file']}/health", timeout=2)
            data = response.json()
            
            assert 'metrics' in data
            assert 'total' in data['metrics']
            assert data['metrics']['total'] >= 4  # At least 4 requests made
            
        except requests.exceptions.ConnectionError:
            pytest.skip("File server not running")


if __name__ == '__main__':
    # Run tests manually
    print("Running integration tests...")
    print("\nNote: Services must be running for tests to pass")
    print("Start services with: python file_command_server1.py (etc.)\n")
    
    pytest.main([__file__, '-v', '--tb=short'])
