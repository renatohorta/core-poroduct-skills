---
name: cp-testing
description: "Software Testing — creates a CrewAI crew with Unit, Integration, E2E, Performance Test Engineers and a Results Analyst to validate software quality. Use when the user says 'test', 'create tests', 'validate quality', 'do performance tests', 'increase coverage'."
---

# cp-testing — Software Testing

Creates a CrewAI crew with specialized agents to run the complete software testing cycle:

1. **Unit Test Engineer** — Creates unit tests (pytest, Jest). Obsessed with coverage and isolated tests.
2. **Integration Test Engineer** — Tests integration between components/APIs. Specialist in finding bugs that only appear when components talk.
3. **E2E Test Engineer** — Tests complete flows (Playwright, Cypress). Hates sleeps, uses role-based selectors, deterministic tests.
4. **Performance Test Engineer** — Load testing, stress testing (k6, Locust). Finds bottlenecks before the user.
5. **Results Analyst** — Compiles results, calculates coverage, identifies regressions. Turns test data into decisions.

## Agents

| Agent | Role |
|--------|--------|
| Unit Test Engineer | Creates isolated unit tests with high coverage |
| Integration Test Engineer | Tests integration between components/APIs |
| E2E Test Engineer | Tests complete end-to-end flows |
| Performance Test Engineer | Load testing, stress testing, benchmarks |
| Results Analyst | Compiles results, calculates coverage, issues verdict |

## Pipeline

```
1. Code analysis and test planning (Analyst)
2. Unit test creation (Unit Eng.)
3. Integration test creation (Integration Eng.)
4. E2E test creation (E2E Eng.)
5. Performance tests (Performance Eng.)
6. Compilation and final report (Analyst) — issues PASS/FAIL
```

## Quality Gate

- **Minimum coverage:** 80%
- **Critical failures:** 0
- **Performance:** p95 < 500ms for APIs, < 3s for pages
- **Verdict:** PASS (all ok) or FAIL (something below the minimum)

## Input

- Source code (directory path or file)
- Acceptance criteria (optional)
- Test mode: unit, integration, e2e, performance, or full

## Output

Complete test report containing:
- Results of each test category
- Code coverage per module
- Performance metrics (p50, p95, p99)
- Identified regressions
- Final PASS/FAIL verdict with justification

## Usage

```bash
# Complete mode (all test types)
python .hermes/skills/cp-testing/scripts/run.py "appointment scheduling system" --source ./src

# Specific mode
python .hermes/skills/cp-testing/scripts/run.py "scheduling API" --source ./src --mode unit

# With acceptance criteria
python .hermes/skills/cp-testing/scripts/run.py "payments module" --source ./src --acceptance criteria.md

# Save report to file
python .hermes/skills/cp-testing/scripts/run.py "mobile app" --source ./src --output report.md

# Just view the crew structure
python .hermes/skills/cp-testing/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-testing/scripts/run.py \
  "medical appointment scheduling system with authentication, \
   patient CRUD, scheduling with time slots, \
   and email notifications" \
  --source ./src \
  --mode full \
  --output test-report.md
```

## Operation Modes

### 🧪 Simulation (CrewAI — default)

Uses the CrewAI crew with 5 agents to plan, simulate and document the test suite. Ideal for:
- Planning before writing tests
- Estimating coverage and effort
- Generating a quality report

### ⚡ Direct (direct test creation — user's preferred)

Used when the user asks "generate tests" without going through CrewAI. Flow:

1. **Audit existing coverage** — compare endpoints registered in `urls.py` against URLs tested in existing test files
2. **Identify gaps** — endpoints without test coverage
3. **Read views and serializers** — understand each endpoint's contract (HTTP methods, payload, response)
4. **Create test file** — follow the project pattern:
   - `APITestCase` from DRF
   - `_Base` class with `setUp` creating org + user + auth
   - Tests for: success, auth (401), validation (400), org scoping, edge cases
5. **Verify syntax** — `compile(content, path, 'exec')`
6. **Commit + push**

**Test file pattern:**
```python
class _Base(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Alpha")
        self.user = User.objects.create_user(
            email="p@a.com", password="x", name="Prod", organization=self.org
        )
        self.client.credentials(HTTP_AUTHORIZATION=*** {issue_tokens(self.user)['access']}")

class NameTests(_Base):
    def test_success_case(self):
        resp = self.client.post(self.url, {...}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_requires_auth(self):
        self.client.credentials()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_validation_error(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_scoped_by_org(self):
        # Creates data in another org and verifies it doesn't leak
        ...
```

**Pitfalls after the asyncio migration (see `references/testes-async-pos-migracao.md`):**
- `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` no longer exists — remove the decorator
- `async def` functions called in synchronous tests need `asyncio.run()`
- 3-dimensional embeddings in DocumentChunk tests need to be `[0.1] * 768`
- `sync_to_async` doesn't see uncommitted data from `APITestCase` — use `TransactionTestCase`
- `doc.id` vs `doc.pk` in `index_document(str(doc.pk))` calls

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.
