---
name: cp-devops
description: "DevOps and Infrastructure — creates a CrewAI crew with CI/CD, Infrastructure, Monitoring and Infra Security Engineers to configure pipelines, provision infrastructure and deploy. Use when the user says 'deploy', 'configure CI/CD', 'provision infrastructure', 'set up environment', 'configure monitoring'."
---

# cp-devops — DevOps and Infrastructure Crew

Creates a self-contained CrewAI crew with agents specialized in DevOps and Infrastructure to configure CI/CD pipelines, provision infrastructure as code, configure monitoring and perform security review.

## Agents

| Agent | Role |
|--------|--------|
| **CI/CD Engineer** | Configures build/test/deploy pipelines (GitHub Actions, GitLab CI) |
| **Infrastructure Engineer** | Terraform, Docker, Kubernetes, cloud (AWS/GCP/Azure) |
| **Monitoring Engineer** | Configures logging, metrics, alerts (Grafana, Prometheus, Datadog) |
| **Infra Security Engineer** | Reviews infrastructure security, firewalls, IAM, secrets |

## Pipeline (Sequential Tasks)

```
1. Infra Requirements Analysis  →  (Infrastructure Eng.)
2. CI/CD Configuration          →  (CI/CD Eng.)
3. Infrastructure Provisioning  →  (Infrastructure Eng.)
4. Monitoring Configuration    →  (Monitoring Eng.)
5. Security Review             →  (Infra Security Eng.)
6. Quality Gate                →  (All — PASS/FAIL)
```

## Input

- Project description + infrastructure requirements
- Can be direct text or a file via `--input`

## Output

- Configured CI/CD pipeline
- Provisioned infrastructure (IaC)
- Active monitoring (metrics, logs, alerts)
- Security report
- Quality Gate: PASS/FAIL

## Quality Gate

The final Quality Gate verifies:
1. CI/CD pipeline configured and functional
2. Infrastructure health check passing
3. Monitoring collecting metrics
4. No critical security vulnerabilities

Verdict: **PASS** (all green) or **FAIL** (items to fix).

## Modes

| Mode | Scope |
|------|--------|
| `full` (default) | Complete pipeline: analysis → CI/CD → infra → monitoring → security → quality gate |
| `ci-cd` | CI/CD pipeline configuration only |
| `infra` | Infrastructure provisioning only |
| `monitoring` | Monitoring configuration only |
| `security` | Security review only |

## Usage

```bash
# Direct description
python .hermes/skills/cp-devops/scripts/run.py "set up a staging environment with PostgreSQL and Redis"

# Specific mode
python .hermes/skills/cp-devops/scripts/run.py --mode ci-cd "configure GitHub Actions for the repository"

# Input file
python .hermes/skills/cp-devops/scripts/run.py --input infra-requirements.txt

# Save output
python .hermes/skills/cp-devops/scripts/run.py "deploy to production" --output report.md

# Dry run (only builds the crew)
python .hermes/skills/cp-devops/scripts/run.py "test" --dry-run
```

## Examples

```bash
# Example 1: Complete deploy
python .hermes/skills/cp-devops/scripts/run.py \
  "set up a production environment for the scheduling system: \
   AWS EC2 with Docker, PostgreSQL RDS, Redis ElastiCache, \
   GitHub Actions for CI/CD, Grafana + Prometheus for monitoring"

# Example 2: CI/CD only
python .hermes/skills/cp-devops/scripts/run.py --mode ci-cd \
  "configure GitHub Actions with tests, lint, Docker build and automatic deploy"

# Example 3: Security only
python .hermes/skills/cp-devops/scripts/run.py --mode security \
  "review the security of the current infrastructure: AWS with ECS, RDS, S3, Lambda"
```

## Infra Cleanup (removing dependencies)

When a code migration (e.g.: Celery → asyncio) eliminates the need for an infrastructure service (e.g.: Redis/ElastiCache), the Terraform and associated scripts need to be updated. Checklist:

