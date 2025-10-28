# LLM Tests

This directory contains test scripts for the LLM service.

## 📁 Tests

### test_msgpack_migration.py
Tests the migration from JSON to MessagePack for caching.

**Purpose:**
- Validates MessagePack serialization/deserialization
- Tests backward compatibility
- Performance benchmarking

**Usage:**
```bash
cd llm
python tests/test_msgpack_migration.py
```

## 🧪 Running Tests

### Run all tests
```bash
cd llm
pytest tests/
```

### Run specific test
```bash
python tests/test_msgpack_migration.py
```

### With coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

## 📝 Adding New Tests

When adding new tests:
1. Name files with `test_*.py` prefix
2. Use pytest conventions
3. Add docstrings explaining test purpose
4. Include both positive and negative test cases
5. Mock external dependencies (Redis, PostgreSQL)

## 🔗 Related Documentation

- [Main LLM README](../README.md)
- [Testing Guidelines](../../docs/guides/TESTING_GUIDE.md) (if exists)

---

**Note**: Tests should be run before deployment and after significant changes.
