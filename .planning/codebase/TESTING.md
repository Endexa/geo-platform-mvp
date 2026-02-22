# Testing Patterns

This document captures the existing test infrastructure, patterns, and coverage gaps as observed in the GEO Platform MVP codebase. It reflects the actual state of testing, not aspirational goals.

---

## Table of Contents

1. [Test Frameworks](#test-frameworks)
2. [Test File Structure](#test-file-structure)
3. [Existing Test Coverage](#existing-test-coverage)
4. [Pytest Test Patterns (geo_data_points)](#pytest-test-patterns-geo_data_points)
5. [Manual Test Runner Pattern](#manual-test-runner-pattern)
6. [Mocking Patterns](#mocking-patterns)
7. [Fixture Patterns](#fixture-patterns)
8. [How to Run Tests](#how-to-run-tests)
9. [Test Gaps](#test-gaps)

---

## Test Frameworks

### Backend

**pytest** is declared as the backend test framework in `CLAUDE.md` (`cd backend && pytest`). However, no pytest configuration file (`pytest.ini`, `pyproject.toml`, or `conftest.py`) exists in the project root or `backend/app/` directory. No test files exist in the backend application code.

**pytest-asyncio** is used in `geo_data_points/tests/` — all async test methods are decorated with `@pytest.mark.asyncio`.

### Frontend

`CLAUDE.md` declares `cd frontend && npm run test` as the test command, but no test runner configuration (`vitest.config.ts`, `jest.config.js`), test files (`*.spec.ts`, `*.test.ts`), or testing libraries appear in the frontend source tree. No frontend tests currently exist.

### geo_data_points

The measurement subsystem has two test approaches:
- `pytest` for unit tests in `geo_data_points/tests/`
- A standalone Python script (`geo_data_points/test_measurements.py`) used as a manual integration runner

---

## Test File Structure

```
geo-platform-mvp/
├── test_all_measurements.py              # Root-level integration runner (not pytest)
├── geo_data_points/
│   ├── test_measurements.py              # Legacy manual script runner
│   └── tests/
│       ├── __init__.py
│       └── test_cnt_content_depth_score.py   # Only pytest unit test file
└── backend/
    └── app/                              # NO test files exist here
```

There are no backend test files. There are no frontend test files. All existing automated tests are in `geo_data_points/tests/`.

---

## Existing Test Coverage

### What Is Tested

**`geo_data_points/tests/test_cnt_content_depth_score.py`** — the only pytest unit test file. Covers `ContentDepthScoreMeasurement` (CNT-007):

| Test | What it validates |
|------|-------------------|
| `test_minimal_content` | Minimal HTML scores below 30, comment contains 'shallow' |
| `test_comprehensive_content` | Rich multi-section HTML scores ≥ 80 |
| `test_moderate_content` | Mid-depth HTML scores between 40 and 80 |
| `test_no_content` | Nearly empty HTML scores exactly 0 |
| `test_rich_multimedia` | HTML with images and video scores above 40, comment mentions media |
| `test_external_references` | HTML with external links, comment mentions references |

**`geo_data_points/test_measurements.py`** — manual script that tests the 5 original "legacy" measurement scripts (pre-refactor):

- `RobotsTxtGPTBot`
- `RobotsTxtClaudeBot`
- `SchemaOrgOrganization`
- `ResponseTime`
- `TitleTagOptimization`

These tests execute against a live URL (default: `https://anthropic.com`) and print results to stdout. They are not pytest-compatible and produce no structured pass/fail output that CI can consume.

**`test_all_measurements.py`** (root level) — an async integration runner that:
1. Discovers all modules in `geo_data_points/measurements/`
2. Instantiates each measurement class
3. Runs `measure()` against a static sample HTML string and sample URL
4. Validates that the return dict contains `score`, `comment`, `metadata`, and `recommendations` keys
5. Validates that `score` is in range 0–100

This runner is also not pytest-compatible (no `test_` functions, no assertions that pytest can collect).

### What Is Not Tested

- **All FastAPI API endpoints** — zero tests
- **SQLAlchemy models** — zero tests
- **Service classes** (`AnalyzerService`, `BrandVoiceService`, `OptimizerService`) — zero tests
- **Middleware** (`SecurityHeadersMiddleware`, `RateLimiter`, etc.) — zero tests
- **Security layer** (`SecurityManager`, JWT token flow) — zero tests
- **Pydantic validators** (`SecureBaseModel`, `URLValidator`, `StringSanitizer`) — zero tests
- **107 out of 108 measurement scripts** — only `cnt_content_depth_score` has a pytest test
- **Frontend Vue components and pages** — zero tests
- **GeoOrchestrator** — zero tests
- **Database integration** — zero tests

---

## Pytest Test Patterns (geo_data_points)

The single pytest test file establishes the intended pattern for measurement tests.

### Test Class Structure

Tests are grouped in a class named `Test<MeasurementName>`:

```python
# From geo_data_points/tests/test_cnt_content_depth_score.py
class TestContentDepthScore:
    """Test cases for content depth measurement."""

    def setup_method(self):
        """Initialize measurement instance."""
        self.measurement = ContentDepthScoreMeasurement()
```

`setup_method` creates a fresh measurement instance before each test.

### Async Test Methods

All test methods are async and decorated with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_minimal_content(self):
    """Test with minimal content."""
    html = """
    <html><body>
        <h1>Title</h1>
        <p>Very short content.</p>
    </body></html>
    """
    result = await self.measurement.measure("https://example.com", html)

    assert result['score'] < 30, "Minimal content should score low"
    assert 'shallow' in result['comment'].lower()
```

### Assertion Style

Assertions use plain `assert` with a descriptive failure message as the second argument:

```python
assert result['score'] < 30, "Minimal content should score low"
assert result['score'] >= 80, "Comprehensive content should score high"
assert 40 < result['score'] < 80, "Moderate content should score in middle range"
assert result['score'] == 0, "No content should score 0"
assert result['score'] > 40, "Rich multimedia should boost score"
```

Comment content assertions check substring presence with `.lower()` normalization:

```python
assert 'shallow' in result['comment'].lower()
assert 'excellent' in result['comment'].lower() or 'exceptional' in result['comment'].lower()
assert 'media' in result['comment'].lower() or 'images' in result['comment'].lower()
```

### Test HTML Fixtures

HTML fixtures are defined inline as multi-line strings within each test method — there is no shared HTML fixture. Each test embeds its own representative HTML directly.

### Debug Print Statements

Tests include `print()` calls alongside assertions for visibility during manual runs:

```python
print(f"✓ Minimal content test: Score={result['score']}, Comment={result['comment'][:100]}")
```

### Standalone Async Runner

Each test file also defines a standalone `async def run_all_tests()` and an `if __name__ == "__main__"` block, allowing the file to be executed directly with Python in addition to being collected by pytest:

```python
async def run_all_tests():
    """Run all test cases."""
    test_suite = TestContentDepthScore()
    test_suite.setup_method()
    await test_suite.test_minimal_content()
    # ...

if __name__ == "__main__":
    asyncio.run(run_all_tests())
```

---

## Manual Test Runner Pattern

`geo_data_points/test_measurements.py` defines the pattern used for the legacy scripts:

```python
def test_measurement(measurement_class, url: str):
    try:
        measurement = measurement_class(url)
        result = measurement.run()

        print(f"✓ {measurement_class.__name__}")
        print(f"  Score: {result['score']:.2f}/100")
        print(f"  Comment: {result['comment']}")
        print(f"  Execution Time: {result.get('execution_time_ms', 0):.0f}ms")
        return result

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        print(f"✗ {measurement_class.__name__} - FAILED")
        return None
```

This pattern:
- Wraps execution in `try/except`
- Returns the raw result dict on success, `None` on failure
- Prints human-readable output
- Does NOT use `assert` statements — failures are only detected by exception, not by value checking

---

## Mocking Patterns

No mocking infrastructure exists in the codebase. The existing tests avoid the need for mocks by:
- Passing HTML strings directly to `measure()` rather than fetching live URLs
- Testing measurement logic in isolation from the database and external APIs

If backend tests were to be added, the following would need to be mocked:
- `sqlalchemy.orm.Session` — for API and service layer tests
- `openai.embeddings.create` — for `BrandVoiceService._generate_embedding`
- `requests.get` — for `AnalyzerService.fetch_content`
- Redis client — for rate limiter tests

The conventional approach for FastAPI tests uses `TestClient` with an overridden `get_db` dependency:

```python
# Pattern that does not yet exist in this codebase — needed for backend tests
from fastapi.testclient import TestClient
from app.core.database import get_db

def override_get_db():
    # Return a test database session
    ...

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
```

---

## Fixture Patterns

### pytest Fixtures

No `conftest.py` exists anywhere in the project. There are no shared pytest fixtures.

The only fixture-like pattern is `setup_method` in `TestContentDepthScore`, which is a pytest instance method called before each test:

```python
def setup_method(self):
    self.measurement = ContentDepthScoreMeasurement()
```

### Test Data Constants

`test_all_measurements.py` defines module-level constants used as shared test inputs:

```python
# From test_all_measurements.py
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Test Page - Sample Content</title>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Test Org"}
    </script>
</head>
<body>
    <header><h1>Main Title</h1></header>
    <main>
        <article>
            <h2>Section Title</h2>
            <p>This is a test paragraph with content.</p>
            <img src="test.jpg" alt="Test image">
        </article>
    </main>
</body>
</html>
"""

SAMPLE_URL = "https://example.com/test"
SAMPLE_METADATA = {
    'domain_authority': 50,
    'backlinks_count': 1000,
    'organic_traffic': 5000,
}
```

---

## How to Run Tests

### Run the single pytest test file

```bash
# From the project root
cd geo_data_points
pytest tests/test_cnt_content_depth_score.py -v
```

### Run pytest discovery across geo_data_points

```bash
cd geo_data_points
pytest tests/ -v
```

### Run the legacy manual measurement script

```bash
# From the project root
python geo_data_points/test_measurements.py https://example.com
```

### Run the all-measurements integration runner

```bash
# From the project root
python test_all_measurements.py
```

### Backend tests (declared in CLAUDE.md, no tests exist yet)

```bash
cd backend
pytest
```

### Frontend tests (declared in CLAUDE.md, no tests exist yet)

```bash
cd frontend
npm run test
```

---

## Test Gaps

The following are the most significant gaps relative to the application's surface area. Listed in order of risk impact.

### Critical (No Coverage at All)

1. **FastAPI API endpoints** — None of the 6 router files have tests. The analysis flow (POST `/analyze` → poll `/{id}`) is the core user journey and is entirely untested.

2. **Input validation / security validators** — `SecureBaseModel`, `URLValidator`, `StringSanitizer`, `KeywordValidator` are critical security components with zero tests. SQL injection patterns, XSS patterns, and SSRF protection in `URLValidator.BLOCKED_DOMAINS` are untested.

3. **Service layer** — `AnalyzerService.run_analysis`, `AnalyzerService.calculate_visibility_score`, `AnalyzerService.calculate_readability_score`, and `BrandVoiceService.check_voice` contain the core business logic and have no tests.

4. **Rate limiter** — The Redis-backed `RateLimiter` and `EndpointRateLimiter` classes are untested. The behavior on Redis failure (fail-open) is untested.

5. **107 remaining measurement scripts** — Only `cnt_content_depth_score` has a pytest unit test. The other 107 measurement modules have no pytest tests (the `test_all_measurements.py` runner validates structure but not scoring correctness).

### High (Partial or No Coverage)

6. **GeoOrchestrator** — The orchestrator that runs all measurements and writes to the database has no tests.

7. **Database models** — Model column definitions, relationships, and cascade behavior are not verified by tests.

8. **Middleware** — None of the 7 middleware classes have tests. Security header injection, request size limiting, and SQL injection detection in query strings are untested.

9. **Background task behavior** — `BackgroundTasks.add_task` calls are tested neither for being registered correctly nor for their execution behavior.

### Medium (Missing Test Types)

10. **Frontend** — No component tests, no page tests, no API integration tests. The polling mechanism in `analyze.vue` and the data fetching in `dashboard.vue` are not tested.

11. **pgvector similarity queries** — The raw SQL cosine similarity in `BrandVoiceService._calculate_vector_similarity` requires a live PostgreSQL + pgvector instance to test correctly. No integration test exists.

12. **Error state transitions** — The analysis status machine (`pending → processing → completed/failed`) is not tested end-to-end.

### Notes on Next Steps

When adding backend tests, the first priority should be:

1. Create `backend/app/tests/conftest.py` with a test database fixture (using SQLite or a test PostgreSQL instance) and a `TestClient` fixture with `get_db` overridden.
2. Add unit tests for `SecureAnalyzeRequest`, `URLValidator`, and `StringSanitizer` — these are pure Pydantic/Python and require no infrastructure.
3. Add integration tests for the two most critical API paths: `POST /api/v1/analysis/analyze` and `GET /api/v1/analysis/{id}`.

When adding measurement tests, the pattern from `geo_data_points/tests/test_cnt_content_depth_score.py` should be replicated: one test class per measurement, `setup_method` for fresh instantiation, async tests with `@pytest.mark.asyncio`, and inline HTML fixtures covering the boundary conditions described in each measurement's scoring rubric.
