---
name: cp-goal-loop
description: "Autonomous try-and-correct loop. Runs a process until the success condition is reached. When it hits a blocker, it stops, implements the solution, and restarts. Repeats until success or until attempts run out. Use when the user asks to run a complete process, test something end to end, validate a flow, or any task that may hit blockers along the way."
---

# cp-goal-loop — Autonomous Loop with Self-Correction

Runs a process until the success condition is reached. When it hits a blocker, it STOPS, implements the solution, and RESTARTS the process from the beginning. Repeats until success or until the maximum number of attempts runs out.

## Analogy

Imagine a robot trying to cross a room full of obstacles:

```
ATTEMPT 1: Walks 3 steps -> HITS a chair
  -> STOPS, moves the chair, RESTARTS from the beginning
ATTEMPT 2: Walks 5 steps -> HITS a locked door
  -> STOPS, implements a key, RESTARTS from the beginning
ATTEMPT 3: Walks to the end -> CROSSED THE ROOM -> SUCCESS
```

## Usage

```
/load skill cp-goal-loop
goal: [description of what needs to be achieved]
process: [steps to try to reach the goal]
```

Or more simply:

```
try running the database migration and deploying to staging.
If something fails, fix it and try again until it works.
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_attempts` | 5 | Maximum number of try-correct cycles |
| `max_time` | 30min | Maximum total time |
| `mode` | e2e | e2e (end-to-end) or unit (unit tests) |

## Internal flow

```
1. START ATTEMPT N
2. Run the process step by step
3. If SUCCESS -> END
4. If BLOCKER:
   a. Diagnose the root cause
   b. Implement the fix (code, config, data)
   c. Validate the fix in isolation
   d. N = N + 1
   e. If N <= max_attempts -> BACK TO STEP 1
   f. If N > max_attempts -> RESIDUAL BLOCKERS REPORT
```

## Examples

**Example 1: Deploy with migrations**
```
goal: deploy to staging with all migrations applied and a green health check
process:
  1. Run python manage.py migrate
  2. Run pytest with the staging database
  3. Deploy via CI/CD
  4. Hit the /api/health health check
  5. Confirm the frontend loads
```

**Example 2: User onboarding**
```
goal: create account, verify email, first login, create first project
process:
  1. POST /api/register with valid data
  2. Verify email via confirmation link
  3. POST /api/login and get a token
  4. GET /api/me confirms authentication
  5. POST /api/projects creates the first project
  6. GET /api/projects confirms it appears in the list
```

**Example 3: External API integration**
```
goal: sync CRM contacts with the local database
process:
  1. Authenticate on the CRM API
  2. Pull the contact list (paginated)
  3. For each contact, upsert into the local database
  4. Verify that the total contacts in the database = total in the API
  5. Schedule the next sync for 1 hour from now
```

## E2E CRUD Testing Pattern

For testing CRUD operations across all artifact types (knowledge, pages, presentations, chat) via REST API, see the companion reference:

- `references/e2e-crud-testing.md` — step-by-step API calls for each artifact type, pitfall notes, and LOOP spec template

For testing the same operations through the web browser UI (login, navigate, click, verify), see:

- `references/browser-e2e-crud-testing.md` — browser-based flow for each artifact type, login procedure, Celery worker startup on Windows, and LOOP spec template

### Triple-Channel Execution (API + Browser + Chat)

Run each LOOP spec **three times** — each channel catches a different failure class:

| Channel | Catches | Misses |
|---------|---------|--------|
| API | Serializer errors, status codes, scoping, permissions | UI rendering, button states, navigation flow |
| Browser (UI clicks) | UI rendering, navigation, button states, SSE streaming | Edge-case status codes, raw response validation |
| Chat (Copilot) | NLU intent parsing, MCP tool wiring, chat→backend pipeline | Direct API edge cases, UI polish |

**Chat channel** is the most realistic: the user types "create a folder" and the Copilot executes via MCP. Use this when the test goal is "can the Copilot operate the system" rather than "can the API work."

**Recommended order:** API first (fastest, most precise), then Chat (validates the NLU→MCP→backend pipeline), then Browser (validates the full UI stack).

See the companion references for each channel:

- `references/e2e-crud-testing.md` — step-by-step API calls for each artifact type
- `references/browser-e2e-crud-testing.md` — browser-based flow (login, navigate, click, verify)
- `references/chat-copilot-crud-testing.md` — chat-first flow (type natural language commands, verify Copilot response, validate persistence). **Updated 2026-08-04:** Added MCP tool inventory table, skill registration procedure, bug lifecycle documentation, and confirmation-prompt handling.

### LOOP Spec Lifecycle

1. **Create** `.hermes/docs/loop-tests/LOOP-NNN-<slug>.md` with criteria + results table
2. **Execute API pass** — run each phase via REST calls, document results
3. **Execute browser pass** — run each phase via web UI, document results
4. **Update spec** — mark criteria PASS/FAIL, add execution rows to results table
5. **Fix bugs** — register in `.hermes/inbox/bugs/`, fix code, retry failed phases
6. **Finalize** — when all criteria pass, mark spec as approved

