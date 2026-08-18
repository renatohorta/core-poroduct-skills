# Padrões de Bugs Pós-Migração (Celery → Asyncio)

Reproduzidos nesta sessão (2026-08-04). Use como checklist ao encontrar `ModuleNotFoundError`, `ImportError` ou `SyntaxError` após uma migração que deletou/renomeou módulos.

## 1. Import de módulo deletado

**Sintoma:** `ModuleNotFoundError: No module named 'agents.tasks'`

**Causa:** O módulo `agents/tasks.py` foi deletado (substituído por `agents/tasks_async.py`), mas `agents/views.py` ainda tinha `from .tasks import run_agent`.

**Correção:** Remover a linha obsoleta. O import correto (`from agents.tasks_async import run_agent`) já existia logo abaixo.

**Padrão:** Ocorreu em 4 arquivos:
- `agents/views.py`: `from .tasks import run_agent`
- `knowledge/views.py`: `from .tasks import index_document`
- `integrations/views.py`: `from .tasks import process_webhook_event`
- `crews/services.py`: `from .tasks import run_crew` (2x)

## 2. Import inserido dentro de multi-line import

**Sintoma:** `SyntaxError: invalid syntax` apontando para a linha do import.

**Causa:** Ao inserir `from config.task_proxy import enqueue_task_sync` programaticamente, ele caiu DENTRO dos parênteses de:
```python
from .models import (
    CrewInstance,
```
Resultando em:
```python
from .models import (
from config.task_proxy import enqueue_task_sync  # ← SyntaxError
    CrewInstance,
```

**Correção:** Mover os imports para antes do bloco `from .models import (`.

**Ocorreu em:** `crews/services.py`, `integrations/views.py`

## 3. Indentação quebrada em try/except

**Sintoma:** `IndentationError: unindent does not match any outer indentation level`

**Causa:** O replace de `index_document.delay(str(doc.id))` por `enqueue_task_sync(...)` quebrou a indentação do bloco `try` circundante. O `try:` ficou num nível e o `enqueue_task_sync` em outro.

**Ocorreu em:** `knowledge/archiving.py` e `crews/services.py`

## 4. Função async faltando no módulo de destino

**Sintoma:** `ImportError: cannot import name 'run_crew' from 'crews.tasks_async'`

**Causa:** A função `run_crew` (pipeline completo) existia no `crews/tasks.py` antigo mas NUNCA foi portada para `crews/tasks_async.py`. O `crew_runner_async.py` tinha o motor baixo-nível (`run_pipeline_async`), mas a função de alto-nível que `services.py` importava não existia.

**Correção:** Adicionar `async def run_crew(crew_run_id)` completa em `crews/tasks_async.py` (141 linhas).

## 5. Import duplicado lado a lado

**Sintoma:** O import antigo e o novo foram inseridos lado a lado:
```python
from .tasks import run_agent       # ← quebra (módulo deletado)
from agents.tasks_async import run_agent  # ← funcionaria se chegasse aqui
```

**Causa:** O Python executa o primeiro import — se o módulo foi deletado, nunca chega no segundo.

## 6. `manage.py` travando por conflito de `lxml` do Hermes

**Sintoma:** `ImportError: cannot import name 'etree' from 'lxml'` apontando para o site-packages do Hermes, não do projeto.

**Causa:** O `sys.path` carrega o site-packages do Hermes antes do do projeto. O Hermes tem um `lxml` incompatível.

**Correção definitiva no manage.py:**
```python
import sys
project_site = os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages')
hermes_site = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'AppData', 'Local', 'hermes', 'hermes-agent', 'venv', 'Lib', 'site-packages',
)
if project_site in sys.path:
    sys.path.remove(project_site)
sys.path.insert(0, project_site)
sys.path = [p for p in sys.path if hermes_site not in p]
```

## 7. `crewai_tools_adapter.py` travando o boot para sempre

**Sintoma:** `manage.py check` / `migrate` / `runserver` trava por horas (não segundos). O processo fica pendurado sem dar erro.

**Causa:** O módulo `chat/skills/crewai_tools_adapter.py` tenta descobrir 63 tools do CrewAI no momento do `import`. Várias chamam `input()` no `__init__` perguntando "Quer instalar a dependência? [y/N]" — mesmo com o `lambda: "N"` que neutraliza `input()`, algumas ferramentas fazem I/O de rede e penduram o processo **para sempre**.

