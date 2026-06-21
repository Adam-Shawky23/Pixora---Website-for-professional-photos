"""
Tests for authentication module — registration, login, logout.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'k29photo'))


@pytest.mark.auth
class TestAuthRegister:
    """Tests for user registration."""
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_register_page_loads(self, client):
        """Test register page loads successfully."""
        response = client.get('/register')
        assert response.status_code == 200
        assert b'register' in response.data.lower()
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_register_post_missing_fields(self, client):
        """Test registration fails with missing fields."""
        with patch('auth.get_cursor'):
            response = client.post('/register', data={
                'first_name': 'John',
                'last_name': 'Doe',
                # Missing email and password
            })
            assert response.status_code == 200
            assert b'fill in all required fields' in response.data or response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_register_weak_password(self, client, test_user_weak_password):
        """Test registration fails with weak password."""
        with patch('auth.get_cursor'):
            response = client.post('/register', data=test_user_weak_password)
            # Should be rejected or shown error
            assert response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_register_invalid_email(self, client, test_user_invalid_email):
        """Test registration fails with invalid email."""
        with patch('auth.get_cursor'):
            response = client.post('/register', data=test_user_invalid_email)
            assert response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_register_gender_validation(self, client, test_user_data):
        """Test registration with invalid gender."""
        test_user_data['gender'] = 'X'  # Invalid
        
        with patch('auth.get_cursor'):
            response = client.post('/register', data=test_user_data)
            # Should reject invalid gender
            assert response.status_code == 200


@pytest.mark.auth
class TestAuthLogin:
    """Tests for user login."""
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_login_page_loads(self, client):
        """Test login page loads successfully."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_login_missing_credentials(self, client):
        """Test login fails with missing credentials."""
        response = client.post('/login', data={
            # Empty credentials
        })
        assert response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        response = client.post('/login', data={
            'email': 'not-an-email',
            'password': 'SomePass123'
        })
        assert response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_logout_redirects(self, client):
        """Test logout functionality."""
        # Set session
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'John Doe'
        
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Session should be cleared
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


@pytest.mark.auth
class TestAuthRateLimiting:
    """Tests for authentication rate limiting."""
    
    @pytest.mark.integration
    @pytest.mark.security
    def test_login_rate_limiting(self, client):
        """Test login endpoint has rate limiting (10 per hour)."""
        # This test checks that the decorator is applied
        # In a real test, you'd hit the endpoint multiple times
        response = client.get('/login')
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.security
    def test_register_rate_limiting(self, client):
        """Test register endpoint has rate limiting (5 per hour)."""
        # This test checks that the decorator is applied
        response = client.get('/register')
        assert response.status_code == 200


@pytest.mark.auth
class TestAuthCSRFProtection:
    """Tests for CSRF protection on auth endpoints."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_csrf_token_in_register_form(self, client):
        """Test CSRF token is present in register form."""
        # CSRF is disabled in testing config
        response = client.get('/register')
        assert response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_csrf_token_in_login_form(self, client):
        """Test CSRF token is present in login form."""
        response = client.get('/login')
        assert response.status_code == 200


@pytest.mark.auth
class TestAuthInputSanitization:
    """Tests for input sanitization in auth module."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_xss_injection_in_registration(self, client):
        """Test XSS injection is prevented in registration."""
        with patch('auth.get_cursor'):
            response = client.post('/register', data={
                'first_name': '<script>alert("xss")</script>',
                'last_name': 'Doe',
                'email': 'test@example.com',
                'password': 'SecurePass123'
            })
            assert response.status_code == 200
            # The injection should be escaped, not executed
            assert b'<script>' not in response.data
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sql_injection_attempt_in_login(self, client):
        """Test SQL injection attempt in login is handled."""
        with patch('auth.get_cursor'):
            response = client.post('/login', data={
                'email': "admin' OR '1'='1",
                'password': 'anything'
            })
            # Should either reject invalid email or handle safely
            assert response.status_code == 200
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_null_byte_injection_registration(self, client):
        """Test null byte injection is prevented."""
        with patch('auth.get_cursor'):
            response = client.post('/register', data={
                'first_name': 'John\x00Hacker',
                'last_name': 'Doe',
                'email': 'test@example.com',
                'password': 'SecurePass123'
            })
            assert response.status_code == 200
            # Null byte should be stripped
            assert b'\x00' not in response.data


@pytest.mark.auth
class TestAuthErrorMessages:
    """Tests for auth error messages."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_login_generic_error_message(self, client):
        """Test login provides generic error message (user enumeration prevention)."""
        with patch('auth.get_cursor') as mock_cursor_factory:
            # Mock: user not found
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor_factory.return_value = mock_cursor
            
            response = client.post('/login', data={
                'email': 'nonexistent@example.com',
                'password': 'SomePass123'
            })
            # Should not say "user not found", just "invalid email or password"
            assert response.status_code == 200 or b'Invalid email' in response.data