This pattern is useful as a quality gate after implementing new endpoints or modifying existing ones. Run it as a goal-loop:

```text
goal: validate complete CRUD of presentations via API + browser
process: follow the script in references/e2e-crud-testing.md phase 3, then references/browser-e2e-crud-testing.md phase 3
```

## Script

```bash
python .hermes/skills/cp-goal-loop/scripts/run.py \
  --goal "deploy in staging working" \
  --steps "migrate,test,deploy,health-check"
```

## Pitfalls

### Celery Worker on Windows (lxml conflict)
The project venv can pick up Hermes' lxml from `sys.path`, causing `ImportError: cannot import name 'etree' from 'lxml'`. Fix: create a wrapper script that cleans `sys.path` before starting celery (see `references/browser-e2e-crud-testing.md` for the full script).

### Django fails to start on Windows (lxml path pollution)
When running `manage.py` from within `execute_code`, the Hermes agent's own `sys.path` is prepended, causing the project venv's `lxml` to be shadowed by Hermes' lxml (which lacks `etree`). Fix: run Django via `subprocess.Popen` with a **clean environment** — strip `HERMES_*` env vars and ensure the project venv's `Scripts` directory is first in `PATH`:
```python
env = os.environ.copy()
for key in list(env.keys()):
    if 'HERMES' in key.upper():
        del env[key]
env['PATH'] = os.pathsep.join([
    os.path.join(back_dir, ".venv", "Scripts"),
    os.environ.get('PATH', '')
])
```

### Frontend runs on port 8080 (TanStack Start), not 5173 (Vite)
The project uses TanStack Start (not plain Vite), so the dev server runs on port 8080 by default. The vite config is wrapped by `@lovable.dev/vite-tanstack-config`. Check `vite.config.ts` for the actual port and proxy settings. The proxy forwards `/api`, `/media`, `/static` to the Django backend.

### Chat route is /chat, not /copilot
The sidebar label says "Copilot" but the actual TanStack route is `/chat`. Navigating to `/copilot` returns 404. Use `http://localhost:8080/chat` directly or click the "Copilot" sidebar link.

### RAG returns 0 results
Documents start as `PENDING` after upload. Without a running Celery worker, index manually:
```python
from knowledge.tasks import index_document
index_document(str(doc.id))
```
The RAG distance cutoff (0.45) can also discard relevant results for short queries — if the top result has distance > 0.45 but is clearly relevant, loosen the cutoff.

### Chat completions returns SSE, not JSON
The endpoint streams tokens as Server-Sent Events. Parse with:
```python
for line in raw.split("\n"):
    if line.startswith("data: "):
        event = json.loads(line[6:])
```
The request body expects `messages` array (OpenAI format), not a `message` string.

### Knowledge upload requires multipart
`POST /knowledge/docs/` with JSON body (`title` + `content`) returns 400. The serializer requires `file` (multipart) or `url`. Use `Content-Type: multipart/form-data`.

### Regenerate endpoint is slow (~33s)
`POST /presentations/{uuid}/regenerate/` takes ~33s to compile the .pptx. Set HTTP timeout ≥60s.

### Chat testing: Copilot may ask for confirmation before destructive operations
When testing via chat, the Copilot may ask "Would you like to proceed?" before executing delete/unpublish. Send a follow-up confirmation message (e.g. "Yes, go ahead"). This is expected — the Copilot is being cautious. Do NOT treat this as a test failure.

### Chat testing: Copilot may lack MCP tools for some operations
Known gaps: restore from trash, list page templates, create page. When found, register a bug in `.hermes/inbox/bugs/` and document the gap in the LOOP spec. Do NOT block the entire test — skip the broken phase and continue testing remaining phases. Fix pattern: create the missing skill file, register it in `chat/skills/__init__.py`, restart Django.

### Chat testing: snapshot may show stale data
The browser accessibility snapshot can get stuck showing the same content even after the Copilot has responded. Use `browser_console(expression='document.querySelector("main")?.innerText')` to read the actual chat content instead of polling the snapshot repeatedly. If the snapshot hasn't changed after 3+ attempts, switch to this technique.

### Adding new Copilot skills requires Django restart
Skills are registered via `@register_skill` decorators that execute at module import time. When you add a new skill file:
1. Create the `.py` file in `chat/skills/`
2. Add `import chat.skills.<new_skill>` to `chat/skills/__init__.py`
3. **Restart Django** — the runserver with `--noreload` won't pick up new imports
4. Verify the skill loads: `python -c "import chat.skills.<new_skill>; print('OK')"` (run with clean env to avoid lxml conflict)

### Bug lifecycle during LOOP execution
1. **Register** `.hermes/inbox/bugs/BUG-YYYYMMDD-<slug>.md` with status `[Open]`
2. **Document** in the LOOP spec results table
3. **Skip the broken phase** and continue testing remaining phases
4. **Fix** in a separate pass (or inline if using goal-loop auto-correction)
5. **Close** by updating status to `[Fixed]` and re-run the affected phase
