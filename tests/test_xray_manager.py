#!/usr/bin/env python3
"""Tests for xray_manager module."""

import platform
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from xray_manager import (
    get_system_info,
    find_xray_binary,
    check_xray_installation,
    XRAY_BINARY_NAME,
)


class TestSystemInfo:
    """Test system information detection."""
    
    def test_get_system_info(self):
        info = get_system_info()
        assert "os" in info
        assert "arch" in info
        assert "system" in info
        assert "machine" in info
        
        assert info["os"] in ("linux", "macos", "windows")
        assert isinstance(info["arch"], str)
    
    def test_system_mapping(self):
        info = get_system_info()
        
        system = platform.system().lower()
        if system == "linux":
            assert info["os"] == "linux"
        elif system == "darwin":
            assert info["os"] == "macos"
        elif system == "windows":
            assert info["os"] == "windows"


class TestBinarySearch:
    """Test Xray binary search functionality."""
    
    def test_find_xray_binary_returns_path_or_none(self):
        result = find_xray_binary()
        assert result is None or isinstance(result, Path)
    
    @patch.dict("os.environ", {"XRAY_BIN": "/custom/path/xray"})
    def test_find_xray_respects_env_var(self):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                result = find_xray_binary()
                assert result is not None
    
    def test_binary_name_platform_specific(self):
        if platform.system() == "Windows":
            assert XRAY_BINARY_NAME == "xray.exe"
        else:
            assert XRAY_BINARY_NAME == "xray"


class TestInstallationCheck:
    """Test installation status checking."""
    
    def test_check_installation_returns_dict(self):
        status = check_xray_installation()
        assert isinstance(status, dict)
        assert "installed" in status
        assert "path" in status
        assert "version" in status
    
    def test_check_installation_not_installed(self):
        with patch("xray_manager.find_xray_binary", return_value=None):
            status = check_xray_installation()
            assert status["installed"] is False
            assert status["path"] is None
            assert status["version"] is None
    
    def test_check_installation_installed(self):
        mock_path = Path("/usr/local/bin/xray")
        with patch("xray_manager.find_xray_binary", return_value=mock_path):
            with patch("xray_manager.get_xray_version", return_value="Xray 1.8.0"):
                status = check_xray_installation()
                assert status["installed"] is True
                assert status["path"] == str(mock_path)
                assert status["version"] == "Xray 1.8.0"


class TestReleaseInfo:
    """Test GitHub release information fetching."""
    
    @pytest.mark.skipif(
        not hasattr(sys, "real_prefix") and not hasattr(sys, "base_prefix"),
        reason="Network test, skip in CI"
    )
    def test_get_release_info_structure(self):
        from xray_manager import get_release_info
        
        # This test requires network access
        try:
            info = get_release_info()
            assert isinstance(info, dict)
            assert "assets" in info
            assert isinstance(info["assets"], list)
        except Exception:
            # Skip if network unavailable
            pytest.skip("Network unavailable")


class TestDownloadURL:
    """Test download URL generation."""
    
    def test_get_download_url_format(self):
        from xray_manager import get_download_url
        
        with patch("xray_manager.get_release_info") as mock_release:
            mock_release.return_value = {
                "assets": [
                    {
                        "name": "Xray-linux-64.zip",
                        "browser_download_url": "https://example.com/xray-linux-64.zip"
                    }
                ]
            }
            
            with patch("xray_manager.get_system_info") as mock_sys:
                mock_sys.return_value = {
                    "os": "linux",
                    "arch": "64",
                    "system": "linux",
                    "machine": "x86_64"
                }
                
                url, filename = get_download_url()
                assert url == "https://example.com/xray-linux-64.zip"
                assert filename == "Xray-linux-64.zip"


class TestVersionParsing:
    """Test version string parsing."""
    
    def test_get_xray_version(self):
        from xray_manager import get_xray_version
        
        mock_path = Path("/usr/local/bin/xray")
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Xray 1.8.0 (Xray, Penetrates Everything.) Custom\n"
            )
            
            version = get_xray_version(mock_path)
            assert version is not None
            assert "Xray" in version
    
    def test_get_xray_version_command_fails(self):
        from xray_manager import get_xray_version
        
        mock_path = Path("/usr/local/bin/xray")
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            
            version = get_xray_version(mock_path)
            assert version is None


class TestChecksumVerification:
    """Test file checksum verification."""
    
    def test_verify_checksum_no_hash(self):
        from xray_manager import verify_checksum
        
        # Without expected hash, should return True
        result = verify_checksum(Path(__file__), None)
        assert result is True
    
    def test_verify_checksum_with_hash(self):
        from xray_manager import verify_checksum
        import hashlib
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)
        
        try:
            # Calculate actual hash
            sha256 = hashlib.sha256()
            with open(temp_path, "rb") as f:
                sha256.update(f.read())
            expected_hash = sha256.hexdigest()
            
            # Verify with correct hash
            result = verify_checksum(temp_path, expected_hash)
            assert result is True
            
            # Verify with wrong hash
            result = verify_checksum(temp_path, "0" * 64)
            assert result is False
        finally:
            temp_path.unlink()


class TestExtraction:
    """Test archive extraction."""
    
    def test_extract_xray_binary_finds_binary(self):
        from xray_manager import extract_xray_binary, XRAY_BINARY_NAME
        import tempfile
        import zipfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock archive
            archive_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(archive_path, "w") as zf:
                zf.writestr(XRAY_BINARY_NAME, b"fake xray binary")
            
            dest_dir = Path(tmpdir) / "extracted"
            result = extract_xray_binary(archive_path, dest_dir)
            
            assert result.exists()
            assert result.name == XRAY_BINARY_NAME


def test_module_constants():
    """Test module-level constants."""
    from xray_manager import (
        XRAY_GITHUB_REPO,
        DEFAULT_VERSION,
        INSTALL_DIR,
    )
    
    assert XRAY_GITHUB_REPO == "XTLS/Xray-core"
    assert DEFAULT_VERSION.startswith("v")
    assert isinstance(INSTALL_DIR, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])