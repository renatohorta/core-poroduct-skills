# Test Fix Patterns Post-Migration

Reproduced in this session (2026-08-04). Checklist when you find `AttributeError` / `django.db.utils.DataError` / `AssertionError` in tests after an infrastructure migration.

## 1. `AttributeError: 'Settings' object has no attribute 'CELERY_TASK_ALWAYS_EAGER'`

**Cause:** The `CELERY_TASK_ALWAYS_EAGER` setting was removed along with Celery. Tests that used `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` to force inline execution now break.

**Fix:** Remove the `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` decorator — with asyncio, tasks run inline by default (no broker needed).

**Occurred in:** `tests/chat/test_core.py`, `tests/chat/test_agui.py`

## 2. Calling an `async def` in a synchronous test without `asyncio.run()`

**Symptom:** `AssertionError` — the async function was called but never executed (returned a coroutine, not the result).

**Cause:** Functions that were `@shared_task` (synchronous) became `async def`. Tests that called them directly now need `asyncio.run()`.

**Fix:**
```python
# Before:
on_crew_run_approved_callback(crew_run_id=..., user_id=...)

# After:
import asyncio
asyncio.run(on_crew_run_approved_callback(crew_run_id=..., user_id=...))
```

**Occurred in:** `tests/chat/test_agui_resume_done.py`

## 3. `django.db.utils.DataError: expected 768 dimensions, not 3`

**Symptom:** Embedding dimension error when creating a DocumentChunk in a test.

**Cause:** pgvector expects 768-dimension vectors (configured in the schema), but the test mocked embeddings with `[0.1, 0.2, 0.3]` (3 dimensions).

**Fix:** Use `[0.1] * 768` instead of small vectors in tests that create DocumentChunk directly.

**Occurred in:** `tests/chat/test_knowledge_search.py`

## 4. LLM settings accidentally deleted

**Symptom:** `AttributeError: 'Settings' object has no attribute 'LLM_MODEL'`

**Cause:** During the cleanup of Celery settings, the LLM settings (`LLM_MODEL`, `LLM_API_KEY`, etc.) were removed along with them.

**Fix:** Restore the complete LLM settings block. Check the git diff for what was removed.

## 5. Test assumes seeded catalog data that does NOT exist in the test database

**Symptom:** `django.db.utils.IntegrityError: null value in column "<col>" violates not-null constraint` when creating a record with an FK.

**Cause:** The test looks up a global catalog record that only exists via seed in dev (`Model.objects.filter(slug=...).first()` returns `None`), then creates a record referencing that `None` by FK. The test database **does not run the seed of large catalogs** (e.g. 1000+ integration providers, bots, etc.).

**Real example (2026-08-10):** `tests/accounts/test_contract.py::test_integration_contract_hides_credentials` did:
```python
prov = IntegrationProvider.objects.filter(slug=Provider.META_ADS).first()  # → None
UserIntegration.objects.create(organization=self.org, provider=prov)  # provider_id null → IntegrityError
```
The `meta-ads` provider exists in dev (1010 seeded providers), but not in the test database.

**Fix:** the test must **create** the catalog record with `get_or_create` (not depend on the seed), with the model's required fields:
```python
from integrations.enums import AuthType, ProviderStatus
prov, _ = IntegrationProvider.objects.get_or_create(
    slug=Provider.META_ADS,
    defaults={
        "name": "Meta Ads",
        "auth_type": AuthType.OAUTH2,
        "provider_status": ProviderStatus.ACTIVE,
    },
)
UserIntegration.objects.create(organization=self.org, provider=prov)
```

**Rule:** in contract/CRUD tests that reference global catalogs, ALWAYS create the catalog entity with `get_or_create` (fill the required fields) instead of `filter(...).first()`. Do not assume the dev seed exists in the test database.

**Occurred in:** `tests/accounts/test_contract.py` (after adding the NOT NULL `provider_id` field).

## Complete Scan (mandatory after a settings migration)

```python
# Check essential settings that may have been accidentally removed
essential_settings = ["LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_TEMPERATURE", "LLM_TIMEOUT"]
with open("config/settings.py") as f:
    content = f.read()
for s in essential_settings:
    if s not in content:
        print(f"MISSING: {s}")
```
