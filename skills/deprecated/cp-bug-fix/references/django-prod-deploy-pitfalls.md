# Django in Production (ECS/ALB) — Deploy and Migration Pitfalls

Real pitfalls found while fixing production bugs in Crewbotics (Django 5 + DRF,
Postgres, ECS Fargate + ALB). All caused 500/400 in production and were resolved.

## 1. DisallowedHost from the ALB/ECS health check (private IP)

**Symptom:** in production, ALL endpoints return 400 (including `/api/v1/health/`),
with log:
```
django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: '10.0.10.100:8000'.
You may need to add '10.0.10.100' to ALLOWED_HOSTS.
```
The ALB marks the target as unhealthy and the service goes down.

**Root cause:** the ALB with `target_type = "ip"` hits the container using the **private IP**
of the container as the Host header (e.g. `10.0.x.x`). This IP is not in `DJANGO_ALLOWED_HOSTS`
(which only has the public domain). `ALLOWED_HOSTS` only accepts what comes from the env var.

**Fix (safe, without opening to arbitrary Hosts):** a middleware that adds RFC 1918
private IP Hosts to `ALLOWED_HOSTS` at runtime, BEFORE the `CommonMiddleware` (which
validates the host). `config/middleware.py`:

```python
import ipaddress
from django.conf import settings
from django.http import HttpRequest

def _is_private_ip(host: str) -> bool:
    raw = (host or "").strip()
    if ":" in raw:
        parts = raw.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit() and "." in parts[0]:
            raw = parts[0]
    try:
        return ipaddress.ip_address(raw).is_private
    except ValueError:
        return False

class AllowPrivateIpHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request: HttpRequest):
        allowed = getattr(settings, "ALLOWED_HOSTS", [])
        if "*" not in allowed:
            host = request.META.get("HTTP_HOST") or ""
            if _is_private_ip(host):
                domain = host
                if ":" in host and host.rsplit(":", 1)[1].isdigit():
                    domain = host.rsplit(":", 1)[0]
                if domain not in allowed:
                    allowed.append(domain)  # in-place mutation respected by CommonMiddleware
        return self.get_response(request)
```

Register in `MIDDLEWARE` right after `SecurityMiddleware` (before the `CommonMiddleware`).

**Implementation pitfalls:**
- Do NOT call `request.get_host()` inside the middleware — it already validates against
  `ALLOWED_HOSTS` and raises `DisallowedHost` before your check. Read `request.META["HTTP_HOST"]`.
- Add the **domain without the port** to ALLOWED_HOSTS (`validate_host` uses
  `split_domain_port` and compares only the domain). Adding `10.0.10.100:8000` (with port)
  does not match.
- `ALLOWED_HOSTS` does not accept CIDR (`10.0.0.0/8`) — only `*` and exact names/IPs.
- In DEBUG, `ALLOWED_HOSTS` already has `*`; the middleware only needs to act in production.

**Regression test:** run the real chain `AllowPrivateIpHostMiddleware → CommonMiddleware`
with `RequestFactory` and `HTTP_HOST` of a private IP (must pass), public domain (passes),
and `evil.com` (must raise `DisallowedHost`). Use a real `HttpResponse` as `get_response`
(`CommonMiddleware` expects an HttpResponse; returning a string causes `AttributeError`).

## 2. Migration with `'tabela'::regclass` fails when the table does not exist

**Symptom:** when running `pytest --create-db`, an app's migration fails with:
```
django.db.utils.ProgrammingError: relation "activity_activitylog" does not exist
LINE 2: WHERE conrelid = 'activity_activitylog'::regclass AND cont...
```

**Root cause:** `'tabela'::regclass` throws an error if the table has not been created yet. During
`migrate`/tests, the `accounts` migrations run BEFORE the `activity`/`crews`/etc. ones.
A `accounts` migration that references tables from other apps breaks.

**Fix:** use `to_regclass('tabela')` (returns NULL if it does not exist) and validate before
acting:
```sql
DO $$
DECLARE tbl_oid oid := to_regclass('activity_activitylog');
BEGIN
  IF tbl_oid IS NULL THEN
    RAISE NOTICE 'tabela ainda não existe — pulando';
    RETURN;
  END IF;
  -- ... uses tbl_oid instead of 'tabela'::regclass ...
END $$;
```

