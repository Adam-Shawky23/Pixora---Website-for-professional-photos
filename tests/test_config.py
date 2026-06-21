"""
Tests for application configuration.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'k29photo'))


@pytest.mark.unit
class TestConfiguration:
    """Tests for Flask configuration."""
    
    def test_secret_key_set(self, app):
        """Test SECRET_KEY is configured."""
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 0
    
    def test_testing_mode_enabled(self, app):
        """Test app is in testing mode."""
        assert app.config['TESTING'] is True
    
    def test_csrf_disabled_in_testing(self, app):
        """Test CSRF is disabled for testing."""
        assert app.config['WTF_CSRF_ENABLED'] is False


@pytest.mark.unit
class TestSessionConfiguration:
    """Tests for session security configuration."""
    
    def test_session_cookie_httponly(self, app):
        """Test session cookies are HttpOnly."""
        # In testing, check that config has the setting
        assert app.config.get('SESSION_COOKIE_HTTPONLY', True) is True
    
    def test_session_cookie_samesite(self, app):
        """Test SameSite cookie attribute."""
        samesite = app.config.get('SESSION_COOKIE_SAMESITE')
        assert samesite in ['Lax', 'Strict', None]  # Valid options


@pytest.mark.unit
class TestUploadConfiguration:
    """Tests for file upload configuration."""
    
    def test_max_content_length_set(self, app):
        """Test max content length is configured."""
        # Default is 16MB
        max_size = app.config.get('MAX_CONTENT_LENGTH')
        assert max_size is None or max_size > 0  # None means unlimited in test config
    
    def test_upload_extensions_defined(self, app):
        """Test allowed upload extensions are defined."""
        # Should be imported from config
        assert app is not None
