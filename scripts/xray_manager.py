#!/usr/bin/env python3
"""Xray core installation and management utility."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request

XRAY_GITHUB_REPO = "XTLS/Xray-core"
DEFAULT_VERSION = "v24.12.18"
INSTALL_DIR = Path.home() / ".local" / "bin"
XRAY_BINARY_NAME = "xray.exe" if platform.system() == "Windows" else "xray"


def get_system_info() -> dict[str, str]:
    """Detect system architecture and OS."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Map Python's platform names to Xray's naming
    os_map = {
        "linux": "linux",
        "darwin": "macos",
        "windows": "windows",
    }
    
    arch_map = {
        "x86_64": "64",
        "amd64": "64",
        "aarch64": "arm64-v8a",
        "arm64": "arm64-v8a",
        "armv7l": "arm32-v7a",
        "i686": "32",
        "i386": "32",
    }
    
    os_name = os_map.get(system, "linux")
    arch_name = arch_map.get(machine, "64")
    
    return {
        "os": os_name,
        "arch": arch_name,
        "system": system,
        "machine": machine,
    }


def get_release_info(version: str = DEFAULT_VERSION) -> dict[str, Any]:
    """Fetch release information from GitHub."""
    url = f"https://api.github.com/repos/{XRAY_GITHUB_REPO}/releases/tags/{version}"
    
    try:
        req = Request(url, headers={"Accept": "application/vnd.github+json"})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch release info: {exc}")


def get_download_url(version: str = DEFAULT_VERSION) -> tuple[str, str]:
    """Get the download URL for the current platform."""
    info = get_system_info()
    release = get_release_info(version)
    
    # Construct filename pattern
    if info["os"] == "windows":
        filename_pattern = f"Xray-windows-{info['arch']}.zip"
    elif info["os"] == "macos":
        filename_pattern = f"Xray-macos-{info['arch']}.zip"
    else:
        filename_pattern = f"Xray-linux-{info['arch']}.zip"
    
    # Find matching asset
    for asset in release.get("assets", []):
        if asset["name"] == filename_pattern:
            return asset["browser_download_url"], filename_pattern
    
    raise RuntimeError(
        f"No release found for {info['os']} {info['arch']}. "
        f"Looking for: {filename_pattern}"
    )


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """Download file with progress."""
    print(f"Downloading: {url}")
    
    req = Request(url, headers={"User-Agent": "xray-manager/1.0"})
    
    with urlopen(req, timeout=30) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\rProgress: {progress:.1f}%", end="", flush=True)
        
        print()  # New line after progress


def verify_checksum(file_path: Path, expected_hash: str | None = None) -> bool:
    """Verify file checksum (SHA256)."""
    if not expected_hash:
        return True
    
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    computed = sha256.hexdigest()
    return computed.lower() == expected_hash.lower()


def extract_xray_binary(archive_path: Path, dest_dir: Path) -> Path:
    """Extract Xray binary from downloaded archive."""
    print(f"Extracting to: {dest_dir}")
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(archive_path, "r") as zf:
        # Find xray binary in archive
        binary_name = XRAY_BINARY_NAME
        
        for name in zf.namelist():
            if name.endswith(binary_name) or name == binary_name:
                # Extract to temp location first
                temp_path = dest_dir / f"{binary_name}.tmp"
                with zf.open(name) as source, open(temp_path, "wb") as target:
                    target.write(source.read())
                
                # Move to final location
                final_path = dest_dir / binary_name
                if final_path.exists():
                    final_path.unlink()
                temp_path.rename(final_path)
                
                # Make executable on Unix
                if platform.system() != "Windows":
                    final_path.chmod(0o755)
                
                print(f"Installed: {final_path}")
                return final_path
    
    raise RuntimeError("Xray binary not found in archive")


