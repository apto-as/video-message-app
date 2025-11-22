# D-ID Examples
## Complete Code Examples for Video Generation

This directory contains working code examples for D-ID video generation integration.

---

## Available Examples

### 1. Basic Examples

| File | Description | Difficulty |
|------|-------------|------------|
| `01_simple_video.py` | Generate a single video | ⭐ Beginner |
| `02_upload_files.py` | Upload image and audio | ⭐ Beginner |
| `03_poll_status.py` | Poll video generation status | ⭐⭐ Intermediate |

### 2. Advanced Examples

| File | Description | Difficulty |
|------|-------------|------------|
| `04_batch_generation.py` | Generate multiple videos in parallel | ⭐⭐ Intermediate |
| `05_rate_limiting.py` | Implement rate limiting | ⭐⭐⭐ Advanced |
| `06_error_handling.py` | Comprehensive error handling | ⭐⭐⭐ Advanced |
| `07_caching.py` | Cache generated videos | ⭐⭐⭐ Advanced |

### 3. Integration Examples

| File | Description | Difficulty |
|------|-------------|------------|
| `08_flask_integration.py` | Flask web app integration | ⭐⭐ Intermediate |
| `09_fastapi_integration.py` | FastAPI integration (production-ready) | ⭐⭐⭐ Advanced |
| `10_cli_tool.sh` | Command-line tool | ⭐ Beginner |

### 4. Frontend Examples

| File | Description | Difficulty |
|------|-------------|------------|
| `11_react_component.jsx` | React video generator component | ⭐⭐ Intermediate |
| `12_react_hooks.jsx` | React hooks for D-ID API | ⭐⭐ Intermediate |
| `13_react_typescript.tsx` | TypeScript implementation | ⭐⭐⭐ Advanced |

---

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install httpx asyncio python-dotenv

# Set API key
export D_ID_API_KEY=your-api-key-here
```

### Run Examples

```bash
# Basic example
python 01_simple_video.py

# Advanced example with rate limiting
python 05_rate_limiting.py --batch-size 10

# CLI tool
./10_cli_tool.sh portrait.jpg voice.wav
```

---

## Example Structure

Each example includes:

- ✅ **Complete working code** (copy-paste ready)
- ✅ **Inline comments** explaining each step
- ✅ **Error handling** for common issues
- ✅ **Usage instructions** in docstring
- ✅ **Expected output** examples

---

## Documentation

For detailed API documentation, see:

- [D-ID Integration Spec](../../D_ID_INTEGRATION_SPEC.md)
- [Quick Start Guide](../../D_ID_QUICKSTART.md)
- [Troubleshooting Guide](../../D_ID_TROUBLESHOOTING.md)

---

## License

MIT License - Free to use and modify.

---

**Maintained by**: Muses (Knowledge Architect)
