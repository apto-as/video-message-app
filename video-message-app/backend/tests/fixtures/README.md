# Test Fixtures

This directory contains test data for E2E testing.

## Structure

```
fixtures/
├── images/          # Sample images for testing
│   ├── person_1.jpg
│   ├── person_2.jpg
│   ├── no_person.jpg
│   └── complex_bg.jpg
├── audio/           # Sample audio files
│   ├── sample_1.wav
│   ├── sample_2.wav
│   └── japanese.wav
└── texts/           # Sample text files
    ├── short.txt
    ├── long.txt
    └── multilang.txt
```

## Usage

```python
import pytest
from pathlib import Path

@pytest.fixture
def test_images():
    fixtures_dir = Path(__file__).parent / "fixtures" / "images"
    return list(fixtures_dir.glob("*.jpg"))
```

## Creating Test Data

### Images

Use `cv2` or `PIL` to create synthetic test images:

```python
import cv2
import numpy as np

# Person-like object
img = np.zeros((640, 480, 3), dtype=np.uint8)
cv2.rectangle(img, (150, 100), (350, 500), (100, 150, 200), -1)
cv2.imwrite("person_1.jpg", img)
```

### Audio

Create minimal WAV files for testing:

```python
with open("sample.wav", "wb") as f:
    f.write(b"RIFF")
    f.write((36).to_bytes(4, "little"))
    f.write(b"WAVE")
    # ... WAV header
```

## Notes

- All test data should be synthetic (no real user data)
- Keep file sizes small (<1MB each)
- Include edge cases (empty, corrupted, oversized)