def find_xray_binary() -> Path | None:
    """Find existing Xray binary in system."""
    # Check environment variable
    env_path = os.getenv("XRAY_BIN")
    if env_path:
        path = Path(env_path)
        if path.exists() and path.is_file():
            return path
    
    # Check common locations
    search_paths = [
        INSTALL_DIR / XRAY_BINARY_NAME,
        Path("/usr/local/bin") / XRAY_BINARY_NAME,
        Path("/usr/bin") / XRAY_BINARY_NAME,
        Path.home() / ".xray" / XRAY_BINARY_NAME,
    ]
    
    for path in search_paths:
        if path.exists() and path.is_file():
            return path
    
    # Check PATH
    which_result = shutil.which("xray")
    if which_result:
        return Path(which_result)
    
    return None


def get_xray_version(binary_path: Path) -> str | None:
    """Get version of installed Xray binary."""
    try:
        result = subprocess.run(
            [str(binary_path), "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0:
            # Parse version from output
            for line in result.stdout.splitlines():
                if "Xray" in line and "v" in line:
                    return line.strip()
        
        return None
    except Exception:
        return None


def install_xray(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Download and install Xray binary."""
    # Check if already installed
    existing = find_xray_binary()
    if existing and not force:
        installed_version = get_xray_version(existing)
        print(f"Xray already installed: {existing}")
        if installed_version:
            print(f"Version: {installed_version}")
        return existing
    
    print(f"Installing Xray {version}...")
    
    # Get download URL
    download_url, filename = get_download_url(version)
    
    # Download to temp directory
    with tempfile.TemporaryDirectory(prefix="xray-install-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        archive_path = tmpdir_path / filename
        
        download_file(download_url, archive_path)
        
        # Extract and install
        binary_path = extract_xray_binary(archive_path, INSTALL_DIR)
        
        # Verify installation
        installed_version = get_xray_version(binary_path)
        if installed_version:
            print(f"Successfully installed: {installed_version}")
        else:
            print("Warning: Could not verify installed version")
        
        return binary_path


def uninstall_xray() -> bool:
    """Remove installed Xray binary."""
    binary_path = find_xray_binary()
    
    if not binary_path:
        print("Xray not found")
        return False
    
    try:
        binary_path.unlink()
        print(f"Uninstalled: {binary_path}")
        return True
    except Exception as exc:
        print(f"Failed to uninstall: {exc}")
        return False


def check_xray_installation() -> dict[str, Any]:
    """Check current Xray installation status."""
    binary_path = find_xray_binary()
    
    if not binary_path:
        return {
            "installed": False,
            "path": None,
            "version": None,
        }
    
    version = get_xray_version(binary_path)
    
    return {
        "installed": True,
        "path": str(binary_path),
        "version": version,
    }


def main():
    """CLI for Xray manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install Xray")
    install_parser.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help=f"Xray version to install (default: {DEFAULT_VERSION})",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if already installed",
    )
    
    # Check command
    subparsers.add_parser("check", help="Check installation status")
    
    # Version command
    subparsers.add_parser("version", help="Show installed version")
    
    # Uninstall command
    subparsers.add_parser("uninstall", help="Remove Xray")
    
    args = parser.parse_args()
    
    if args.command == "install":
        try:
            binary_path = install_xray(
                version=args.version,
                force=args.force,
            )
            print(f"\nXray binary: {binary_path}")
            print(f"Add to PATH: export XRAY_BIN={binary_path}")
        except Exception as exc:
            print(f"Installation failed: {exc}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "check":
        status = check_xray_installation()
        print(json.dumps(status, indent=2))
        sys.exit(0 if status["installed"] else 1)
    
    elif args.command == "version":
        binary_path = find_xray_binary()
        if not binary_path:
            print("Xray not installed", file=sys.stderr)
            sys.exit(1)
        version = get_xray_version(binary_path)
        if version:
            print(version)
        else:
            print("Could not determine version", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "uninstall":
        success = uninstall_xray()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()