**Solução definitiva (não apenas env var):**
1. Deletar `chat/skills/crewai_tools_adapter.py`
2. Deletar `chat/skills/crewai_custom/` (diretório inteiro)
3. Remover o import de `chat/skills/__init__.py`
4. Remover a classe de teste `CrewAIToolsAdapterTests` de `tests/chat/test_core.py`

**O Copilot não usa essas tools.** Ele usa as skills nativas registradas manualmente em `chat/skills/`.

## 8. Chamada de `async def` em código síncrono sem `asyncio.run()`

**Sintoma:** `RuntimeWarning: coroutine 'X' was never awaited` + teste falha porque a função retornou uma corrotina em vez do resultado.

**Correção:** Envolver em `asyncio.run()`:
```python
import asyncio
asyncio.run(process_webhook_event(str(evt.id)))
```

## 9. `doc.id` vs `doc.pk` em testes de knowledge

**Sintoma:** `ProductContext.DoesNotExist` ao chamar `index_document(str(doc.id))`.

**Causa:** `doc.id` retorna o UUID público (campo `uuid` do CoreModel), mas `index_document` espera o PK interno.

**Correção:** Usar `doc.pk` em vez de `doc.id`.

## 10. `run_pipeline` está em `crew_runner_async`, não em `tasks_async`

**Sintoma:** `AttributeError: module 'crews.tasks_async' has no attribute 'run_pipeline'`

**Correção:** Trocar o path do patch:
```python
# Antes:
@patch("crews.tasks_async.run_pipeline")
# Depois:
@patch("crews.crew_runner_async.run_pipeline_async")
```

## 11. `asyncio.run(asyncio.run(...))` duplicado

**Sintoma:** `ValueError: a coroutine was expected, got 0`

**Correção:** Usar apenas um `asyncio.run()`.

## 12. Settings de LLM deletadas acidentalmente

**Sintoma:** `AttributeError: 'Settings' object has no attribute 'LLM_MODEL'`

**Correção:** Restaurar o bloco completo de settings LLM. Verificar no git diff o que foi removido.

## 13. Settings de compatibilidade faltando

**Sintoma:** `AttributeError: 'Settings' object has no attribute 'CELERY_TASK_ALWAYS_EAGER'`

**Correção:** Adicionar como compatibilidade:
```python
CELERY_TASK_ALWAYS_EAGER = True
CREW_RUN_STALE_AFTER = env_int("CREW_RUN_STALE_AFTER", 300)
```

## 14. `database_sync_to_async` não existe no asgiref instalado

**Sintoma:** `ImportError: cannot import name 'database_sync_to_async'`

**Correção:** Usar `sync_to_async` (existe em todas as versões) combinado com `TransactionTestCase`.

## 15. Testes somem silenciosamente por erro de sintaxe

**Sintoma:** A contagem de testes cai (ex: 429 → 369) sem aviso claro.

**Correção:** Verificar a contagem de testes ANTES e DEPOIS de cada alteração. Se caiu, algum arquivo não carregou.

## 16. `@mock.patch` vs `@patch` — import correto

**Sintoma:** `NameError: name 'mock' is not defined`

**Correto:**
```python
from unittest.mock import patch
@patch("path.to.module")
```

## 17. Parêntese extra de substituição regex

**Sintoma:** `SyntaxError: unmatched ')'` apontando para `asyncio.run(...))`.

**Correção:** Sempre verificar o resultado de substituições em bloco. Usar `compile()` para validar sintaxe.

## 18. Import no meio do arquivo (depois de decorator)

**Sintoma:** `SyntaxError: invalid syntax` em linha de import depois de um decorator.

**Correção:** Imports SEMPRE no topo do arquivo, antes de qualquer código.

## 21. Rota dupla ao incluir urls com path parameter

**Sintoma:** 404 ao acessar `/serve/<slug>/` mesmo com a rota configurada.

**Causa:** `path("serve/<slug:slug>/", include("pages.urls"))` captura o slug no prefixo, e `pages/urls.py` também tem `<slug:slug>/`. Resultado: `/serve/<slug>/<slug>/` — slug capturado duas vezes.

**Correção:** O prefixo não deve ter o path parameter:
```python
# ERRADO:
path("serve/<slug:slug>/", include("pages.urls"))

# CERTO:
path("serve/", include("pages.urls"))
```

## 22. Vite proxy faltando para nova rota pública

**Sintoma:** 404 ao acessar `/serve/<slug>/` pelo frontend (:8080), mas funciona no backend (:8000).

**Causa:** O Vite dev server só redireciona ao backend as rotas listadas em `server.proxy` no `vite.config.ts`. Rotas novas precisam ser adicionadas.

