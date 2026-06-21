"""
Tests for security module — input validation, sanitization, password validation.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'k29photo'))

from security import (
    sanitize_string,
    sanitize_email,
    sanitize_filename,
    validate_password,
    validate_tags
)


class TestSanitizeString:
    """Tests for string sanitization function."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_basic_string(self):
        """Test basic string sanitization."""
        result = sanitize_string("  hello world  ")
        assert result == "hello world"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_html_escaping(self):
        """Test HTML special characters are escaped."""
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_null_bytes(self):
        """Test null bytes are removed."""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_max_length(self):
        """Test max length enforcement."""
        result = sanitize_string("abcdefghijklmnop", max_length=5)
        assert len(result) == 5
        assert result == "abcde"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_non_string_input(self):
        """Test non-string input returns empty string."""
        result = sanitize_string(None)
        assert result == ""
        assert isinstance(result, str)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_sql_injection_attempt(self):
        """Test SQL injection patterns are escaped."""
        result = sanitize_string("'; DROP TABLE users; --")
        assert "&quot;" in result or "&apos;" in result
        assert "DROP TABLE" in result  # Escaped, not executed


class TestSanitizeEmail:
    """Tests for email sanitization and validation."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_email(self):
        """Test valid email is accepted."""
        result = sanitize_email("user@example.com")
        assert result == "user@example.com"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_email_lowercase_conversion(self):
        """Test email is converted to lowercase."""
        result = sanitize_email("User@Example.COM")
        assert result == "user@example.com"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_invalid_email_no_at_sign(self):
        """Test email without @ is rejected."""
        result = sanitize_email("notanemail.com")
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_invalid_email_no_domain(self):
        """Test email without domain is rejected."""
        result = sanitize_email("user@")
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_invalid_email_spaces(self):
        """Test email with spaces is rejected."""
        result = sanitize_email("user @example.com")
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_empty_email(self):
        """Test empty email is rejected."""
        result = sanitize_email("")
        assert result is None


class TestSanitizeFilename:
    """Tests for filename sanitization."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_filename(self):
        """Test valid filename is preserved."""
        result = sanitize_filename("photo.jpg")
        assert result == "photo.jpg"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_path_traversal_prevention_slash(self):
        """Test path traversal with forward slashes is blocked."""
        result = sanitize_filename("../../etc/passwd")
        assert result == "passwd"
        assert "../" not in result
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_path_traversal_prevention_backslash(self):
        """Test path traversal with backslashes is blocked."""
        result = sanitize_filename("..\\..\\windows\\system32")
        assert "..\\" not in result
        assert "system32" in result
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_special_characters_removal(self):
        """Test special characters are removed."""
        result = sanitize_filename("photo<script>.jpg")
        assert "<" not in result
        assert ">" not in result
        assert "script" in result
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_filename_length_limit(self):
        """Test filename is truncated to 255 chars."""
        long_name = "a" * 300 + ".jpg"
        result = sanitize_filename(long_name)
        assert len(result) <= 255


class TestValidatePassword:
    """Tests for password validation."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_strong_password(self):
        """Test valid strong password is accepted."""
        valid, msg = validate_password("SecurePass123")
        assert valid is True
        assert msg == ""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_password_too_short(self):
        """Test short password is rejected."""
        valid, msg = validate_password("Pass1")
        assert valid is False
        assert "8 characters" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_password_no_uppercase(self):
        """Test password without uppercase is rejected."""
        valid, msg = validate_password("securepass123")
        assert valid is False
        assert "uppercase" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_password_no_lowercase(self):
        """Test password without lowercase is rejected."""
        valid, msg = validate_password("SECUREPASS123")
        assert valid is False
        assert "lowercase" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_password_no_digit(self):
        """Test password without digit is rejected."""
        valid, msg = validate_password("SecurePassword")
        assert valid is False
        assert "digit" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_password_multiple_requirements_missing(self):
        """Test error message when multiple requirements missing."""
        valid, msg = validate_password("pass")
        assert valid is False
        # Should fail on first check (length)
        assert len(msg) > 0


class TestValidateTags:
    """Tests for tag validation."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_tags(self):
        """Test valid tags are accepted."""
        valid, msg, tags = validate_tags("nature photography landscape")
        assert valid is True
        assert msg == ""
        assert "nature" in tags
        assert "photography" in tags
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_tags_converted_to_lowercase(self):
        """Test tags are converted to lowercase."""
        valid, msg, tags = validate_tags("Nature PHOTOGRAPHY")
        assert valid is True
        assert "nature" in tags
        assert "photography" in tags
        assert "PHOTOGRAPHY" not in tags
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_tags_duplicates_removed(self):
        """Test duplicate tags are removed."""
        valid, msg, tags = validate_tags("nature nature photography")
        assert valid is True
        assert tags.count("nature") == 1
        assert len(tags) == 2
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_tags_invalid_characters(self):
        """Test tags with invalid characters are rejected."""
        valid, msg, tags = validate_tags("nature <script> photography")
        assert valid is False
        assert "lowercase letters, numbers, and hyphens" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_tags_max_length_single_tag(self):
        """Test single tag length limit."""
        long_tag = "a" * 51
        valid, msg, tags = validate_tags(long_tag)
        assert valid is False
        assert "50 characters" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_tags_max_count(self):
        """Test max number of tags (10)."""
        tag_string = " ".join([f"tag{i}" for i in range(15)])
        valid, msg, tags = validate_tags(tag_string)
        assert valid is False
        assert "Maximum 10 tags" in msg
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_empty_tags_string(self):
        """Test empty tag string returns empty list."""
        valid, msg, tags = validate_tags("")
        assert valid is True
        assert tags == []
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_tags_with_hyphens(self):
        """Test tags with hyphens are accepted."""
        valid, msg, tags = validate_tags("high-quality vintage-photo")
        assert valid is True
        assert "high-quality" in tags
        assert "vintage-photo" in tags


class TestSecurityIntegration:
    """Integration tests for security functions."""
    
    @pytest.mark.integration
    @pytest.mark.security
    def test_xss_prevention_in_html_output(self):
        """Test that XSS attempts are escaped."""
        malicious = "<img src=x onerror=alert('xss')>"
        sanitized = sanitize_string(malicious)
        
        # Should not contain executable script
        assert "onerror=" not in sanitized
        assert "<img" not in sanitized
        assert "&lt;img" in sanitized
    
    @pytest.mark.integration
    @pytest.mark.security
    def test_email_and_string_sanitization_together(self):
        """Test email and string sanitization work together."""
        email = sanitize_email("  USER@EXAMPLE.COM  ")
        name = sanitize_string("  John Doe  ")
        
        assert email == "user@example.com"
        assert name == "John Doe"
