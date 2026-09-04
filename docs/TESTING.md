# Testing Guide for REMAININGCONNECTIONS

This document describes the testing infrastructure and how to run tests for the REMAININGCONNECTIONS project.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Coverage](#coverage)
- [CI/CD Integration](#cicd-integration)

## Overview

The project uses `pytest` as the testing framework with support for:
- Unit tests
- Integration tests
- Async tests (using pytest-asyncio)
- Network tests
- Mock/stub testing

## Test Structure

```
tests/
├── __init__.py
├── test_strict_proxy_checker.py      # Tests for proxy checking
├── test_mtproto_checker.py           # Tests for MTProto validation
├── test_subscription_validator.py    # Tests for subscription parsing
├── test_xray_manager.py              # Tests for Xray installation
├── test_config_exporter.py           # Tests for config export
└── conftest.py                       # Shared fixtures (to be created)
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_strict_proxy_checker.py
```

### Run Specific Test Class or Function

```bash
# Run a specific class
pytest tests/test_strict_proxy_checker.py::TestHostValidation

# Run a specific test
pytest tests/test_strict_proxy_checker.py::TestHostValidation::test_valid_ipv4
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=scripts --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Run Tests in Parallel

```bash
pytest -n auto
```

### Run Only Fast Tests

```bash
pytest -m "not slow"
```

## Test Categories

Tests are organized using pytest markers:

### Unit Tests

```bash
pytest -m unit
```

Fast, isolated tests that don't require external dependencies.

### Integration Tests

```bash
pytest -m integration
```

Tests that verify interaction between components.

### Network Tests

```bash
pytest -m network
```

Tests that require internet connectivity. Skipped in offline environments.

### Smoke Tests

```bash
pytest -m smoke
```

Quick validation tests to ensure basic functionality.

### Tests Requiring Xray

```bash
pytest -m requires_xray
```

Tests that need Xray binary installed.

## Writing Tests

### Basic Test Structure

```python
import pytest

def test_simple_function():
    """Test a simple function."""
    result = my_function(input_data)
    assert result == expected_output
```

### Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    result = await my_async_function()
    assert result is not None
```

### Test with Fixtures

```python
import pytest

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """Test using fixture data."""
    assert sample_data["key"] == "value"
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("example.com", True),
    ("invalid..domain", False),
    ("", False),
])
def test_validation(input, expected):
    """Test with multiple inputs."""
    assert validate(input) == expected
```

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    """Test with mocked dependency."""
    with patch("module.external_call") as mock_call:
        mock_call.return_value = "mocked_value"
        result = function_using_external_call()
        assert result == "processed_mocked_value"
        mock_call.assert_called_once()
```

### Testing Exceptions

```python
import pytest

def test_exception_raised():
    """Test that an exception is raised."""
    with pytest.raises(ValueError, match="Invalid input"):
        risky_function("bad_input")
```

### Network Test Example

```python
import pytest

@pytest.mark.network
@pytest.mark.skipif(
    not has_network(),
    reason="Network not available"
)
def test_api_call():
    """Test that requires network."""
    response = fetch_from_api()
    assert response.status_code == 200
```

## Coverage

### Generate Coverage Report

```bash
pytest --cov=scripts --cov-report=term-missing
```

### HTML Coverage Report

```bash
pytest --cov=scripts --cov-report=html
open htmlcov/index.html
```

### Coverage Thresholds

The project aims for:
- Overall coverage: ≥ 80%
- Critical modules: ≥ 90%
- New code: ≥ 85%

### Exclude from Coverage

Use `# pragma: no cover` for lines that shouldn't be counted:

```python
if __name__ == "__main__":  # pragma: no cover
    main()
```

## Best Practices

### 1. Test Naming

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### 2. Test Organization

- Group related tests in classes
- Use descriptive test names
- One assertion concept per test

### 3. Test Independence

- Tests should not depend on each other
- Use fixtures for setup/teardown
- Clean up resources after tests

### 4. Test Documentation

- Add docstrings to test functions
- Explain complex test logic
- Document test data requirements

### 5. Avoid Common Pitfalls

- Don't test implementation details
- Avoid overly complex tests
- Don't use time.sleep() (use mocks instead)
- Clean up temporary files

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Every push to main
- Every pull request
- Scheduled daily runs

### Local Pre-commit Testing

Create a git hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit

pytest tests/ -x -v
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

## Debugging Tests

### Run with Python Debugger

```bash
pytest --pdb
```

Drops into debugger on failure.

### Run with Increased Verbosity

```bash
pytest -vv --tb=long
```

### Show Print Statements

```bash
pytest -s
```

### Run Last Failed Tests

```bash
pytest --lf
```

### Run Tests That Failed First

```bash
pytest --ff
```

## Performance Testing

### Test Execution Time

```bash
pytest --durations=10
```

Shows 10 slowest tests.

### Profile Tests

```bash
pytest --profile
```

## Continuous Testing

### Watch for Changes

Use `pytest-watch`:

```bash
pip install pytest-watch
ptw
```

### Run Tests on File Change

```bash
pytest-watch --runner "pytest -v"
```

## Troubleshooting

### Tests Fail in CI but Pass Locally

- Check Python version compatibility
- Verify all dependencies are in requirements.txt
- Check for timezone issues
- Review environment variables

### Slow Test Execution

- Use pytest-xdist for parallel execution
- Mock slow external calls
- Use faster test fixtures
- Profile tests to find bottlenecks

### Flaky Tests

- Add retries for network tests
- Increase timeouts
- Fix race conditions with proper synchronization
- Use deterministic test data

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update test documentation
5. Add integration tests for new workflows

## Questions?

For testing-related questions, open an issue on GitHub or contact the maintainers.