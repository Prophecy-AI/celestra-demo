"""Tests for PathValidator"""
import pytest
import tempfile
import os
from pathlib import Path
from security.path_validator import PathValidator, SecurityError


def test_validate_absolute_path_in_workspace():
    """Test 1: Absolute path within workspace is allowed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)
        test_path = os.path.join(tmpdir, "test.txt")

        result = validator.validate(test_path, "read")

        assert result == os.path.realpath(test_path)
        assert result.startswith(os.path.realpath(tmpdir))


def test_validate_relative_path_in_workspace():
    """Test 2: Relative path is resolved within workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)

        result = validator.validate("test.txt", "write")

        assert result == os.path.realpath(os.path.join(tmpdir, "test.txt"))
        assert result.startswith(os.path.realpath(tmpdir))


def test_validate_rejects_parent_directory_escape():
    """Test 3: Parent directory escape with .. is blocked"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)

        with pytest.raises(SecurityError) as exc_info:
            validator.validate("../../../etc/passwd", "read")

        assert "Access denied" in str(exc_info.value)
        assert "outside workspace" in str(exc_info.value)


def test_validate_rejects_absolute_path_outside():
    """Test 4: Absolute path outside workspace is blocked"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)

        with pytest.raises(SecurityError) as exc_info:
            validator.validate("/etc/passwd", "read")

        assert "Access denied" in str(exc_info.value)


def test_validate_rejects_symlink_escape():
    """Test 5: Symlink pointing outside workspace is blocked"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)

        # Create symlink to /etc
        symlink_path = os.path.join(tmpdir, "escape_link")
        os.symlink("/etc", symlink_path)

        with pytest.raises(SecurityError) as exc_info:
            validator.validate(os.path.join(symlink_path, "passwd"), "read")

        assert "Access denied" in str(exc_info.value)


def test_validate_with_dotdot_sequences():
    """Test 6: Multiple .. sequences are resolved correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)

        # Create nested directory
        nested = os.path.join(tmpdir, "a", "b", "c")
        os.makedirs(nested, exist_ok=True)

        # This should resolve back to workspace but still valid
        result = validator.validate(os.path.join(nested, "..", "..", "..", "test.txt"), "read")

        assert result == os.path.realpath(os.path.join(tmpdir, "test.txt"))


def test_validate_error_message_format():
    """Test 7: Error message contains helpful information"""
    with tempfile.TemporaryDirectory() as tmpdir:
        validator = PathValidator(tmpdir)

        with pytest.raises(SecurityError) as exc_info:
            validator.validate("/etc/passwd", "delete")

        error_msg = str(exc_info.value)
        assert "delete" in error_msg  # Operation name
        assert "/etc/passwd" in error_msg  # Attempted path
        assert tmpdir in error_msg  # Workspace path