## 3. PK retype uuid→bigint: retype ALL the FKs to the PK

**Symptom:** in production, ALL endpoints filtered by `organization` return 500:
```
psycopg.errors.UndefinedFunction: operator does not exist: uuid = integer
HINT: No operator matches the given name and argument types.
```
Affects `/dashboard/kpis/`, `/crews/`, `/crew-runs/`, `/outputs/`, `/knowledge/docs/usage/`.

**Root cause:** the migration that retyped the PKs to bigint (via `RESTART IDENTITY`) only
retyped `organization_id` of SOME tables (e.g. accounts_invite, accounts_user,
pages_page, presentations_presentation). The remaining domain tables (crews_crewrun,
agents_agentoutput, knowledge_productcontext, chat_conversation, billing_invoice,
integrations_*, pages_pagefolder, etc.) kept `organization_id` as **uuid**
while `Organization.id` became **bigint**. The query `WHERE organization_id = 1`
(integer) fails.

**Fix:** create a migration that retypes `organization_id` of ALL the remaining
tables from uuid→bigint, idempotent (only acts if the column is still uuid) and that recreates
the FK. Combine with pitfall #2 (`to_regclass`).

**Rule:** when retyping a PK from uuid→bigint, check ALL the FK columns that point
to it (via `information_schema.columns WHERE column_name='<pk>_id'`) and retype them all.
A partial omission brings down all the endpoints that filter by that FK.

## 4. Deploy workflow references a removed Dockerfile

**Symptom:** the GitHub Action deploy fails with:
```
ERROR: failed to build: failed to solve: failed to read dockerfile: open Dockerfile.celery: no such file or directory
```

**Root cause:** the project migrated from Celery to asyncio/TaskQueue (runs inside the Daphne
ASGI), but the workflow `.github/workflows/deploy.yml` still had a step that built
`Dockerfile.celery` (separate worker) which no longer exists.

**Fix:** remove the Celery worker step from the workflow. The deploy only builds the Django
(Daphne ASGI) image, which already runs the TaskQueue/Scheduler in the background. Validate the YAML with
`python -c "import yaml; yaml.safe_load(open('...deploy.yml'))"`.

**Rule:** when removing an infra component (Celery, worker, beat), scan the deploy
workflow and the `.env.example` for orphan references to the removed component.

## 5. LLM_MODEL points to a nonexistent model → 404 NOT_FOUND, mute Copilot

**Symptom:** in production, Copilot does not respond. Log:
```
litellm.NotFoundError: Vertex_ai_betaException - models/gemini-3-flash is not found
for API version v1alpha ... status: NOT_FOUND
```
The local `.env` uses a valid model (e.g. `gemini-2.5-flash`), but production breaks.

**Root cause:** the production `LLM_MODEL` comes from an **AWS secret** (`valueFrom =
"${local.secret_prefix}:LLM_MODEL::"` in terraform), NOT from code. The secret was
configured with a model that does not exist in the provider (e.g. `gemini-3-flash`). The code
(`chat/llm_client.py` → `get_model()`) only returns `settings.LLM_MODEL` or the default —
**without a model fallback**.

**Fix (defensive, in code):** add a model fallback in `chat/llm_client.py`.
If the configured model returns 404/NotFoundError, try with a known-good model
before giving up:
```python
_FALLBACK_MODEL = "gemini/gemini-2.5-flash"

def _is_not_found_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    if "notfound" in name or "not_found" in name:
        return True
    msg = str(exc).lower()
    return "not found" in msg or "404" in msg or "does not exist" in msg
```
Apply in `astream_with_tools`, `complete` and `complete_json`: in the `except`, if
`_is_not_found_error(exc)` and the current model != `_FALLBACK_MODEL`, re-call with
`model=_FALLBACK_MODEL` (and `force_tool` preserved in astream). Only fall back for
404 errors — rate-limit/key errors must not switch models.

**Regression test:** mock `litellm.completion` with `side_effect=[_NotFound(...), _Ok(...)]`
and verify that the 2nd call used `_FALLBACK_MODEL`; and that a non-404 error does not trigger the fallback
(`call_count == 1`).

**Note:** the fallback resolves the symptom, but the correct thing is to fix the `LLM_MODEL` secret in
AWS to a valid model. The fallback uses an older model as a safety net.
