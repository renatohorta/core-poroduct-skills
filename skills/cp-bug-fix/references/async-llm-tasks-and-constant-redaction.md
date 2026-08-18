# Tasks async de LLM e armadilha de redação de constantes

## 1. Toda task async nova que chama LLM DEVE entrar no set `_LONG_TASKS`

Em `config/task_proxy.py`, o `except RuntimeError` do `enqueue_task_sync` tem um
set `_LONG_TASKS` (default: `run_crew`, `on_crew_run_approved_callback`,
`on_crew_run_rejected_callback`). Tasks nesse set rodam numa **daemon thread com
seu próprio event loop** — nunca inline.

**Sintoma de esquecer:** num servidor WSGI (`manage.py runserver`, sem event
loop rodando), a task roda **inline** no request. O `POST` que enfileira a task
bloqueia até o timeout do cliente. Exemplo real (INI-79 Camada 3): o
`POST /api/v1/page-generation/` deveria retornar `201 {"status":"pending"}` em
milissegundos, mas deu `TimeoutError` no `urllib` porque `generate_page` rodou
inline (chamada de modelo LiteLLM).

**Correção:** adicionar o nome da task ao set:
```python
_LONG_TASKS = {
    "run_crew",
    "on_crew_run_approved_callback",
    "on_crew_run_rejected_callback",
    "generate_page",   # ← nova task de LLM
}
```

**Regra de ouro:** task que faz chamada de modelo = `_LONG_TASKS` (thread).
Task rápida de ORM (`index_document`, `generate_title`) = inline (persiste
antes do teste/request retornar; em `TransactionTestCase` o banco é limpo antes
de uma thread terminar).

**Auto-reload:** o `manage.py runserver` recarrega `task_proxy.py` sozinho —
a correção vale sem reiniciar o processo. (Módulos importados no boot do ASGI,
como `callbacks_async.py`/`tasks_async.py`, NÃO têm auto-reload — esses exigem
reiniciar.)

## 2. Armadilha: constantes numéricas aparecem como `***` na saída da ferramenta

Ao ler arquivos via `execute_code`/`read_file`, uma constante numérica pode
aparecer redigida como `TOKENS_MAX_CHARS=***` (ou `=***`). Isso é um artefato
de redação da ferramenta, **NÃO um erro de sintaxe** — o arquivo está válido.

**Como confirmar antes de "corrigir":**
1. `import` do módulo — se compila/importa, não há bug.
2. Ler os bytes crus e decodificar: `open(p,'rb').read().split(b'\n')[N]` e
   imprimir `list(line)` — os ints dos bytes revelam o valor real
   (ex.: `[51,95,53,48,48]` = `3_500`).

**NÃO** reescrever a linha com um valor chutado — você corromperia um arquivo
que estava correto. O `***` é só a ferramenta mascarando o número.

## 3. Padrão de geração assíncrona de página (INI-79 Camada 3)

Quando uma geração via LLM não pode ficar num `POST` bloqueante:
- Model `PageGenerationJob` (status pending/running/done/failed, FK p/ page).
- `tasks_async.py` com `generate_page_task(job_id)` que lê o job, marca
  RUNNING, chama o gerador, grava resultado/erro.
- ViewSet com `create` (enfileira via `enqueue_task_sync`, retorna 201 pending)
  + `retrieve` (status p/ polling) + action de catálogo.
- Front faz polling no `GET /page-generation/<id>/` a cada ~2s até done/failed.
- `task_proxy._LONG_TASKS` precisa incluir o nome da task (ver seção 1).
