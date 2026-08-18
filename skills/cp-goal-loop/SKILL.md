---
name: cp-goal-loop
description: "Loop autonomo de tentativa-e-correcao. Executa um processo ate alcancar a condicao de sucesso. Quando encontra um bloqueio, para, implementa a solucao, e recomeca. Repete ate sucesso ou esgotar tentativas. Use quando o usuario pedir para realizar um processo completo, testar algo de ponta a ponta, validar um fluxo, ou qualquer tarefa que possa encontrar bloqueios no caminho."
---

# cp-goal-loop — Loop Autonomo com Auto-Correcao

Executa um processo ate alcancar a condicao de sucesso. Quando encontra um bloqueio, PARA, implementa a solucao, e RECOMECA o processo do inicio. Repete ate sucesso ou esgotar o numero maximo de tentativas.

## Analogia

Imagine um robo tentando atravessar uma sala cheia de obstaculos:

```
TENTATIVA 1: Anda 3 passos -> BATE numa cadeira
  -> PARA, move a cadeira, RECOMECA do inicio
TENTATIVA 2: Anda 5 passos -> BATE numa porta trancada
  -> PARA, implementa uma chave, RECOMECA do inicio
TENTATIVA 3: Anda ate o fim -> ATRAVESSOU A SALA -> SUCESSO
```

## Uso

```
/carregar skill cp-goal-loop
objetivo: [descricao do que precisa ser alcancado]
processo: [passos para tentar alcancar o objetivo]
```

Ou mais simples:

```
tente rodar a migracao do banco e fazer deploy em staging.
Se algo falhar, corrija e tente de novo ate funcionar.
```

## Parametros

| Parametro | Default | Descricao |
|-----------|---------|-----------|
| `max_tentativas` | 5 | Numero maximo de ciclos tentativa-correcao |
| `max_tempo` | 30min | Tempo maximo total |
| `modo` | e2e | e2e (end-to-end) ou unit (testes unitarios) |

## Fluxo interno

```
1. INICIA TENTATIVA N
2. Executa o processo passo a passo
3. Se SUCESSO -> FIM
4. Se BLOQUEIO:
   a. Diagnostica a causa raiz
   b. Implementa a correcao (codigo, config, dados)
   c. Valida a correcao isoladamente
   d. N = N + 1
   e. Se N <= max_tentativas -> VOLTA AO PASSO 1
   f. Se N > max_tentativas -> RELATORIO DE BLOQUEIOS RESIDUAIS
```

## Exemplos

**Exemplo 1: Deploy com migracoes**
```
objetivo: deploy em staging com todas as migracoes aplicadas e health check verde
processo:
  1. Rodar python manage.py migrate
  2. Rodar pytest com o banco de staging
  3. Fazer deploy via CI/CD
  4. Bater no health check /api/health
  5. Confirmar que o frontend carrega
```

**Exemplo 2: Onboarding de usuario**
```
objetivo: criar conta, verificar email, fazer primeiro login, criar primeiro projeto
processo:
  1. POST /api/register com dados validos
  2. Verificar email via link de confirmacao
  3. POST /api/login e obter token
  4. GET /api/me confirma autenticacao
  5. POST /api/projects cria primeiro projeto
  6. GET /api/projects confirma que aparece na lista
```

**Exemplo 3: Integracao com API externa**
```
objetivo: sincronizar contatos do CRM com o banco local
processo:
  1. Autenticar na API do CRM
  2. Puxar lista de contatos (paginado)
  3. Para cada contato, upsert no banco local
  4. Verificar que o total de contatos no banco = total na API
  5. Agendar proxima sincronizacao para daqui 1h
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

**Chat channel** is the most realistic: the user types "crie uma pasta" and the Copilot executes via MCP. Use this when the test goal is "can the Copilot operate the system" rather than "can the API work."

**Recommended order:** API first (fastest, most precise), then Chat (validates the NLU→MCP→backend pipeline), then Browser (validates the full UI stack).

See the companion references for each channel:

- `references/e2e-crud-testing.md` — step-by-step API calls for each artifact type
- `references/browser-e2e-crud-testing.md` — browser-based flow (login, navigate, click, verify)
- `references/chat-copilot-crud-testing.md` — chat-first flow (type natural language commands, verify Copilot response, validate persistence). **Updated 2026-08-04:** Added MCP tool inventory table, skill registration procedure, bug lifecycle documentation, and confirmation-prompt handling.

### LOOP Spec Lifecycle

1. **Create** `.hermes/docs/testes-de-loop/LOOP-NNN-<slug>.md` with criteria + results table
2. **Execute API pass** — run each phase via REST calls, document results
3. **Execute browser pass** — run each phase via web UI, document results
4. **Update spec** — mark criteria PASS/FAIL, add execution rows to results table
5. **Fix bugs** — register in `.hermes/inbox/bugs/`, fix code, retry failed phases
6. **Finalize** — when all criteria pass, mark spec as approved

This pattern is useful as a quality gate after implementing new endpoints or modifying existing ones. Run it as a goal-loop:

```text
objetivo: validar CRUD completo de presentations via API + browser
processo: seguir o roteiro em references/e2e-crud-testing.md fase 3, depois references/browser-e2e-crud-testing.md fase 3
```

## Script

```bash
python .hermes/skills/cp-goal-loop/scripts/run.py \
  --goal "deploy em staging funcionando" \
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
for line in raw.split("\\n"):
    if line.startswith("data: "):
        event = json.loads(line[6:])
```
The request body expects `messages` array (OpenAI format), not a `message` string.

### Knowledge upload requires multipart
`POST /knowledge/docs/` with JSON body (`title` + `content`) returns 400. The serializer requires `file` (multipart) or `url`. Use `Content-Type: multipart/form-data`.

### Regenerate endpoint is slow (~33s)
`POST /presentations/{uuid}/regenerate/` takes ~33s to compile the .pptx. Set HTTP timeout ≥60s.

### Chat testing: Copilot may ask for confirmation before destructive operations
When testing via chat, the Copilot may ask "Você gostaria de prosseguir?" before executing delete/unpublish. Send a follow-up confirmation message (e.g. "Sim, pode prosseguir"). This is expected — the Copilot is being cautious. Do NOT treat this as a test failure.

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
1. **Register** `.hermes/inbox/bugs/BUG-YYYYMMDD-<slug>.md` with status `[Aberto]`
2. **Document** in the LOOP spec results table
3. **Skip the broken phase** and continue testing remaining phases
4. **Fix** in a separate pass (or inline if using goal-loop auto-correction)
5. **Close** by updating status to `[Corrigido]` and re-run the affected phase
