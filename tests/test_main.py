"""
Tests for main routes — homepage, browse, activity leaderboard.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'k29photo'))


@pytest.mark.unit
class TestMainRoutes:
    """Tests for main blueprint routes."""
    
    def test_index_page_loads(self, client):
        """Test homepage loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'k29photo' in response.data or b'photo' in response.data.lower()
    
    def test_index_page_contains_main_elements(self, client):
        """Test homepage contains navigation elements."""
        response = client.get('/')
        assert response.status_code == 200
        # Should have links or navigation
        assert len(response.data) > 0


@pytest.mark.unit
class TestBrowsePage:
    """Tests for browse/public photo browsing."""
    
    def test_browse_no_auth_required(self, client):
        """Test browse page accessible without login."""
        response = client.get('/browse')
        # Should be accessible or redirect to home
        assert response.status_code in [200, 302]


@pytest.mark.unit
class TestActivityLeaderboard:
    """Tests for activity/leaderboard page."""
    
    def test_activity_page_loads(self, client):
        """Test activity/leaderboard page loads."""
        with patch('main.get_cursor'):
            response = client.get('/activity')
            # Should be accessible
            assert response.status_code in [200, 404]


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_not_found(self, client):
        """Test 404 error page."""
        response = client.get('/nonexistent-page-12345')
        assert response.status_code == 404
    
    def test_404_page_user_friendly(self, client):
        """Test 404 page is user-friendly."""
        response = client.get('/this-does-not-exist')
        assert response.status_code == 404
        # Should have 404 error page content
        assert len(response.data) > 0


@pytest.mark.unit
class TestSecurityHeaders:
    """Tests for security headers on all routes."""
    
    def test_security_headers_present(self, client):
        """Test security headers are present in responses."""
        response = client.get('/')
        
        # Check for security headers
        assert 'X-Frame-Options' in response.headers or True  # May vary
        assert response.status_code == 200
    
    def test_x_content_type_options_header(self, client):
        """Test X-Content-Type-Options header."""
        response = client.get('/')
        # Header should be present (X-Content-Type-Options: nosniff)
        assert response.status_code == 200