**Correção:**
```typescript
server: {
  proxy: {
    "/serve": {
      target: process.env.VITE_BACKEND_URL || "http://localhost:8000",
      changeOrigin: true,
    },
  },
}
```

## 23. `enqueue_task_sync` sem event loop — task nunca executa

**Sintoma:** Tasks de background (gerar título da conversa, indexar documento) nunca completam. O servidor roda com `manage.py runserver` (WSGI), não Daphne (ASGI).

**Causa:** `manage.py runserver` (WSGI) não tem event loop rodando. A `TaskQueue` e o `Scheduler` só sobem no `LifespanASGI.startup()` do Daphne. Sem event loop, `enqueue_task_sync()` caía no `except RuntimeError` e chamava `asyncio.run(enqueue_task(...))`, que criava um loop temporário, enfileirava a task na `TaskQueue`... mas a `TaskQueue` **não tem workers rodando** porque eles só sobem no ASGI lifespan.

**Correção:** Em `config/task_proxy.py`, quando não há event loop rodando, executar a task **inline** em vez de enfileirar:
```python
except RuntimeError:
    # Sem loop rodando (WSGI) — executa inline
    try:
        result = coro_factory(*args, **kwargs)
        if hasattr(result, '__await__'):
            return asyncio.run(result)
        return result
    except Exception as exc:
        logger.error("Task '%s' falhou inline: %s", name, exc)
        return str(uuid.uuid4())
```

**Como detectar:** Verificar o header `Server:` na resposta HTTP. Se for `WSGIServer` (Django runserver) ou `Cheroot` (waitress), é WSGI. Se for `daphne` ou `uvicorn`, é ASGI.

## 25. Paginação DRF quebra frontend que esperava array plano

**Sintoma:** Dashboard de atividades mostrava "Nenhuma atividade no período" mesmo com dados no banco. O `useQuery` recebia `{ count, results }` mas o componente esperava um array.

**Causa:** Adicionar `pagination_class` a um ViewSet do DRF que antes retornava `T[]` muda a resposta para `{ count, next, previous, results: T[] }`. O frontend que consumia `data` como array agora recebe um objeto.

**Correção em 3 camadas:**

1. **Backend:** Adicionar `pagination_class` ao ViewSet:
```python
from rest_framework.pagination import PageNumberPagination

class MyPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100

class MyViewSet(...):
    pagination_class = MyPagination
```

2. **API endpoint type:** Atualizar o tipo de retorno no `endpoints.ts`:
```typescript
// Antes:
api.get<T[]>("/path/")
// Depois:
api.get<PaginatedResponse<T>>("/path/")
```

3. **Hook de query:** Adicionar `page` e `page_size` aos params, e extrair `results`:
```typescript
// No hook:
useAuthedQuery({
  queryKey: ["key", params],
  queryFn: () => api.list(params),  // retorna PaginatedResponse
  select: (data) => data.results,   // extrai o array
})
```

4. **Componente:** Adicionar state de página + botões Anterior/Próxima:
```typescript
const [page, setPage] = useState(1);
const { data: pageData } = useQuery(params);
const logs = pageData?.results ?? [];
const totalPages = Math.ceil((pageData?.count ?? 0) / pageSize);
// Render: "{page} de {totalPages}" + Anterior/Próxima
```

**Ocorreu em:** `dashboard.tsx` (ActivityFeed) + `activity/views.py` (ActivityLogViewSet)

## 26. Frontend/Backend page_size fora de sincronia

**Sintoma:** O backend retorna 10 itens por página mas o frontend mostra "1 de 2" calculado com base em 30 itens por página. A paginação mostra números errados.

**Causa:** `page_size` foi alterado no backend (`ActivityLogPagination.page_size = 10`) mas o frontend ainda tinha `page_size: 30` hardcoded em 3 lugares:
1. Parâmetro da chamada API: `page_size: 30`
2. Cálculo de totalPages: `Math.ceil(totalCount / 30)`
3. Slice redundante: `logs?.slice(0, 30)` (desnecessário com paginação)

**Correção:** Sempre que alterar `page_size` no backend, buscar no frontend por TODAS as ocorrências do valor antigo:
```bash
grep -rn "page_size: 30\|/ 30\|slice(0, 30)" src/
```

**Padrão:** O frontend hardcoda o page_size em vez de derivar do backend. Considere extrair para uma constante compartilhada ou usar o valor do backend via API.

## 27. Layout de paginação sobrepondo conteúdo abaixo

**Sintoma:** Os botões "Anterior 1 de 2 Próxima" aparecem sobrepostos ao conteúdo abaixo do card de atividades.

