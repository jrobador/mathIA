# How to Run the Tests

Here's how to run your tests after organizing them into the new structure:

## Prerequisites

1. Make sure you're in the `backend` directory:

```bash
cd backend
```

2. Ensure you have pytest and all dependencies installed:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run all tests

```bash
python -m pytest
```

### Run tests by category

```bash
# Run unit tests only
python -m pytest tests/unit/

# Run integration tests only
python -m pytest tests/integration/

# Run end-to-end tests only
python -m pytest tests/e2e/
```

### Run specific test files

```bash
# Run a specific test file
python -m pytest tests/unit/test_diagnostic.py

# Run multiple specific files
python -m pytest tests/unit/test_diagnostic.py tests/unit/test_state.py
```

### Run individual tests

```bash
# Run a specific test function
python -m pytest tests/unit/test_state.py::TestStateManagement::test_initialize_state

# Run tests matching a pattern
python -m pytest -k "mastery"  # Runs all tests with "mastery" in their name
```

### Run with detailed output

```bash
# Show more details and output
python -m pytest -v

# Show even more details
python -m pytest -vv
```

### Run with coverage report

```bash
# Install pytest-cov if not already installed
pip install pytest-cov

# Run tests with coverage
python -m pytest --cov=app tests/

# Generate HTML report
python -m pytest --cov=app --cov-report=html tests/
```

## Troubleshooting

### Test discovery issues

If tests aren't being discovered properly, check:
1. That `__init__.py` files exist in all test directories
2. That test files start with `test_`
3. That test functions start with `test_`

### ImportError issues

If you get import errors:
1. Make sure you're running pytest from the `backend` directory
2. Check that the package is properly installed or in PYTHONPATH
3. Verify your imports match the project structure

### Async test issues

If you have problems with async tests:
1. Check that `pytest.ini` has the right asyncio mode: `asyncio_mode = auto`
2. Ensure async test functions are marked with `@pytest.mark.asyncio`
3. Make sure you're using `await` properly inside async tests

## CI/CD Integration

If you're using a CI/CD system, add a command like this to your pipeline:

```yaml
# Example GitHub Actions step
- name: Run tests
  run: |
    cd backend
    python -m pytest
```

This provides a comprehensive guide for running tests at various levels of granularity and with different options for output detail and coverage reporting.