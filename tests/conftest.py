"""
Pytest configuration and fixtures for k29photo tests.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add k29photo module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'k29photo'))


@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-insecure'
    os.environ['WTF_CSRF_ENABLED'] = 'False'  # Disable CSRF in tests
    
    from app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    return app


@pytest.fixture
def client(app):
    """Test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner for the Flask app."""
    return app.test_cli_runner()


@pytest.fixture
def mock_db():
    """Mock database connection and cursor."""
    mock_cursor = MagicMock()
    mock_db_conn = MagicMock()
    mock_db_conn.cursor.return_value = mock_cursor
    
    return {
        'cursor': mock_cursor,
        'connection': mock_db_conn
    }


@pytest.fixture
def mock_flask_g(mock_db):
    """Mock Flask g object with database."""
    mock_g = MagicMock()
    mock_g.db = mock_db['connection']
    
    return mock_g


@pytest.fixture
def test_user_data():
    """Sample test user data."""
    return {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'password': 'SecurePass123',
        'dob': '1990-01-15',
        'hometown': 'Athens',
        'gender': 'M'
    }


@pytest.fixture
def test_user_weak_password():
    """Test user with weak password."""
    return {
        'first_name': 'Jane',
        'last_name': 'Smith',
        'email': 'jane.smith@example.com',
        'password': 'weak',  # Too short, no digit
        'gender': 'F'
    }


@pytest.fixture
def test_user_invalid_email():
    """Test user with invalid email."""
    return {
        'first_name': 'Invalid',
        'last_name': 'User',
        'email': 'not-an-email',
        'password': 'ValidPass123',
        'gender': 'M'
    }
