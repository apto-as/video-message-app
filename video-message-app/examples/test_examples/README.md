# Test Examples - Video Message App

This directory contains example test files demonstrating best practices for testing in the Video Message App project.

## Directory Structure

```
examples/test_examples/
├── README.md                        # This file
├── example_unit_test.py             # Unit test examples
├── example_integration_test.py      # Integration test examples
├── example_e2e_test.py              # E2E test examples (coming soon)
├── example_mocking.py               # Mocking patterns (coming soon)
└── example_fixtures.py              # Reusable fixtures (coming soon)
```

## Files Overview

### 1. example_unit_test.py

**What it demonstrates:**
- Clear test naming conventions (`test_<function>_<scenario>_<expected>`)
- Arrange-Act-Assert (AAA) pattern
- Parametrized tests with `@pytest.mark.parametrize`
- Edge case coverage
- Test fixtures for setup/teardown
- Helper functions for test data generation

**Key Examples:**
```python
# Parametrized test for multiple inputs
@pytest.mark.parametrize("filename", ["test.jpg", "image.png", "photo.webp"])
def test_accept_valid_image_formats(validator, filename):
    result = validator.validate_filename(filename)
    assert result is True

# Edge case testing
def test_reject_path_traversal_attack(validator):
    with pytest.raises(ValidationError) as exc_info:
        validator.validate_filename("../../../etc/passwd", raise_error=True)
    assert "path traversal" in str(exc_info.value).lower()
```

**Run this example:**
```bash
pytest examples/test_examples/example_unit_test.py -v
```

---

### 2. example_integration_test.py

**What it demonstrates:**
- Integration testing with multiple components
- Async test patterns with `@pytest.mark.asyncio`
- Mocking external dependencies (D-ID API, OpenVoice)
- Resource management (GPU, storage)
- Progress tracking and event streams
- Fixture composition and dependency injection

**Key Examples:**
```python
# Async integration test
@pytest.mark.asyncio
async def test_pipeline_success_happy_path(mock_services, sample_image, sample_audio):
    pipeline = mock_services
    result = await pipeline.execute(image_path=sample_image, audio_path=sample_audio)
    assert result.success is True
    assert result.video_url is not None

# Mocking external services
@pytest.fixture
def mock_services(video_pipeline):
    class MockDIdClient:
        async def create_talk_video(self, audio_url, source_url):
            return {"id": "tlk_test123", "status": "done"}

    video_pipeline._d_id_client = MockDIdClient()
    return video_pipeline
```

**Run this example:**
```bash
pytest examples/test_examples/example_integration_test.py -v
```

---

## Key Testing Concepts

### 1. Test Naming Convention

```python
# Pattern: test_<function>_<scenario>_<expected_result>

# Good examples
def test_image_validator_valid_jpg_returns_true()
def test_pipeline_no_person_detected_raises_error()
def test_concurrent_requests_10_users_completes_under_2min()

# Bad examples (avoid)
def test_1()  # Non-descriptive
def test_image()  # Too vague
```

---

### 2. Arrange-Act-Assert (AAA) Pattern

```python
def test_storage_saves_file():
    # Arrange (Setup)
    storage = StorageManager()
    test_file = Path("test.jpg")

    # Act (Execute)
    result = storage.save_file(test_file)

    # Assert (Verify)
    assert result.success is True
    assert result.path.exists()
```

---

### 3. Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("test.jpg", True),
    ("image.png", True),
    ("file.exe", False),
])
def test_validation(input, expected):
    assert validate(input) == expected
```

---

### 4. Fixtures for Test Data

```python
@pytest.fixture
def sample_image(tmp_path):
    """Create test image file"""
    img_path = tmp_path / "test.jpg"
    # Create minimal valid JPEG
    img_path.write_bytes(b'\xff\xd8\xff\xe0...')
    return img_path

def test_with_fixture(sample_image):
    assert sample_image.exists()
```

---

### 5. Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result == expected
```

---

### 6. Mocking External Dependencies

```python
@pytest.fixture
def mock_api_client(monkeypatch):
    """Mock external API"""
    class MockClient:
        async def call_api(self):
            return {"status": "success"}

    monkeypatch.setattr("module.APIClient", MockClient)
```