1. **Terraform**: remove the service resource (e.g.: `aws_elasticache_replication_group`)
2. **Security Groups**: remove the SG of the removed service
3. **ECS Task Definitions**: remove containers that are no longer needed (e.g.: `celery-worker`, `celery-beat`)
4. **CloudWatch Log Groups**: remove log groups of the removed containers
5. **Secrets Manager**: remove secrets that are no longer needed (e.g.: `REDIS_URL`)
6. **Outputs**: remove outputs of the removed service
7. **Dockerfile / docker-compose**: remove references to the service
8. **Dev scripts**: remove health checks and dependencies of the service
9. **Code**: remove health checks and connections to the service in the application code
10. **Tests**: update mocks and patches that reference the removed service

**Typical savings:** ElastiCache Redis `cache.t4g.small` = ~$20/month + NAT Gateway = ~$32/month + Fargate containers = ~$30/month.

## Code Migration (worker/broker swap)

When a migration replaces a queue system (e.g.: Celery → native asyncio), besides the infra, the code needs attention on these points:

### 1. Tasks — create async versions

Create `*_async.py` for each app that had Celery tasks. The `run_crew` function (main pipeline) is the most critical — it needs to call `Crew.kickoff_async()` instead of `Crew.kickoff()`.

### 2. Imports — stale import sweep

After deleting the old `tasks.py`, sweep ALL `.py` files for broken imports:

```python
deleted_modules = ["agents.tasks", "chat.tasks", "crews.tasks", "crews.callbacks",
                   "knowledge.tasks", "integrations.tasks", "activity.tasks", "config.celery"]
```

**Common pitfall:** imports inserted inside existing multi-line blocks. Example:
```python
# WRONG — import inside the parentheses of from .models import (...)
from .models import (
from config.task_proxy import enqueue_task_sync  # ← breaks syntax
    CrewInstance,
)
```

### 3. `.delay()` calls → `enqueue_task_sync()`

Every `task.delay(args)` call becomes `enqueue_task_sync("task_name", task_async_fn, args)`. The `config/task_proxy.py` proxy provides `enqueue_task_sync()` for synchronous calls (views/services) and `enqueue_task()` for async.

### 4. Async functions called from synchronous context

Tests and code that called Celery functions directly now call `async def`. They need `asyncio.run()`:

```python
# Before
sweep_stalled_runs()
# After
import asyncio
asyncio.run(sweep_stalled_runs())
```

### 5. Accidentally removed settings

Cleaning up `CELERY_*` settings can remove non-Celery settings that were nearby. Verify:
- `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_TIMEOUT`
- `CREW_RUN_STALE_AFTER`, `CREW_RUN_TIME_LIMIT`, `CREW_LLM_TIMEOUT`
- `CELERY_TASK_ALWAYS_EAGER` (add as compat, always True)

### 6. Tests — `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)`

Remove or comment out decorators that reference deleted settings. Replace with `asyncio.run()` in calls to async functions.

### 7. Django boot — `crewai_tools_adapter` can hang

The `chat/skills/crewai_tools_adapter.py` module runs code at module level (not lazy). Some CrewAI tools call `input()` or do network I/O in `__init__`, hanging the `manage.py` boot forever.

**Solution:** make discovery lazy — replace the code at the end of the file with a `get_discovery_summary()` function that only runs on the first call, not on import.

**Quick solution:** set `CREWAI_TOOLS_DISCOVERY=0` in the environment or in `manage.py` before any Django import.

### 8. `manage.py` — `lxml` conflict between venvs

If the Hermes Agent has a broken `lxml` on the path, the project's `sys.path` can load it before the `.venv`'s `lxml`. Fix in `manage.py`:

```python
_project_site = os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages")
_hermes_site = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "AppData", "Local", "hermes", "hermes-agent", "venv", "Lib", "site-packages",
)
if _project_site in sys.path:
    sys.path.remove(_project_site)
sys.path.insert(0, _project_site)
sys.path = [p for p in sys.path if _hermes_site not in p]
```

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.