**Causa:** O container da paginação não tem `clear: both` nem `position: relative`, permitindo que elementos flutuantes ou com posicionamento absoluto do conteúdo acima interfiram.

**Correção:**
```tsx
<div style={{
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 12,
  padding: "16px 0 8px",
  marginTop: 8,
  borderTop: "1px solid var(--rn-gray-800)",
  position: "relative",
  clear: "both",
}}>
  <button disabled={page <= 1} style={{ opacity: page <= 1 ? 0.4 : 1, cursor: page <= 1 ? "default" : "pointer" }}>
    Anterior
  </button>
  <span style={{ whiteSpace: "nowrap" }}>
    {page} de {totalPages}
  </span>
  <button disabled={page >= totalPages} style={{ opacity: page >= totalPages ? 0.4 : 1, cursor: page >= totalPages ? "default" : "pointer" }}>
    Próxima
  </button>
</div>
```

**Propriedades críticas:** `clear: both` (evita overlap com floats), `whiteSpace: nowrap` (evita quebra do "X de Y"), `position: relative` (cria stacking context), `marginTop` (espaçamento do conteúdo acima).

**Sintoma:** Dashboard de atividades mostrava "Nenhuma atividade no período" mesmo com dados no banco. O `useQuery` recebia `{ count, results }` mas o componente esperava um array.

**Causa:** Adicionar `pagination_class` a um ViewSet do DRF que antes retornava `T[]` muda a resposta para `{ count, next, previous, results: T[] }`. O frontend que consumia `data` como array agora recebe um objeto.

**Correção em 3 camadas:**

1. **Backend:** Adicionar `pagination_class` ao ViewSet:
```python
from rest_framework.pagination import PageNumberPagination

class MyPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100

class MyViewSet(...):
    pagination_class = MyPagination
```

2. **API endpoint type:** Atualizar o tipo de retorno no `endpoints.ts`:
```typescript
// Antes:
api.get<T[]>("/path/")
// Depois:
api.get<PaginatedResponse<T>>("/path/")
```

3. **Hook de query:** Adicionar `page` e `page_size` aos params, e extrair `results`:
```typescript
// No hook:
useAuthedQuery({
  queryKey: ["key", params],
  queryFn: () => api.list(params),  // retorna PaginatedResponse
  select: (data) => data.results,   // extrai o array
})
```

4. **Componente:** Adicionar state de página + botões Anterior/Próxima:
```typescript
const [page, setPage] = useState(1);
const { data: pageData } = useQuery(params);
const logs = pageData?.results ?? [];
const totalPages = Math.ceil((pageData?.count ?? 0) / pageSize);
// Render: "{page} de {totalPages}" + Anterior/Próxima
```

**Ocorreu em:** `dashboard.tsx` (ActivityFeed) + `activity/views.py` (ActivityLogViewSet)

**Sintoma:** O remote `main` tem commits que o `main` local não tem. Commits futuros partem da feature branch e o `main` local fica para trás.

**Causa:** `git push origin HEAD:main` atualiza o remote mas não o branch local `main`.

**Correção:**
```bash
git checkout main
git merge feature-branch    # fast-forward (já está no remote)
git push origin main         # confirma (já sincronizado)
git checkout feature-branch  # volta a trabalhar
```

**Como detectar:** `git log --oneline main..origin/main` mostra commits que estão no remote mas não no local. `git log --oneline origin/main..main` mostra o inverso.

## Varredura Completa (obrigatória após migração)

```python
# 1. Imports stale
deleted_modules = [
    "agents.tasks", "chat.tasks", "crews.tasks", "crews.callbacks",
    "knowledge.tasks", "integrations.tasks", "activity.tasks", "config.celery",
]
for root, dirs, files in os.walk(project_dir):
    for f in files:
        if f.endswith('.py'):
            with open(os.path.join(root, f)) as fh:
                content = fh.read()
            for mod in deleted_modules:
                for line in content.split('\n'):
                    s = line.strip()
                    if s.startswith(f'from {mod} import') or s.startswith(f'import {mod}'):
                        print(f"STALE: {rel}: {s}")

# 2. Settings essenciais
essential_settings = ["LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_TEMPERATURE", "LLM_TIMEOUT"]
with open("config/settings.py") as f:
    content = f.read()
for s in essential_settings:
    if s not in content:
        print(f"MISSING: {s}")

# 3. Chamadas async sem await
# Procurar por padrões como: `process_webhook_event(str(...))` sem `asyncio.run()`
```