---

## Running Examples

### Run all example tests
```bash
pytest examples/test_examples/ -v
```

### Run specific example
```bash
pytest examples/test_examples/example_unit_test.py -v
```

### Run with coverage
```bash
pytest examples/test_examples/ --cov=backend --cov-report=html
```

### Run only unit test examples
```bash
pytest examples/test_examples/example_unit_test.py -v
```

### Run only integration test examples
```bash
pytest examples/test_examples/example_integration_test.py -v
```

---

## Best Practices Demonstrated

### 1. Test Isolation

- Each test is independent
- No shared state between tests
- Use fixtures for setup/teardown

### 2. Clear Intent

- Test names describe what is being tested
- One assertion per test (when possible)
- Arrange-Act-Assert structure

### 3. Edge Cases

- Test boundary conditions
- Test error handling
- Test invalid inputs

### 4. Performance Awareness

- Use mocks for slow operations
- Mark slow tests with `@pytest.mark.slow`
- Run fast tests frequently, slow tests less often

### 5. Documentation

- Docstrings explain what test verifies
- Comments for complex setup
- Clear variable names

---

## Common Patterns

### Pattern 1: Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_pipeline():
    result = await pipeline.execute(image, audio)
    assert result.success is True
```

### Pattern 2: Testing Exceptions

```python
def test_invalid_input_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        validator.validate("invalid")
    assert "error message" in str(exc_info.value)
```

### Pattern 3: Testing With Fixtures

```python
@pytest.fixture
def setup_environment():
    # Setup
    env = Environment()
    yield env
    # Teardown
    env.cleanup()

def test_with_env(setup_environment):
    assert setup_environment.is_ready()
```

### Pattern 4: Parametrized Testing

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert multiply_by_two(input) == expected
```

### Pattern 5: Mocking External Services

```python
@pytest.fixture
def mock_d_id(monkeypatch):
    class MockDId:
        async def create_video(self):
            return {"id": "test123"}

    monkeypatch.setattr("services.d_id.DIdClient", MockDId)
```

---

## Test Markers

```python
# Unit test
@pytest.mark.unit

# Integration test
@pytest.mark.integration

# E2E test
@pytest.mark.e2e

# Slow test (>10 seconds)
@pytest.mark.slow

# Requires GPU
@pytest.mark.gpu

# Security test
@pytest.mark.security

# Performance test
@pytest.mark.performance
```

---

## Tips for Writing Good Tests

### DO:
✅ Write descriptive test names
✅ Keep tests small and focused
✅ Use fixtures for reusable setup
✅ Test edge cases and error conditions
✅ Use parametrized tests for multiple inputs
✅ Mock external dependencies
✅ Clean up resources in fixtures

### DON'T:
❌ Test implementation details
❌ Share state between tests
❌ Use magic numbers (use named constants)
❌ Ignore test failures
❌ Write tests that depend on execution order
❌ Hardcode file paths (use tmp_path)
❌ Skip cleanup in fixtures

---

## Further Reading

- [TEST_STRATEGY.md](../../TEST_STRATEGY.md) - Overall testing strategy
- [TEST_EXECUTION_GUIDE.md](../../TEST_EXECUTION_GUIDE.md) - How to run tests
- [TEST_CASES.md](../../TEST_CASES.md) - Complete test catalog
- [TEST_TROUBLESHOOTING.md](../../TEST_TROUBLESHOOTING.md) - Common issues

---

## Contributing New Examples

When adding new test examples:

1. **Follow naming convention**: `example_<test_type>_test.py`
2. **Add comprehensive comments**: Explain what each test demonstrates
3. **Include docstrings**: Describe the purpose of the test
4. **Demonstrate best practices**: Show the "right way" to test
5. **Update this README**: Add description of new example

---

## Questions?

Refer to the main test documentation:
- [TEST_STRATEGY.md](../../TEST_STRATEGY.md)
- [TEST_TROUBLESHOOTING.md](../../TEST_TROUBLESHOOTING.md)

---

*"Good tests are the foundation of maintainable code. These examples show you how."*

— Muses, Knowledge Architect
