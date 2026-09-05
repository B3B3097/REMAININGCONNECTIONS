 #!/usr/bin/env python3
"""
System integration test for REMAININGCONNECTIONS.
Tests all components locally before deployment.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

def print_header(text: str):
    """Print formatted header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_status(text: str, status: bool):
    """Print status line."""
    icon = "✓" if status else "✗"
    print(f"  [{icon}] {text}")

def test_project_structure():
    """Test if all required files exist."""
    print_header("Testing Project Structure")
    
    required_files = [
        'requirements.txt',
        'README.md',
        'scripts/extract_tg_proxies.py',
        'scripts/extract_http_socks_proxies.py',
        'scripts/validate_http_socks_proxies.py',
        'scripts/check_tg_proxies.py',
        'scripts/generate_summary.py',
        'scripts/export_formats.py',
        'scripts/health_check.py',
        '.github/workflows/subscription-discovery.yml',
        '.github/workflows/tg-proxy-discovery.yml',
        '.github/workflows/http-socks-discovery.yml',
        '.github/workflows/utils-discovery.yml',
        '.github/workflows/generate-summary.yml',
        '.github/workflows/export-formats.yml',
        '.github/workflows/health-monitor.yml',
    ]
    
    all_exist = True
    for filepath in required_files:
        exists = Path(filepath).exists()
        print_status(filepath, exists)
        if not exists:
            all_exist = False
    
    return all_exist

def test_dependencies():
    """Test if all dependencies can be imported."""
    print_header("Testing Dependencies")
    
    dependencies = [
        ('yaml', 'PyYAML'),
        ('requests', 'requests'),
        ('aiohttp', 'aiohttp'),
        ('aiohttp_socks', 'aiohttp-socks'),
    ]
    
    all_imported = True
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print_status(f"{package_name}", True)
        except ImportError:
            print_status(f"{package_name} (missing)", False)
            all_imported = False
    
    return all_imported

def test_data_structure():
    """Test if data directory and files are properly structured."""
    print_header("Testing Data Structure")
    
    os.makedirs('data', exist_ok=True)
    os.makedirs('extracted', exist_ok=True)
    os.makedirs('checked', exist_ok=True)
    
    data_files = [
        'data/subscriptions_found.json',
        'data/tg_proxies_found.json',
        'data/http_proxies_found.json',
        'data/socks_proxies_found.json',
        'data/utils_found.json',
    ]
    
    all_valid = True
    for filepath in data_files:
        if not Path(filepath).exists():
            # Create empty file
            with open(filepath, 'w') as f:
                json.dump({
                    'generated_at': '2024-01-01T00:00:00Z',
                    'proxies': []
                }, f, indent=2)
            print_status(f"{filepath} (created)", True)
        else:
            try:
                with open(filepath, 'r') as f:
                    json.load(f)
                print_status(f"{filepath} (valid)", True)
            except json.JSONDecodeError:
                print_status(f"{filepath} (invalid JSON)", False)
                all_valid = False
    
    return all_valid

def test_scripts_syntax():
    """Test if all Python scripts have valid syntax."""
    print_header("Testing Script Syntax")
    
    scripts = [
        'scripts/extract_tg_proxies.py',
        'scripts/extract_http_socks_proxies.py',
        'scripts/validate_http_socks_proxies.py',
        'scripts/check_tg_proxies.py',
        'scripts/generate_summary.py',
        'scripts/export_formats.py',
        'scripts/health_check.py',
    ]
    
    all_valid = True
    for script in scripts:
        if not Path(script).exists():
            print_status(f"{script} (missing)", False)
            all_valid = False
            continue
        
        try:
            with open(script, 'r') as f:
                compile(f.read(), script, 'exec')
            print_status(f"{script}", True)
        except SyntaxError as e:
            print_status(f"{script} (syntax error: {e})", False)
            all_valid = False
    
    return all_valid

def test_workflows_syntax():
    """Test if all workflow files are valid YAML."""
    print_header("Testing Workflow Syntax")
    
    import yaml
    
    workflows = list(Path('.github/workflows').glob('*.yml'))
    
    all_valid = True
    for workflow in workflows:
        try:
            with open(workflow, 'r') as f:
                yaml.safe_load(f)
            print_status(f"{workflow.name}", True)
        except yaml.YAMLError as e:
            print_status(f"{workflow.name} (YAML error: {e})", False)
            all_valid = False
    
    return all_valid

def run_quick_functionality_test():
    """Run quick functionality tests."""
    print_header("Testing Core Functionality")
    
    tests_passed = True
    
    # Test summary generation
    try:
        import subprocess
        result = subprocess.run(
            ['python', 'scripts/generate_summary.py'],
            capture_output=True,
            timeout=10
        )
        print_status("Summary generation", result.returncode == 0)
        if result.returncode != 0:
            tests_passed = False
    except Exception as e:
        print_status(f"Summary generation (error: {e})", False)
        tests_passed = False
    
    # Test health check
    try:
        result = subprocess.run(
            ['python', 'scripts/health_check.py'],
            capture_output=True,
            timeout=10
        )
        print_status("Health check", result.returncode in [0, 1])  # 0 or 1 are valid
        if result.returncode not in [0, 1]:
            tests_passed = False
    except Exception as e:
        print_status(f"Health check (error: {e})", False)
        tests_passed = False
    
    # Test export formats
    try:
        result = subprocess.run(
            ['python', 'scripts/export_formats.py'],
            capture_output=True,
            timeout=10
        )
        print_status("Export formats", result.returncode == 0)
        if result.returncode != 0:
            tests_passed = False
    except Exception as e:
        print_status(f"Export formats (error: {e})", False)
        tests_passed = False
    
    return tests_passed

def main():
    """Run all tests."""
    print("\n" + "█"*60)
    print("  REMAININGCONNECTIONS - System Integration Test")
    print("█"*60)
    
    results = {
        'Project Structure': test_project_structure(),
        'Dependencies': test_dependencies(),
        'Data Structure': test_data_structure(),
        'Script Syntax': test_scripts_syntax(),
        'Workflow Syntax': test_workflows_syntax(),
        'Functionality': run_quick_functionality_test(),
    }
    
    # Print summary
    print_header("Test Summary")
    
    all_passed = True
    for test_name, passed in results.items():
        print_status(test_name, passed)
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("  ✅ All tests passed!")
        print("="*60)
        return 0
    else:
        print("  ❌ Some tests failed!")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())