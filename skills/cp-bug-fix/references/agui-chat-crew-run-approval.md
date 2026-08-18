# Aprovar/Rejeitar no card de crew — botão trava "processando"

## Sintoma
Usuário clica em "Aprovar entrega" (ou "Rejeitar") no card de resultado da crew no chat. O botão fica com spinner (`animate-spin`), `disabled=true`, e **nunca** volta ao normal. Nenhuma resposta/ack aparece. A mensagem da crew concluiu (DONE) mas a decisão não é confirmada.

## Causa raiz
O front (em `CrewRunCard.tsx`, função `decide`) faz `POST /api/v1/chat/agui/resume/` e chama `await res.text()`, que espera o **stream SSE fechar**. O backend (`chat/agui/views.py` → `_apply_decision`) chama `enqueue_task_sync("on_crew_run_approved_callback", ...)`.

Se esse callback roda **inline** (via `asyncio.run` no `except RuntimeError` de `config/task_proxy.py`), ele executa operações longas (integrações Composio, criação de página) DENTRO do request. O endpoint nunca retorna headers → `res.text()` fica pendurado → botão "processando" para sempre.

## Diagnóstico
1. Reproduzir no browser: clicar em aprovar, verificar que o botão fica `disabled` + spinner (`document.querySelector(...).disabled`, `innerHTML` com `lucide-loader-circle animate-spin`).
2. Testar o endpoint direto:
```python
import urllib.request, json
# login → access token
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/chat/agui/resume/",
    data=json.dumps({"crewRunId": run_id, "decision": "approve"}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {access}"})
resp = urllib.request.urlopen(req, timeout=15)   # TimeoutError ⇒ inline blocking
```
- `TimeoutError` → callback rodando inline (bug).
- `200` em ~2s com stream `RUN_STARTED → crew.decision → RUN_FINISHED` → correto.

## Correção (2 partes)

### 1. `config/task_proxy.py` — callbacks de aprovação em thread separada
No `except RuntimeError`, o set de tasks longas NÃO pode conter só `run_crew`. Incluir:
```python
_LONG_TASKS = {
    "run_crew",
    "on_crew_run_approved_callback",
    "on_crew_run_rejected_callback",
}
if name in _LONG_TASKS:
    # roda em daemon thread com asyncio.run(); retorna imediatamente
```

### 2. `crews/callbacks_async.py` — isolar ORM síncrono (SynchronousOnlyOperation)
Ao mover o callback para thread, aparecem erros latentes mascarados pelo inline:
- `_create_page_from_run` chamava `_final_task_output(run)`, `run.crew.custom_name`, `run.created_at` (ORM síncrono) em contexto async → `SynchronousOnlyOperation`.
- Fix: helper síncrono `_read_final_meta(run, _final_task_output)` retornando `(final_link, crew_name, created_at, org_id)`, chamado via `sync_to_async`. Usar `organization_id`/`uuid`, nunca `run.organization`/`pk`.
- `PageViewSet.publish(request, pk=...)` → o `PageViewSet` tem `lookup_field="uuid"`. Usar `publish(request, uuid=str(page.uuid))`, senão `publish() got an unexpected keyword argument 'pk'`.

## Verificação
- Teste de regressão `tests/chat/test_resume_nonblocking.py`: chama `enqueue_task_sync("on_crew_run_approved_callback", fake_callback, ...)` num teste síncrono (sem event loop) e asserta que (a) retorna < 3s (não bloqueia) e (b) o callback roda numa thread diferente (`threading.get_ident()`).
- `pytest tests/chat/test_resume_nonblocking.py tests/chat/test_agui_resume_done.py --create-db`.
- Loop E2E no browser: clicar aprovar → botão volta ao normal, ack aparece.

## Reiniciar o Daphne
Módulos editados são importados no boot do ASGI (sem auto-reload). Matar o PID da porta 8000 e relançar. Ao subir via subprocess/execute_code, setar `PYTHONPATH` SÓ para `.venv\Lib\site-packages` (senão conflito cffi/lxml/_overlapped com o venv do Hermes) e usar `python.exe -m daphne` (não `daphne.exe`). Testar `python -c "import asyncio, daphne"` antes.
