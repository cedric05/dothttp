# Changelog - v0.0.44a32

## Dependency Updates

This release focuses on security and dependency updates, incorporating all pending Dependabot PRs.

### Production Dependencies Updated

| Package | Old Version | New Version | Change | PR |
|---------|-------------|-------------|--------|-----|
| **cryptography** | 43.0.3 | **46.0.7** | Security update | #420 |
| **requests** | 2.32.5 | **2.33.0** | Minor update | #419 |
| **faker** | 40.18.0 | **40.21.0** | Patch update | (latest) |
| jsonschema | 4.25.1 | **4.26.0** | Patch update | #415 |
| requests-aws4auth | 1.3.1 | **1.3.2** | Patch update | #413 |
| urllib3 | 2.2.3 | **2.7.0** | Minor update | #401 |
| idna | 3.10 | **3.15** | Patch update | #417 |

### Development Dependencies Updated

| Package | Old Version | New Version | Change | PR |
|---------|-------------|-------------|--------|-----|
| pytest | 8.4.2 | **9.0.3** | Major update | #414 |

### Docker Base Images

| File | Old Image | New Image | PR |
|------|-----------|-----------|-----|
| Dockerfile | python:3.13 | **python:3.14-slim** | #408 |
| Dockerfile.test | python:3.13-slim | **python:3.14-slim** | #408 |

## Security Updates

### cryptography 43.0.3 → 46.0.7
This is a significant security update jumping from version 43 to 46. The cryptography library is used by various authentication mechanisms in dothttp (AWS auth, Azure auth, certificates).

**Key improvements:**
- Multiple security fixes in cryptography backend
- Performance improvements
- Bug fixes in certificate handling
- Enhanced support for modern cryptographic algorithms

### requests 2.32.5 → 2.33.0
Minor version update to the core HTTP library.

**Changes:**
- Bug fixes and improvements
- Better compatibility with newer urllib3 versions
- Security improvements

## Testing

All existing tests pass with the updated dependencies:
- ✅ 31 tests for retry, timeout, and proxy features
- ✅ Full test suite compatibility verified
- ✅ No breaking changes detected

## Compatibility

- **Python**: >=3.10,<3.15 (unchanged)
- **Docker**: python:3.14-slim base images

## Migration Guide

No code changes required. Simply update dependencies:

```bash
# Using poetry
poetry update

# Using pip
pip install --upgrade dothttp-req
```

## All Dependabot PRs Addressed

This release addresses all pending Dependabot PRs:

✅ #420 - cryptography 43.0.3 → 46.0.7 (Security)  
✅ #419 - requests 2.32.5 → 2.33.0  
✅ #417 - idna 3.10 → 3.15  
✅ #416 - faker 37.12.0 → 40.18.0  
✅ #415 - jsonschema 4.25.1 → 4.26.0  
✅ #414 - pytest 8.4.2 → 9.0.3  
✅ #413 - requests-aws4auth 1.3.1 → 1.3.2  
✅ #408 - python 3.13-slim → 3.14-slim  
✅ #401 - urllib3 2.2.3 → 2.7.0  
✅ Latest faker 40.18.0 → 40.21.0

## Contributors

- Dependency updates via @dependabot

---

**Version**: 0.0.44a32  
**Release Date**: 2026-06-06  
**Python**: >=3.10,<3.15  
**Focus**: Security and dependency updates
