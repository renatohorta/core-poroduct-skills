---
name: cp-bug-fix
description: Corrige bugs usando o fluxo NEXUS-Micro com agents do The Agency. Cria uma crew CrewAI com Developer → QA (com criação de testes automatizados) → Evidence Collector, máximo 3 retries. Use quando o usuário pedir para corrigir um bug, consertar um erro, ou quando mencionar "corrigir", "bug", "erro", "fix", "consertar" em qualquer contexto de código.
---

# cp-bug-fix — Correção de Bug com NEXUS-Micro

Corrige bugs usando o fluxo NEXUS-Micro com agents do The Agency. Cria uma crew CrewAI com:

1. **Developer** (Backend Architect ou Frontend Developer) — investiga e implementa o fix
2. **QA** (API Tester + Test Automation Engineer) — valida o fix E cria testes automatizados
3. **Evidence Collector** — verificação final com screenshots/evidências

Máximo 3 tentativas no loop Dev→QA. Se falhar 3x, escala com relatório de escalation.

## Uso

```
/carregar skill cp-bug-fix
corrigir: [descrição do bug]
```

Ou diretamente:

```
corrige o bug onde o endpoint de login retorna 500 quando o email tem acento
```

## Modos de Operação

### 🧪 Simulação (CrewAI — default)

Usa o fluxo NEXUS-Micro com agentes CrewAI: Developer → QA → Evidence Collector.
Máximo 3 tentativas no loop Dev→QA. Se falhar 3x, escala com relatório de escalation.

```
[Developer] ──► [QA: API Tester + Test Automation Engineer] ──► [Evidence Collector]
     │                              │                                    │
     │  implementa fix              │  valida + cria testes              │  verificação final
     │                              │  automatizados                    │
     │                              │                                    │
     └──────────────────────────────┼────────────────────────────────────┘
                                    │
                              PASS / FAIL
                                    │
                          FAIL (max 3) → ESCALATION
```

### ⚡ Direto (traceback-driven — preferido do usuário)

Usado quando o usuário cola um traceback. Fluxo:

1. **Ler o traceback** — identificar o `ModuleNotFoundError` / `SyntaxError` / `ImportError` e a linha exata
2. **Diagnosticar causa raiz** — import de módulo deletado, import dentro de bloco errado, função faltando na migração
3. **Corrigir o arquivo** — remover linha obsoleta, reposicionar import, adicionar função faltante
4. **Verificar sintaxe** — `compile(content, path, 'exec')` — SEMPRE compile após editar. Sem isso, o erro só aparece no runtime (Django carregando URLs), não no teste.
5. **Testar** — o usuário testa via sistema real (password-reset, login) e cola o próximo erro se houver
6. **Iterar** — repetir até o erro sumir
7. **Commit + push** — após cada correção, commitar e pushar na main

**SEMPRE verificar sintaxe com `compile()` após editar** — o erro de sintaxe só aparece no runtime (Django carregando URLs), não no pytest collection. Sem essa verificação, você descobre o erro só quando o usuário testa.

**SEMPRE verificar se o `sys.path` está correto** — em ambientes com múltiplos venvs (ex: Hermes + projeto), o `lxml` do Hermes pode ser carregado antes do do projeto, causando `ImportError: cannot import name 'etree'`. Sintoma: `manage.py` trava ou dá erro de lxml. Correção: adicionar no topo do `manage.py` a remoção do site-packages do Hermes do `sys.path` e inserção do do projeto no topo.

**SEMPRE remover o `crewai_tools_adapter` se o `manage.py` travar** — o módulo `chat/skills/crewai_tools_adapter.py` tenta descobrir 63 tools do CrewAI no momento do import. Várias chamam `input()` no `__init__` ou fazem I/O de rede, travando o processo **para sempre** (horas, não segundos). O `lambda: "N"` que neutraliza `input()` não é suficiente. Solução definitiva: deletar o módulo, deletar `chat/skills/crewai_custom/`, e remover o import de `chat/skills/__init__.py`. O Copilot não usa essas tools — ele usa as skills nativas registradas manualmente.

**SEMPRE varrer imports stale após remover módulos** — não pare no primeiro erro. (Doc-editing secret-masking pitfall: `references/editing-docs-secret-masking.md`) Quando um `ModuleNotFoundError` aparece, o módulo deletado pode ter sido importado em MÚLTIPLOS arquivos. Use uma varredura abrangente:

```python
# Varredura completa de imports stale
deleted = ["agents.tasks", "chat.tasks", "crews.tasks", "config.celery", ...]
for root, dirs, files in os.walk(back_dir):
    for f in files:
        if f.endswith('.py'):
            with open(fpath) as fh:
                content = fh.read()
            for mod in deleted:
                for line in content.split('\n'):
                    if line.strip().startswith(f'from {mod} import'):
                        print(f"STALE: {rel}: {line}")
```

**SEMPRE verificar imports inseridos dentro de blocos errados** — quando você adiciona imports via find-and-replace, eles podem cair dentro de um multi-line import (dentro dos parênteses de `from .models import (`). Isso quebra a sintaxe silenciosamente. Verifique sempre o contexto de 3 linhas acima e abaixo do local da inserção.

**SEMPRE verificar indentação após substituições** — find-and-replace pode quebrar a indentação de blocos `try/except` ao redor da substituição. Verifique as 5 linhas antes e depois.

**SEMPRE verificar se o servidor roda WSGI ou ASGI** — `manage.py runserver` (WSGI) não tem event loop rodando. A `TaskQueue` e o `Scheduler` só sobem no `LifespanASGI.startup()` do Daphne. Sem event loop, `enqueue_task_sync()` enfileira na `TaskQueue` mas **nunca executa** — a task fica enfileirada para sempre. Sintoma: tasks de background (gerar título, indexar documento) nunca completam.

**Como detectar:** Bater em qualquer endpoint e ver o header `Server:` na resposta. Se for `WSGIServer` (Django runserver) ou `Cheroot` (waitress), é WSGI. Se for `daphne` ou `uvicorn`, é ASGI.

**Correção em `config/task_proxy.py`:** Quando a TaskQueue existe mas workers não estão rodando (ou não há event loop), executar a task em uma **thread separada** com `asyncio.run()`. Três cenários:

1. **Sem event loop rodando** (`except RuntimeError`) — cria thread com `asyncio.run()`.
2. **Com loop rodando mas queue sem workers** — mesma abordagem: thread separada.
3. **Com loop rodando e queue com workers** — enfileira normalmente via `asyncio.run_coroutine_threadsafe()`.

**Pitfall crítico:** NÃO tentar `asyncio.run()` inline quando já há um loop rodando (cenário 2). `asyncio.run()` exige que não haja loop no thread atual. Usar `asyncio.ensure_future()` também falha porque a corrotina nunca é executada (ninguém a awaita). A solução correta é uma **daemon thread** com seu próprio `asyncio.run()`:

```python
def enqueue_task_sync(name, coro_factory, *args, **kwargs):
    import asyncio, threading, uuid
    try:
        loop = asyncio.get_running_loop()
        q = get_queue()
        if q._running:
            # Cenário 3: ASGI com workers — enfileira
            task_obj = Task(name=name, coro=coro_factory(*args, **kwargs), ...)
            asyncio.run_coroutine_threadsafe(q.enqueue(task_obj), loop)
            return task_obj.task_id
        else:
            # Cenário 2: loop rodando mas sem workers — thread separada
            _tid = str(uuid.uuid4())
            def _run():
                try:
                    asyncio.run(coro_factory(*args, **kwargs))
                except Exception as exc:
                    logger.error("Task '%s' [%s] falhou: %s", name, _tid, exc)
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            return _tid
    except RuntimeError:
        # Cenário 1: sem loop rodando — thread separada
        _tid = str(uuid.uuid4())
        def _run():
            try:
                asyncio.run(coro_factory(*args, **kwargs))
            except Exception as exc:
                logger.error("Task '%s' [%s] falhou: %s", name, _tid, exc)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return _tid
```

**SEMPRE mover `enqueue_task_sync` para FORA de `sync_to_async`** — quando `enqueue_task_sync` é chamado DENTRO de um bloco `sync_to_async` (que roda em uma thread pool), o `asyncio.get_running_loop()` falha (não há loop na thread pool). O fallback inline cria um novo event loop com `asyncio.run()`, mas a transação `transaction.atomic()` da thread pool **ainda não comitou**. A task inline tenta `Conversation.objects.get(pk=...)` e recebe `DoesNotExist` porque o registro não está visível para a nova conexão de banco. Sintoma: `generate_session_title` nunca completa, título fica como "Nova Conversa" para sempre.

**Correção:** `_build_task` retorna `(task, is_new, conversation_id)` em vez de só `task`. O `post()` async desempacota o tuple e chama `enqueue_task_sync` **fora** do `sync_to_async`, no ASGI event loop principal, onde a transação já comitou e a TaskQueue está rodando:

```python
# ERRADO — dentro de sync_to_async (thread pool, transação não comitada):
def _build_task(self, user, conv_ref, message):
    with transaction.atomic():
        conversation = Conversation.objects.create(...)
        ChatMessage.objects.create(...)
        enqueue_task_sync("generate_title", generate_session_title, str(conversation.id), message)  # ← FALHA: DoesNotExist
        return AgentTask.objects.create(...)

# CERTO — retorna dados, enfileira fora:
def _build_task(self, user, conv_ref, message):
    with transaction.atomic():
        conversation = Conversation.objects.create(...)
        ChatMessage.objects.create(...)
        task = AgentTask.objects.create(...)
        return task, is_new, str(conversation.id)

# No post() async (ASGI event loop, transação comitada):
task, is_new, conv_id = await sync_to_async(self._build_task)(user, conv_ref, message)
if is_new:
    enqueue_task_sync("generate_title", generate_session_title, conv_id, message)  # ← FUNCIONA
```

**SEMPRE verificar se o interceptor `runAgent` usa `activeIdRef.current` (ref) em vez de `ctrl.activeId` (state) ou `base.threadId` (UUID aleatório do construtor)** — quando o `ChatReady` cria o `HttpAgent` com um interceptor `runAgent`, o closure captura `ctrl.activeId` (React state) com o **valor inicial** (null). Quando o usuário clica em uma conversa e digita, o interceptor vê `activeId = null` e cria uma conversa nova. Sintoma: mensagem vai para conversa nova em vez da atual.

**Causa raiz — DUAS armadilhas:**

1. **`ctrl.activeId` é React state, stale no closure.** O closure do interceptor `base.runAgent = async function(...) { ... ctrl.activeId ... }` captura o valor de `activeId` no momento da criação do `HttpAgent` (que é criado uma vez, via `if (!agentRef.current)`). O React state `activeId` muda depois, mas o closure ainda vê o valor antigo.

2. **`base.threadId` NÃO é setado pelo runtime — e é PIOR que não ter interceptor.** O construtor do `HttpAgent` gera um UUID aleatório para `this.threadId`. O runtime do AG-UI **não** seta `agent.threadId` quando troca de thread — ele só chama o adapter. Usar `base.threadId` como fallback é pior que não ter interceptor: o valor é sempre truthy (um UUID fake), então o interceptor passa um UUID inexistente para o backend, que cria uma conversa nova **silenciosamente** (sem erro, sem 404). O usuário vê a mensagem sumir e não entende por quê.

**Correção em 3 partes:**

1. **`onSwitchToThread` no adapter** seta `agent.threadId = threadId` **antes** do fetch REST.
2. **Expor `activeIdRef` no context** (`ThreadListController` + provider value).
3. **Interceptor usa `ctrl.activeIdRef?.current`** (ref, não state) em vez de `ctrl.activeId` ou `base.threadId`.

```tsx
// ERRADO — ctrl.activeId é React state, stale no closure:
base.runAgent = async function (params, subscriber) {
  if (!ctrl.activeId) { ... }  // ← sempre null, closure capturou valor inicial
  ...
};

// ERRADO — base.threadId é UUID aleatório do construtor, sempre truthy:
base.runAgent = async function (params, subscriber) {
  if (base.threadId) { ... }  // ← sempre truthy, UUID fake, backend cria conversa nova
  ...
};

// CERTO — activeIdRef.current é ref, sempre atualizado:
const origRunAgent = base.runAgent.bind(base);
base.runAgent = async function (params, subscriber) {
  const ctrl = controller;
  const pendingId = ctrl.pendingThreadIdRef.current;
  if (pendingId) {
    ctrl.pendingThreadIdRef.current = null;
    base.threadId = pendingId;
    params = { ...params, threadId: pendingId };
    return origRunAgent(params, subscriber);
  }
  // Usa activeIdRef.current (ref, nao state) para evitar stale closure.
  const activeId = ctrl.activeIdRef?.current;
  if (activeId) {
    base.threadId = activeId;
    params = { ...params, threadId: activeId };
    return origRunAgent(params, subscriber);
  }
  // Fallback: sem threadId ativo, cria ou pega a mais recente
  const conversations = ctrl.conversations;
  const mostRecent = conversations && conversations.length > 0 ? conversations[0] : null;
  if (mostRecent) {
    await ctrl.adapter.onSwitchToThread!(mostRecent.uuid);
    await ctrl.refresh();
    base.threadId = mostRecent.uuid;
  } else {
    const conv = await chatApi.createSession();
    await ctrl.adapter.onSwitchToThread!(conv.uuid);
    await ctrl.refresh();
    base.threadId = conv.uuid;
  }
  params = { ...params, threadId: base.threadId };
  return origRunAgent(params, subscriber);
};
```

**NÃO fazer:**
- Usar `ctrl.activeId` dentro do interceptor `runAgent` — é React state, o closure captura o valor inicial.
- Usar `base.threadId` como fallback — o construtor do `HttpAgent` gera um UUID aleatório, sempre truthy, que o backend interpreta como conversa nova.
- Assumir que o runtime seta `agent.threadId` ao trocar de thread — ele NÃO seta, só chama o adapter.

**Após push HEAD:main, sincronizar branch main local** — quando você faz `git push origin HEAD:main` de uma feature branch, o remote `main` é atualizado mas o `main` local fica desatualizado. Commits futuros partem da feature branch e o `main` local fica para trás. Para corrigir:
```bash
git checkout main
git merge feature-branch    # fast-forward
git push origin main         # já está sincronizado, mas confirma
git checkout feature-branch  # volta a trabalhar
```

**SEMPRE usar `git cherry-pick` (não merge) para trazer um commit de docs de uma branch desatualizada** — quando uma branch antiga tem um commit de docs/status (ex: marcar feature como Concluída) mas está MUITO atrás da main (dezenas de arquivos divergentes), `git merge` arrastaria tudo. O `cherry-pick <commit>` aplica só aquele commit na main. Antes, verificar que os arquivos que o commit toca são idênticos entre o parent do commit e a main (`git show <commit>^:<path>` vs `git show main:<path>`) — se forem, o cherry-pick aplica limpo sem conflito. Depois `git push origin main`. A branch antiga pode ser deletada (o commit já foi portado).

**SEMPRE verificar rota dupla ao incluir urls com path parameter** — `path("serve/<slug:slug>/", include("pages.urls"))` captura o slug no prefixo, e se `pages/urls.py` também tem `<slug:slug>/`, o slug é capturado DUAS VEZES → 404. Correção: o prefixo não deve ter o path parameter:
```python
# ERRADO — slug capturado duas vezes:
path("serve/<slug:slug>/", include("pages.urls"))  # + <slug:slug>/ = /serve/<slug>/<slug>/

# CERTO — prefixo sem slug:
path("serve/", include("pages.urls"))  # + <slug:slug>/ = /serve/<slug>/
```

**SEMPRE verificar catch-all slug em routers incluídos em `/api/v1/`** — um `path("<slug:slug>/", page_serve_by_slug)` em `pages/urls.py` captura QUALQUER path de segmento único, inclusive `activity-log/`, `dashboard/`, etc. Se `pages.urls` é incluído em `/api/v1/` ANTES de `activity.urls`, o Django tenta servir `activity-log/` como slug de página → 404. Correção: separar as rotas de slug serve em um arquivo separado (`serve_urls.py`) que só é incluído em `/serve/`, e manter apenas os routers REST em `urls.py` (incluído em `/api/v1/`).

**SEMPRE adicionar proxy no vite.config.ts ao criar nova rota pública** — o frontend (Vite dev server em :8080) só redireciona ao backend (:8000) as rotas listadas em `server.proxy`. Se você adiciona uma rota como `/serve/<slug>/` no backend, precisa adicionar o proxy correspondente no `vite.config.ts`:
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

**SEMPRE verificar se o frontend espera array plano ou paginado ao adicionar paginação no backend** — quando você adiciona `pagination_class` a um ViewSet do DRF que antes retornava `T[]`, a resposta muda para `{ count, next, previous, results: T[] }`. O frontend que consumia `data` como array agora recebe um objeto. Correção em 3 camadas:

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

**SEMPRE verificar se o elemento tem largura fixa ao debuggar sobreposição de texto** — quando o usuário reporta "texto se sobrepondo" em botões de paginação ou ações, a causa raiz mais comum é uma classe CSS com `width` fixa (ex: `.mini-btn { width: 34px; height: 34px }`) que não comporta o texto. Sintoma: o texto transborda e sobrepõe elementos adjacentes no flex container. Correção: remover a classe de largura fixa e usar `padding` explícito + `whiteSpace: "nowrap"` nos botões.

**SEMPRE verificar ícone duplicado por `data-icon` + componente React** — quando um botão tem `data-icon="refresh"` (que renderiza um ícone via CSS `::before` com máscara SVG) E um componente React de ícone (ex: `<RefreshCw>`), o resultado são dois ícones sobrepostos. O `data-icon` renderiza via pseudo-elemento `::before`, e o componente React renderiza o SVG real. Correção: remover `data-icon="X"` e manter apenas o componente React. Este padrão é comum em botões de ação (refresh, add, edit) que foram migrados de HTML puro para React.

**SEMPRE verificar contraste de tokens gray no dark mode** — no tema escuro do Crewbotics, `gray-200` e `gray-300` valem `#404040` — quase invisível no fundo `#0A0A0A`. Para texto descritivo (descrições de atividades, labels), usar `gray-600` (`#A3A3A3`). Para texto secundário (nomes de usuário, metadados, timestamps), usar `gray-400` (`#525252`). Nunca usar `gray-200` ou `gray-300` para texto em dark mode — eles só servem para bordas e separadores.

**SEMPRE verificar se os tokens CSS usados existem no tema escuro** — tokens como `gray-800` e `gray-700` NÃO EXISTEM no sistema de tokens do Crewbotics. O tema escuro só define `gray-100` a `gray-600` + `gray-900`. Usar tokens inexistentes resulta em fundo/borda transparente (herda do pai). Correção: mapear para tokens existentes:
  - `gray-800` (inexistente) → `gray-100` (`#262626` no dark mode) para fundo escuro
  - `gray-700` (inexistente) → `gray-300` (`#404040` no dark mode) para borda
  - `gray-200` (`#404040` no dark mode) → `gray-600` (`#A3A3A3`) para texto
  - `gray-500` (`#737373`) → `gray-400` (`#525252`) para texto secundário

**SEMPRE verificar import de bibliotecas com lazy proxy** — pacotes que usam metaclasses para lazy-loading (ex: `ddgs` com `_ProxyMeta`) podem falhar com `ImportError: cannot import name 'etree'` mesmo quando o módulo está instalado. O proxy tenta carregar dependências no momento do primeiro acesso, e se o `sys.path` tiver um venv diferente na frente (ex: Hermes venv com `lxml` sem `etree`), a importação falha. Correção: importar direto do submódulo (`from ddgs.ddgs import DDGS`) em vez do pacote raiz (`from ddgs import DDGS`). Ver `references/ddgs-api-quirks.md` para detalhes da API do ddgs 9.x.

### SEMPRE verificar loading dots em mensagens do assistente (AG-UI React)

Quando o usuário reporta "três pontinhos aparecem em todos os balões de mensagens do copilot", a causa raiz é que o `<ThreadPrimitive.If running>` com os loading-dots está DENTRO do componente `AssistantMessage`, que é renderizado para CADA mensagem. Quando o runtime está processando, `If running` é `true` para TODAS as mensagens, não só a última. Correção: mover os loading-dots para FORA do `ThreadPrimitive.Messages`, entre o fechamento do `Messages` e o `Viewport`. Renderizar como uma bolha separada de "assistente pensando" no final da lista.

> **Endpoints de mensagem do chat** (`branches`, `branch-version`): resolver por `uuid`+`id`, ignorar IDs otimistas AG-UI (`__optimistic__`/`msg_`) p/ evitar 500 em loop; **carrosséis HTML/CSS**: portar p/ SVG + `resvg-py`+`font_files` (sem browser, ECS-safe). Código em `references/agui-message-id-resolve-and-carousel-templates.md`.

**NUNCA usar `s.optional.message?.status?.type === "in_progress"` para detectar streaming** — este selector verifica o status da mensagem **atual** sendo renderizada pelo `AssistantMessage`. Quando a mensagem aparece no DOM, ela já foi finalizada (status é "complete" ou similar), então `isStreaming` sempre retorna `false`. O loading-dot nunca aparece. A abordagem correta é `ThreadPrimitive.If running` **fora** do loop de mensagens, que verifica se o runtime AG-UI está processando alguma requisição, independente de qual mensagem está sendo renderizada.

```tsx
// ERRADO — isStreaming sempre false, loading-dots nunca aparecem:
AssistantMessage: () => {
  const isStreaming = Aui.useAuiState?.(
    (s: any) => s.optional.message?.status?.type === "in_progress",
  );
  return (
    <MessagePrimitive.Root>
      <MessagePrimitive.Parts />
      {isStreaming && <div className="loading-dots">...</div>}  {/* ← nunca aparece */}
    </MessagePrimitive.Root>
  );
}

// CERTO — ThreadPrimitive.If running fora do loop:
<ThreadPrimitive.Messages components={{...}} />
<ThreadPrimitive.If running>
  <div className="msg msg--ai">
    <div className="msg__bubble">
      <div className="loading-dots">...</div>
    </div>
  </div>
</ThreadPrimitive.If>
```

**SEMPRE verificar `};` vs `}` em objetos JSX** — ao editar objetos literais com múltiplos componentes inline (ex: `components={{ Text: ..., UserMessage: ..., AssistantMessage: ... }}`), o último item NÃO deve ter `;` após o `}`. Um `};` dentro de um objeto literal JSX causa `[PARSE_ERROR] Expected ',' or '}' but found ';'`. O Vite/oxc parser é estrito. Correção: o último item termina com `}` (sem `;`), e o `;` só vem depois do fechamento do objeto: `}};`.

```tsx
{/* ERRADO — loading dots dentro de AssistantMessage, aparece em todas */}
<ThreadPrimitive.Messages components={{
  AssistantMessage: () => (
    <div>
      <MessagePrimitive.Parts />
      <ThreadPrimitive.If running>   {/* ← aparece em TODAS as mensagens */}
        <div className="loading-dots">...</div>
      </ThreadPrimitive.If>
    </div>
  ),
}} />

{/* CERTO — loading dots fora do loop de mensagens */}
<ThreadPrimitive.Messages components={{...}} />
<ThreadPrimitive.If running>
  <div className="msg msg--ai">
    <div className="msg__bubble">
      <div className="loading-dots">...</div>
    </div>
  </div>
</ThreadPrimitive.If>
```

**SEMPRE testar no browser após corrigir bugs de frontend React** — quando o bug é no frontend (duplicação de chamadas, ReferenceError, componente quebrando), não confie apenas no `bun run build`. O build compila TypeScript, mas não detecta erros de runtime como `ReferenceError: agent is not defined` ou lógica que causa chamadas duplicadas. Após cada correção:

1. `bun run build` — verifica se compila
2. Recarregar a página no browser
3. Abrir DevTools → Console (verificar erros)
4. Abrir DevTools → Network (verificar chamadas duplicadas)
5. Testar a ação que estava quebrada

**NÃO fazer:** editar → build → commitar sem testar no browser. O build passa mesmo com bugs de runtime. O usuário vai reportar o erro e você vai precisar de mais 5 iterações.

**REGRRA DE OURO:** se o usuário reportar um erro de frontend que você corrigiu, NÃO faça outra correção sem testar no browser primeiro. Cada iteração sem teste gera 3-5 correções adicionais. Teste no browser após CADA correção, não após o commit.

**REGRRA DE FERRO:** se o usuário disser "teste no browser" ou "vc esta mexendo e nao testando", PARE imediatamente de editar. Faça `bun run build`, recarregue a página, teste manualmente, e só então continue editando. O usuário prefere que você teste primeiro e edite depois, não o contrário.

**SEMPRE verificar se a variável que você referencia existe no escopo do componente** — `ReferenceError: X is not defined` é o erro mais comum ao editar componentes React. Antes de usar uma variável em um callback ou JSX, verifique se ela:
- Foi declarada no mesmo componente (via `useState`, `useRef`, `useMemo`, etc.)
- Foi recebida como prop
- Foi recebida de um hook (ex: `useConversationThreadList()`)
- NÃO foi declarada em um componente pai diferente (ex: `agent` está em `ChatReady`, não em `ThreadListSidebar`)

**SEMPRE verificar se o `agentRef` type é `any`** — o `HttpAgent` do `@ag-ui/client` tem um setter real (get/set) em `threadId`. Se o tipo for `{ threadId: string | null }`, a atribuição `agent.threadId = uuid` seta uma propriedade plana, não o setter — o fetch nunca dispara. Use `React.MutableRefObject<any>` para acessar o setter real.

**SEMPRE consumir o stream SSE em testes que verificam persistência** — `StreamingHttpResponse` só persiste a `ChatMessage` quando o stream é totalmente consumido. Sem `async_to_sync(_collect)(resp)`, o `_finish()` nunca roda e a mensagem do assistente não é criada no banco. Sintoma: testes que criam conversa + enviam mensagem encontram só a mensagem do usuário, nunca a do assistente.

```python
# ERRADO — stream não consumido, _finish() nunca roda:
resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
assert resp.status_code == 200
msgs = ChatMessage.objects.filter(conversation=conv)
assert msgs.count() == 2  # ← FALHA: só tem 1 (a do user)

# CERTO — consome o stream antes de verificar:
resp = _post(client, {"message": "Oi", "conversationId": str(conv.uuid)}, user=user)
assert resp.status_code == 200
async_to_sync(_collect)(resp)  # ← consome o stream, _finish() persiste a resposta
msgs = ChatMessage.objects.filter(conversation=conv)
assert msgs.count() == 2  # ← PASS: user + assistant
```

**SEMPRE mockar `is_configured` em testes de AG-UI** — o `AguiReActEngine._run_loop()` verifica `llm_client.is_configured()` primeiro. Se retornar `False`, chama `_stub_run()` que **não usa** `litellm.acompletion`. Mockar só o `acompletion` sem mockar `is_configured` faz o teste passar isolado mas falhar em lote (porque o stub não persiste mensagem do assistente).

```python
# CERTO — mocka ambos:
from chat import llm_client
import litellm
monkeypatch.setattr(llm_client, "is_configured", lambda: True)
monkeypatch.setattr(litellm, "acompletion", _fake_acompletion(_text_chunks("OK.")))
```

**SEMPRE verificar código morto ao encontrar duplicação** — quando dois arquivos têm implementações similares (ex: `AguiChatPage.tsx` e `AguiRuntimeProvider.tsx` ambos criam `HttpAgent` com interceptor), verifique se o segundo é importado em algum lugar. Se não for, é código morto e deve ser removido, não mantido.

### GrapesJS RTE — NÃO customizar o RTE

O RTE (Rich Text Editor) do GrapesJS é frágil. Toda customização introduz race conditions quebram o duplo-clique para editar texto. **Regra de ouro:** não adicione handlers em `rte:enable`, `component:selected`, `canvas:frame:load` ou `redelegateTextViews`. O GrapesJS vanilla gerencia o RTE corretamente.

**Padrões que SEMPRE quebram o RTE:**
- `demoteTextContainers` — muda tipo de componente pai, re-renderização destrói RTE ativo no filho
- `redelegateTextViews` — `delegateEvents()` re-liga handlers de dblclick, RTE interpreta segundo duplo-clique
- `ed.Keymaps.removeAll()` em `rte:enable` — remove proteção interna que impede RTE de perder foco
- `requestAnimationFrame(() => requestAnimationFrame(focusEditing))` — double rAF compete com foco do RTE
- Handler `component:selected` que re-seleciona componente em edição — interrompe RTE
- `range.selectNodeContents(el)` + `range.collapse(false)` — sobrescreve seleção de texto do usuário

**Proteção para `ed.getWrapper()`:** o método lança `TypeError` quando chamado antes da inicialização completa. Use `if (!wrapper) return;` ou try/catch com retry.

**SEMPRE pular `notify()` (save) enquanto o RTE estiver ativo** — o `notify()` debounced (400ms) dispara em `component:update`, que é emitido QUANDO o RTE ativa. `getEditorData()` chama `ed.getHtml()` que serializa a árvore de componentes — isso causa um re-render do canvas que **reseta o cursor para o início do texto**. Depois disso, qualquer clique no texto volta o cursor pro início porque o re-render substitui o DOM. Correção: adicionar `if (ed.getEditing()) return;` no início do callback do `setTimeout` do `notify()`:

```tsx
const notify = () => {
  if (notifyTimer) clearTimeout(notifyTimer);
  notifyTimer = setTimeout(() => {
    // NÃO salvar enquanto o RTE estiver ativo — ed.getHtml() serializa
    // a árvore de componentes e causa re-render que reseta o cursor
    // para o início do texto. O save acontece no blur natural (quando
    // o usuário clica fora do componente).
    if (ed.getEditing()) return;
    const data = getEditorData();
    if (data) onChange(data);
  }, 400);
};
```

**Sintoma:** usuário dá duplo-clique em texto → RTE ativa → cursor vai pro início → clicar em qualquer posição do texto volta o cursor pro início. O save (onChange) está disparando durante a edição e resetando o DOM.

**NUNCA usar `s.optional.message?.status?.type === "in_progress"` para detectar streaming no AG-UI** — este selector verifica o status da mensagem **atual** sendo renderizada pelo `AssistantMessage`. Quando a mensagem aparece no DOM, ela já foi finalizada (status é "complete" ou similar), então `isStreaming` sempre retorna `false`. O loading-dot nunca aparece. A abordagem correta é `ThreadPrimitive.If running` **fora** do loop de mensagens, que verifica se o runtime AG-UI está processando alguma requisição, independente de qual mensagem está sendo renderizada.

```tsx
// ERRADO — isStreaming sempre false, loading-dots nunca aparecem:
AssistantMessage: () => {
  const isStreaming = Aui.useAuiState?.(
    (s: any) => s.optional.message?.status?.type === "in_progress",
  );
  return (
    <MessagePrimitive.Root>
      <MessagePrimitive.Parts />
      {isStreaming && <div className="loading-dots">...</div>}  {/* ← nunca aparece */}
    </MessagePrimitive.Root>
  );
}

// CERTO — ThreadPrimitive.If running fora do loop:
<ThreadPrimitive.Messages components={{...}} />
<ThreadPrimitive.If running>
  <div className="msg msg--ai">
    <div className="msg__bubble">
      <div className="loading-dots">...</div>
    </div>
  </div>
</ThreadPrimitive.If>
```

**Conversa duplicada vazia toma o topo da sidebar (pendingThreadIdRef nunca setado)** — quando o usuário reporta "começo a conversar, o chat responde, mas ao dar refresh a última conversa some", a causa raiz é que o `pendingThreadIdRef` foi projetado para evitar duplicação de conversa na primeira mensagem mas **nunca é setado** no `sendPrompt` do adapter. O interceptor `runAgent` lê e limpa esse ref, mas como fica sempre `null`, cai no fallback de criar conversa nova (duplicata vazia toma o topo da sidebar; a conversa real parece sumir no refresh). Correção: setar `pendingThreadIdRef.current = conv.uuid` **antes** de retornar no `sendPrompt`. Ver `references/agui-chat-duplicate-conversation-pending-ref.md`.

**SEMPRE usar `runtimeRef` (ref) em vez de `runtime` (state) em `useEffect`** — o hook `useAgUiRuntime` retorna um objeto NOVO a cada render. Se você colocar `runtime` nas dependências de um `useEffect`, ele dispara em loop infinito: effect → switchToThread → setState → re-render → novo runtime → effect → ... Use `runtimeRef` (ref) para acessar o runtime dentro do effect:

```tsx
// ERRADO — runtime muda a cada render, loop infinito:
const runtime = useAgUiRuntime({...});
useEffect(() => {
  runtime.threads.switchToThread(id);
}, [runtime]);  // ← loop infinito

// CERTO — runtimeRef é estável:
const runtimeRef = useRef(runtime);
runtimeRef.current = runtime;
useEffect(() => {
  const r = runtimeRef.current;
  r?.threads?.switchToThread(id);
}, [controller.bootReady]);  // ← sem runtime na deps
```

**SEMPRE usar `bootReady` state para carregar conversa auto-selecionada no boot** — o `ThreadListProvider` auto-seleciona a conversa mais recente (seta `activeId`) mas não chama `onSwitchToThread` porque o runtime ainda não existe. Adicione `bootReady` (React state) no provider, setado `true` após o auto-select. No `ChatReady`, adicione um `useEffect` que observa `bootReady` + `activeIdRef.current` e chama `runtime.threads.switchToThread(id)`:

```tsx
// No provider (useConversationThreadList.tsx):
const [bootReady, setBootReady] = useState(false);

// No auto-select useEffect:
useEffect(() => {
  if (autoSelectDone.current) return;
  if (conversations.length === 0) return;
  autoSelectDone.current = true;
  const mostRecent = conversations[0];
  if (!mostRecent) return;
  threadIdRef.current = mostRecent.uuid;
  setActiveId(mostRecent.uuid);
  setBootReady(true);
}, [conversations]);

// No ChatReady (AguiChatPage.tsx):
const bootLoaded = useRef(false);
useEffect(() => {
  if (bootLoaded.current) return;
  if (!controller.bootReady) return;
  const id = controller.activeIdRef?.current;
  if (!id) return;
  bootLoaded.current = true;
  const r = runtimeRef.current;
  if (r?.threads?.switchToThread) {
    r.threads.switchToThread(id);
  }
}, [controller.bootReady, controller.activeIdRef?.current]);
```

### SEMPRE proteger `ed.getWrapper()` com null check ou try/catch em GrapesJS

O método `Editor.getWrapper()` do GrapesJS lança `TypeError: Cannot read properties of undefined (reading 'getWrapper')` quando chamado antes do editor completar a inicialização interna. Isso acontece em callbacks registrados em `canvas:frame:load` e em `requestAnimationFrame` duplo. Proteja com:

```tsx
// Opção 1 — null check (quando o wrapper pode ser undefined):
const wrapper = ed.getWrapper();
if (!wrapper) return;

// Opção 2 — try/catch com retry (quando o erro vem de dentro do getWrapper):
try {
  const wrapper = ed.getWrapper();
  if (!wrapper) return;
  // ... usa wrapper ...
} catch {
  requestAnimationFrame(() => requestAnimationFrame(redelegateTextViews));
}
```

### SEMPRE remover handler `component:selected` que re-seleciona o componente em edição

Quando o RTE está ativo e o usuário clica no texto para selecionar/posicionar o cursor, o clique propaga para o canvas e o GrapesJS seleciona o componente sob o cursor. Um handler `component:selected` que re-seleciona o componente em edição interrompe o RTE e perde a seleção de texto. **Remova** esse handler — o GrapesJS já gerencia internamente que o RTE não perde foco quando o usuário clica no canvas.

### SEMPRE remover `selectNodeContents` + `collapse` do handler `rte:enable`

O handler `rte:enable` que foca o elemento em edição não deve chamar `range.selectNodeContents(el)` + `range.collapse(false)` — isso sobrescreve a seleção de texto que o usuário acabou de fazer com duplo-clique. Apenas foque o elemento se ele não está ativo:

```tsx
ed.on("rte:enable", () => {
  const focusEditing = () => {
    try {
      const editing = ed.getEditing?.();
      const view = editing?.getView?.() as { el?: HTMLElement } | undefined;
      const el = view?.el;
      const doc = ed.Canvas.getDocument();
      if (!el || !doc) return;
      if (doc.activeElement === el) return;
      el.focus();  // ← só foca, não mexe na seleção
    } catch { /* best-effort */ }
  };
  requestAnimationFrame(() => requestAnimationFrame(focusEditing));
});
```

### SEMPRE remover keymaps específicos (não todos) no `rte:enable`

O handler `rte:enable` que remove keymaps não deve chamar `ed.Keymaps.removeAll()` — isso remove a proteção interna do GrapesJS que impede o RTE de perder foco. Remova apenas keymaps que interferem com edição de texto inline:

```tsx
ed.on("rte:enable", () => {
  const toRemove = [
    "core:copy", "core:paste", "core:cut",
    "core:component-outline", "core:component-delete",
  ];
  for (const id of toRemove) {
    try { ed.Keymaps.remove(id); } catch { /* noop */ }
  }
});
ed.on("rte:disable", () => {
  // Não restaura keymaps — o GrapesJS os recria internamente
});
```

```typescript
// ERRADO — return fora do try, messages fora de escopo:
try {
  const conv = await chatApi.getSession(threadId);
  const messages = (conv.messages ?? []).map(...);
} finally {
  setIsLoading(false);
}
return { messages };  // ← ReferenceError

// CERTO — return dentro do try:
try {
  const conv = await chatApi.getSession(threadId);
  const messages = (conv.messages ?? []).map(...);
  return { messages };
} finally {
  setIsLoading(false);
}
```

**SEMPRE adicionar `console.debug` no interceptor `runAgent`** — quando o bug de thread switching acontece, não há log no console para diagnosticar qual threadId foi usado. Adicione `console.debug("[runAgent]", ...)` em cada branch do interceptor (pending, activeId, fallback, new session):

```tsx
console.debug("[runAgent] using activeId:", activeId);
console.debug("[runAgent] fallback to mostRecent:", mostRecent.uuid);
console.debug("[runAgent] created new session:", conv.uuid);
```

**SEMPRE expor `window.__chatDebug` para debug remoto** — após criar o HttpAgent e o controller, exponha o estado do chat no console do browser:

```tsx
if (typeof window !== "undefined") {
  (window as any).__chatDebug = {
    agent,
    controller,
    get activeId() { return controller.activeId; },
    get agentThreadId() { return agent?.threadId; },
    get conversations() { return controller.conversations; },
  };
}
```

Isso permite que o usuário digite `__chatDebug` no console do DevTools para inspecionar o estado atual do chat.

- Import de módulo que foi deletado (ex: `agents.tasks` → `agents.tasks_async`)
- Import inserido dentro de um multi-line import (dentro dos parênteses de `from .models import (`)
- Função que existia no módulo antigo mas não foi portada para o novo
- Indentação quebrada no bloco ao redor da substituição
- Import duplicado: linha antiga + linha nova lado a lado (a antiga quebra, a nova funciona)
- `manage.py` travando por conflito de `lxml` do Hermes (corrigir `sys.path` no manage.py)
- `crewai_tools_adapter.py` travando o boot para sempre (solução: deletar o módulo inteiro)
- Chamada de função `async def` em teste síncrono sem `asyncio.run()`
- `doc.id` vs `doc.pk` em testes de knowledge (usar `doc.pk`)
- `run_pipeline` está em `crew_runner_async`, não em `tasks_async`
- `asyncio.run(asyncio.run(...))` duplicado
- Settings que testes referenciam foram deletadas (ex: `CELERY_TASK_ALWAYS_EAGER`, `CREW_RUN_STALE_AFTER`, `LLM_MODEL`)
- Testes com `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` quebram quando a setting não existe mais
- Lambda mock em testes não aceita argumentos posicionais (ex: `lambda **kw` vs `lambda *a, **kw`)
- `embedding dimension mismatch` em testes (ex: vetor 3d vs 768d esperado pelo pgvector)
- **`operator does not exist: uuid = integer` em todos os endpoints filtrados por org** — migration de PK UUID→bigint que esqueceu de retipar `organization_id` nas tabelas de domínio; e **`exclude`/`__in` é case-sensitive no Postgres** (não dar `.lower()` nos valores). Ambos em `references/organization-fk-retype-uuid-bigint.md`.

**SEMPRE verificar se TODAS as funções de seed copiam TODOS os campos do modelo** — quando você adiciona um campo novo a um modelo Django (ex: `category` em `CrewTemplate`), precisa atualizar **todas** as funções de seed que criam instâncias desse modelo, não só a principal. É comum ter funções de seed separadas (`crew_seed.py` + `agency_crew_seed.py`) e esquecer de adicionar o campo novo na secundária. Sintoma: o seed roda sem erro, mas o campo fica vazio no banco. Correção: antes de criar um seed, listar todos os campos do modelo com `[f.name for f in Model._meta.get_fields()]` e garantir que cada seed function seta todos.

**SEMPRE mover bugs [Corrigido] e features [Concluído] para `.hermes/inbox/processed/`** — após corrigir um bug (ou concluir uma feature), o arquivo da inbox fica com `**Status:** [Corrigido]`/`[Concluído]` mas **continua na pasta ativa** (`inbox/bugs/`, `inbox/features/`). Ao consolidar a inbox, mova esses itens para `inbox/processed/` com `git mv` (preserva histórico). Itens sem status explícito ou com status `[Aberto]`/`[Reclassificado]` ficam na pasta ativa. Deixar o roadmap `tasks.md` desatualizado é comum — ao revisar o que "falta", cruze o roadmap com o código real (muitos TSKs marcados `[ ]` já estão implementados; ex.: ActivityLog vive no app `activity/` não `utils/`, e password-reset backend já está pronto — só faltam páginas frontend).

**SEMPRE rodar `manage.py migrate` no dev DB após mergear uma feature com migration nova** — quando você mergea na main uma feature que adiciona um campo/modelo (ex: `chat.0012_conversation_knowledge_folder`), o código (models/serializers) fica atualizado mas o banco de dev NÃO tem a coluna até você rodar `manage.py migrate`. Sintoma: endpoint que consulta o modelo retorna 500 com `psycopg.errors.UndefinedColumn: column <tabela>.<campo>_id does not exist`. O pytest não pega isso (cria schema do zero); só aparece no dev/prod. Correção: `manage.py migrate <app>` (ou `manage.py migrate` geral) e validar com `manage.py shell -c "from <app>.models import <Model>; <Model>.objects.all()[:1]"`. Verificar migrations pendentes com `manage.py showmigrations <app> --plan` (linhas `[ ]` = não aplicadas).

### CrewAI 1.15.5 — execução de crews quebra silenciosamente

Quando o Copilot acha a crew, chama `execute_crew`, mas a crew "não roda" (run fica `QUEUED` ou quebra com erro que não propaga ao chat), consulte `references/crewai-crew-execution-pitfalls.md`.

**SEMPRE verificar se a crew rodou em STUB ao reiniciar o backend via subprocess** — se o run completa DONE mas todos os outputs são `[STUB — crewai ausente]` MESMO com o Gemini configurado (`is_configured()=True`, log mostra `LiteLLM ... provider = gemini`), a causa é que o `import crewai` falhou dentro do processo reiniciado por falta das env vars do Windows (`USERPROFILE`, `HOME`, `LOCALAPPDATA`, `APPDATA`) que o `chromadb`/`crewai_core` exigem. `_crewai_available()` retorna `False` → cai no stub. Correção: relançar o Daphne herdando `os.environ` (só sobrescrever PYTHONPATH/DJANGO_SETTINGS_MODULE) e validar com `python -c "import crewai"` no MESMO env. Detalhes em `references/crewai-stub-on-subprocess-restart.md`.

**SEMPRE verificar se o `import crewai` funciona no processo do servidor quando a crew roda em STUB** — se o card mostra `[STUB — crewai ausente]` mas o Gemini está configurado (`is_configured()` True, chave no `.env`), a causa é o `import crewai` falhando dentro do Daphne, não a chave. No Windows, o crewai 1.15.5 puxa `chromadb` (`Path.home()`) e `crewai_core` (`Path(LOCALAPPDATA)`); se o processo não tem `USERPROFILE`/`HOME`/`LOCALAPPDATA` no ambiente (comum ao relançar via `subprocess.Popen` com env construído à mão), o import quebra com `RuntimeError: Could not determine home directory` ou `TypeError ... not 'NoneType'` → `_crewai_available()` retorna False → stub. Correção: relançar o Daphne com o ambiente Windows completo (USERPROFILE, HOMEDRIVE, HOMEPATH, HOME, TEMP, TMP, LOCALAPPDATA, APPDATA). Verificar com `python -c "import crewai"` usando o MESMO env antes de relançar. Detalhes em `references/crewai-stub-windows-env.md`. Resumo dos pitfalls:
- `kickoff()` síncrono QUEBRA com múltiplas tasks (`cannot schedule new futures after shutdown`) — usar `kickoff_async()` via `asyncio.run()` em daemon thread.
- `build_llm_kwargs`: providers nativos (gemini) precisam model SEM prefixo e SEM `provider` explícito, senão 404 no Gemini.
- `OutputStatus` enum NÃO tem `DONE` (só PENDING/APPROVED/REJECTED) — usar `ExecutionStatus.DONE`.
- `sanitize_output(text)` aceita 1 arg.
- `build_tools(crew, allow_ask=True)` e `extract_integration_nodes(graph)` — assinaturas corretas pós-migração asyncio.
- `enqueue_task_sync` no `except RuntimeError`: tasks longas (`run_crew`) em daemon thread, NUNCA inline (senão o Daphne mata o SSE).
- `execute_crew` deve validar os inputs obrigatórios do `crew.input_schema` antes de disparar (senão o agente pede os dados que deveriam ter sido passados).
- `per_agent_context` no runner espera STRING, não dict — converter `{member: {key: val}}` em texto legível antes de injetar no backstory.
- Frontend: exibir `output.executionStatus` (DONE/RUNNING/ERROR), NÃO `output.status` (PENDING/APPROVED/REJECTED) — o status de aprovação fica PENDING mesmo quando a task rodou.

**SEMPRE verificar o escopo ao inserir blocos grandes via find-and-replace** — `content.replace(old, new)` com âncora não-única pode inserir o bloco DENTRO de uma função (compila mas corrompe a lógica). Prevenção: âncoras com linhas de contexto ACIMA e ABAIXO; verificar com `compile()`; conferir visualmente a indentação ao redor. Se corromper, reescreva o arquivo inteiro.

**SEMPRE verificar que o `category` é passado ao criar CrewTemplates via seed** — o modelo `CrewTemplate` tem campo `category` que é usado pelo frontend para filtrar templates no marketplace. Se a função de seed não setar `obj.category`, o template aparece sem categoria no marketplace. Correção: adicionar `obj.category = crew.get("category", "")` na função de seed, tanto em `crew_seed.py` quanto em `agency_crew_seed.py`.

**SEMPRE verificar que o `input_schema` do JSON é usado, não o do código** — a função `upsert_agency_crews` em `agency_crew_seed.py` usa `input_schema_for(crew_slug)` que busca em `INPUT_SCHEMAS` no código. Mas o JSON `agency_crew_templates.json` também tem `input_schema` em cada crew. Se os dois divergirem, o código vence. Para garantir consistência, ou (a) remove o `input_schema` do JSON e mantém só no código, ou (b) faz o seed ler do JSON. A opção (a) é preferível para manter a fonte da verdade no código Python (mais fácil de testar e versionar).

**SEMPRE verificar o prefixo `agency-` no `member_slug` do seed de runbooks** — o `agency_crew_seed.py` (Fase 2) usa `member_slug` com prefixo `agency-` (ex: `agency-trend-researcher`) no JSON `agency_crew_templates.json`, mas os `BotTemplate` têm `metadata["source_slug"]` SEM o prefixo (ex: `trend-researcher`). Sintoma: o seed roda sem erro, as 5 crews são criadas, mas `members.filter(bot_template__isnull=False).count()` é 0 — nenhum membro vinculado ao agente. O runbook fica "vazio" de agentes reais.

**Correção em 2 partes:**
1. **Lookup tolerante ao prefixo** em `upsert_agency_crews` — indexar `bots_by_slug` também sem o prefixo, e resolver com helper que tenta o slug completo e depois sem `agency-`:
```python
def _resolve_bot(bots_by_slug, member_slug):
    if not member_slug:
        return None
    bot = bots_by_slug.get(member_slug)
    if bot:
        return bot
    if member_slug.startswith("agency-"):
        return bots_by_slug.get(member_slug[len("agency-"):])
    return None
```
2. **Criar BotTemplates faltantes** — se algum `member_slug` não existir como `source_slug` (ex: `multi-platform-publisher`, `pr-communications-manager`), adicionar ao `agents/seed_data/agency_agents.json` e rodar `manage.py seed_agency_agents` antes do `seed_agency_runbooks`.

**Verificação:** após o seed, conferir `members.filter(bot_template__isnull=False).count()` == `members.count()` para cada runbook. Ordem de seed: `seed_agency_agents` → `seed_agency_runbooks`.

**SEMPRE verificar que TODAS as funções de seed copiam TODOS os campos do modelo** — quando você adiciona um campo novo a um modelo Django (ex: `category` em `CrewTemplate`), precisa atualizar **todas** as funções de seed que criam instâncias desse modelo, não só a principal. É comum ter funções de seed separadas (`crew_seed.py` + `agency_crew_seed.py`) e esquecer de adicionar o campo novo na secundária. Sintoma: o seed roda sem erro, mas o campo fica vazio no banco. Correção: antes de criar um seed, listar todos os campos do modelo com `[f.name for f in Model._meta.get_fields()]` e garantir que cada seed function seta todos.

**SEMPRE verificar o escopo ao inserir blocos grandes via find-and-replace** — `content.replace(old, new)` com âncora não-única pode inserir o bloco DENTRO de uma função (compila mas corrompe a lógica). Prevenção: âncoras com linhas de contexto ACIMA e ABAIXO; verificar com `compile()`; conferir visualmente a indentação ao redor. Se corromper, reescreva o arquivo inteiro.

### PREFERÊNCIA DO USUÁRIO — o Copilot NUNCA expõe ids/uuid ao usuário final

O usuário exige que o Copilot **nunca fale de id ou uuid para o usuário final**. Ele deve referenciar crews, páginas, documentos e pastas da base de conhecimento **SEMPRE pelo NOME** (ex.: "a crew Presença Digital", "o documento briefing-produto.txt", "a página de vendas"). Os ids/uuid são usados internamente para executar ações, mas nunca mostrados ou pedidos ao usuário.

**Sintoma do bug:** o Copilot responde "A crew com o ID '22' não foi encontrada" ou "Encontrei a crew X (ID: 22)". O LLM recebe os resultados das ferramentas (que contêm `id`, `uuid`, `run_id`, `crew_id`, `folder_id` etc.) e os repete nas respostas de texto.

**Correção (2 camadas):**
1. **System prompt** — adicionar regra explícita em AMBOS os prompts:
   - `chat/engine.py` → `_build_system_prompt()` (engine AG-UI do Copilot)
   - `chat/llm.py` → `build_system_prompt()` (chat normal / orquestração)
   ```
   NUNCA exponha IDs, UUIDs ou identificadores técnicos ao usuário final.
   Referencie crews, páginas, documentos e pastas SEMPRE pelo NOME. Os
   resultados das ferramentas podem conter id, uuid, run_id, crew_id,
   folder_id etc. — use-os internamente para executar ações, mas NUNCA
   os mostre ou peça ao usuário. Se precisar que o usuário escolha algo,
   liste pelos nomes.
   ```
2. **Skills** — os retornos de `list_crews`, `hire_crew`, `create_crew` devem usar `str(c.uuid)` (não `str(c.id)`), e o `execute_crew` deve resolver por uuid com fallback (ver seção abaixo). Componentes Generative UI (SiteCard, PlaybookCard) carregam `pageId`/`run_id` nas props para o frontend renderizar — isso é correto, não é texto ao usuário.

**Testes:** verificar que o system prompt contém a regra; testes que esperam `str(crew.id)` (PK) precisam ser atualizados para `str(crew.uuid)`.

### SEMPRE usar `uuid` (não `id` numérico) como referência externa de crews

O contrato do Crewbotics (AGENTS.md §11) define que **`uuid` é a referência externa via API**, não o `id` numérico (PK). O `CoreModel` tem `id` (UUID PK) E `uuid` (UUID secundário). Os serializers expõem `id = source="uuid"` — então o frontend já recebe o uuid como `id`. Mas as **skills do Copilot** e helpers de intent frequentemente usam `str(c.id)` (o PK numérico) por engano.

**Sintoma clássico:** o Copilot lista a crew ("Presença Digital para Profissionais, ID: 22"), o usuário pede para acionar, e o Copilot responde "A crew com o ID '22' não foi encontrada". O `list_crews` retornou `str(c.id)` = "22" (PK), mas o `execute_crew` resolve por `uuid`/`pk` e não acha.

**Causa raiz:** `_uuid.UUID("22")` levanta `ValueError`, então o bloco de resolução por uuid é pulado, e a busca por nome também falha.

**Correção em 2 camadas:**
1. **Skills que LISTAM crews** (`list_crews`, `hire_crew`, `create_crew`) devem retornar `str(c.uuid)`, não `str(c.id)`.
2. **Skills que EXECUTAM crews** (`execute_crew`) devem resolver por `uuid` primeiro, com fallback para `id` numérico (pk) e depois nome:
```python
crew = None
import uuid as _uuid
try:
    _uuid.UUID(str(crew_id))
    crew = CrewInstance.objects.filter(uuid=crew_id, organization=self.org).first()
except (ValueError, TypeError):
    pass
if not crew:
    try:
        crew = CrewInstance.objects.filter(pk=int(crew_id), organization=self.org).first()
    except (ValueError, TypeError):
        pass
if not crew:
    qs = CrewInstance.objects.filter(organization=self.org)
    crew = (qs.filter(custom_name__iexact=crew_id).first()
            or qs.filter(custom_name__icontains=crew_id).first())
```

**Varredura completa:** ao corrigir, procure TODOS os lugares que usam `str(c.id)`/`crew.id`/`instance.id` em contexto de crew — `chat/intent.py` (`crew_context_from_queryset`), `chat/views.py` (contexto de crews, orquestração, `CrewIntentView`), `chat/skills/*`. O serializer expõe `id=uuid`, então o frontend está correto; o bug é sempre no backend.

**Testes:** testes que esperam `str(crew.id)` (PK) precisam ser atualizados para `str(crew.uuid)`.

### SEMPRE verificar se o crewai importa no processo ao ver stub "(crewai ausente)"

Quando a crew roda em modo stub `[STUB — crewai ausente]` mas `llm_client.is_configured()` é True (Gemini/OpenAI configurado, e até aparecem chamadas LiteLLM no log de OUTRAS partes do Copilot), a causa raiz é `_crewai_available()` retornar False porque `import crewai` falha DENTRO do processo em execução — não é problema de chave.

No Windows, o `import crewai` (1.15.5) puxa `chromadb` (que chama `Path.home()`) e `crewai_core` (telemetria, que chama `Path(LOCALAPPDATA)`). Se o Daphne/processo for lançado via subprocess com env MÍNIMO (sem `USERPROFILE`/`HOME`/`LOCALAPPDATA`/`APPDATA`/`TEMP`), o import quebra com:
- `RuntimeError: Could not determine home directory` (chromadb → `Path.home()`)
- `TypeError: ... not 'NoneType'` (crewai_core → `Path(LOCALAPPDATA)`)

**Diagnóstico:** `python -c "import crewai"` com o MESMO env do processo. Se falhar, é isto.

**Correção:** relançar o Daphne/processo com o ambiente Windows completo (`USERPROFILE`, `HOME`, `HOMEDRIVE`, `HOMEPATH`, `LOCALAPPDATA`, `APPDATA`, `TEMP`, `TMP`). Quando o backend é iniciado pelo terminal normal do usuário essas vars existem — este bug aparece só quando o agente relança o server via `subprocess.Popen` com `env={...}` parcial. Testar com `python -c "import crewai"` no env final antes de subir.

**SEMPRE diagnosticar execução de crew "silenciosa" via ExecutionLog**

> Para o mesmo padrão em **skills longas síncronas** (ex: `create_presentation` gerando carrossel com imagens) que "somem" do chat — tool_call sem tool_result, task presa em `running`, artefatos criados mas resposta não persistida — ver `references/skill-longa-sse-nao-persistida.md`.

Quando o usuário reporta "pedi para acionar a crew mas nada aconteceu"

```python
from chat.models import ExecutionLog
for l in ExecutionLog.objects.filter(task_id=<id>).order_by('id'):
    print(f'[{l.action_type}] tool={l.tool_name} payload={l.payload}')
```

**Padrão revelador:** um `tool_call` de `execute_crew` **sem** `tool_result` correspondente = a task async `run_crew` quebrou em background e o erro foi engolido. O `execute_crew` retorna `{status: "dispatched"}` imediatamente (o dispatch é síncrono), mas o `run_crew` roda numa **thread separada** via `enqueue_task_sync` — se ele lançar exceção, o erro só vai pro log, NUNCA pro chat. O usuário vê "crew acionada" mas nada roda.

**Causa raiz mais comum (pós-migração Celery→asyncio):** o `crews/tasks_async.py` chama funções com **assinaturas erradas** que não foram atualizadas na migração. Sintomas de `TypeError`:
- `build_tools() takes from 1 to 2 positional arguments but 4 were given` → o `tasks_async.py` chamava `build_tools(crew, members, tasks, inputs)`, mas a assinatura é `build_tools(crew, allow_ask=True)`. Correção: `build_tools(crew)`.
- `extract_integration_nodes() takes 1 positional argument but 3 were given` → o `tasks_async.py` chamava `extract_integration_nodes(crew, tasks, inputs)`, mas a assinatura é `extract_integration_nodes(graph)`. Correção: `extract_integration_nodes(crew.graph or {})`.

**Como confirmar o fix:** rodar `dispatch_run(crew, {...})` num shell. Se antes falhava em segundos com `TypeError` e agora demora (roda o pipeline de verdade), o bug de assinatura foi corrigido. Se o shell der timeout, é sinal de que a crew está executando de verdade (bom sinal).

**SEMPRE verificar assinaturas de funções chamadas em tasks async após migração** — a migração Celery→asyncio (`tasks.py` → `tasks_async.py`) pode copiar chamadas com argumentos posicionais que não batem com a assinatura atual da função. Ao ver `TypeError: X() takes N positional arguments but M were given` numa task async, confira a assinatura real da função (`def build_tools(crew, allow_ask=True)`) e ajuste a chamada — não assuma que os argumentos extras são válidos.

**SEMPRE rodar `run_crew` em thread separada, NUNCA inline no `except RuntimeError` do `enqueue_task_sync`** — quando o `execute_crew` roda dentro do engine AG-UI (via `sync_to_async` numa thread pool), o `enqueue_task_sync` cai no `except RuntimeError` (sem event loop na thread pool). Se ele executar `asyncio.run(result)` **inline**, a crew completa (7 tasks, com LLM) roda DENTRO do request, travando o stream SSE do `POST /chat/agui/` até o Daphne matar a conexão. Sintoma no log: `Application instance ... took too long to shut down and was killed` para o POST `/api/v1/chat/agui/`.

**Correção em `config/task_proxy.py`** — no `except RuntimeError`, especializar por nome de task:
- **`run_crew`** (task longa) → roda numa **daemon thread** com seu próprio `asyncio.run()`. NUNCA inline.
- **Tasks rápidas** (`index_document`, `generate_title`, etc.) → continuam inline, porque os testes de knowledge/chat dependem de a task persistir ANTES do request/teste retornar (em `TransactionTestCase` o banco é limpo antes de uma thread terminar).

```python
except RuntimeError:
    if name == "run_crew":
        import threading
        _tid = str(uuid.uuid4())
        def _run():
            try:
                result = coro_factory(*args, **kwargs)
                if hasattr(result, '__await__'):
                    asyncio.run(result)
            except Exception as exc:
                logger.error("Task '%s' [%s] falhou na thread: %s", name, _tid, exc)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return _tid
    # Tasks rápidas: inline (persiste antes do retorno).
    try:
        result = coro_factory(*args, **kwargs)
        if hasattr(result, '__await__'):
            return asyncio.run(result)
        return result
    except Exception as exc:
        logger.error("Task '%s' falhou inline: %s", name, exc)
        return str(uuid.uuid4())
```

**Pitfall de teste:** se você trocar TODAS as tasks para thread separada, os testes de knowledge (`test_e2e_ct_005.py`) quebram com `ProductContext matching query does not exist` — a thread roda depois que o `TransactionTestCase` limpa o banco. Por isso o `run_crew` é a ÚNICA task que deve ir para thread; as demais ficam inline.

**NÃO parar no `run_crew` ao listar tasks longas — incluir os callbacks de aprovação/rejeição.** Quando o usuário clica em "Aprovar entrega"/"Rejeitar", o front faz `POST /chat/agui/resume/` e chama `enqueue_task_sync("on_crew_run_approved_callback" | "on_crew_run_rejected_callback", ...)`. Se esses callbacks rodarem **inline** no `except RuntimeError` (como `run_crew` fazia originalmente), eles executam Composio + criação de página DENTRO do request — o `_apply_decision` fica pendurado, o endpoint nunca retorna headers, e o `res.text()` do front fica "processando" para sempre (botão com spinner). Correção em `config/task_proxy.py`: incluir `on_crew_run_approved_callback` e `on_crew_run_rejected_callback` no mesmo branch de thread separada que `run_crew`. Receita completa em `references/agui-chat-crew-run-approval.md`.

**SEMPRE isolar ORM síncrono em contexto async ao mover callbacks para thread.** Ao mover `on_crew_run_approved_callback` para uma thread com seu próprio `asyncio.run()`, aparecem bugs latentes de `SynchronousOnlyOperation` que antes eram mascarados (o callback nem rodava inline). Em `crews/callbacks_async.py`, o `_create_page_from_run` fazia ORM síncrono direto (`_final_task_output(run)`, `run.crew.custom_name`, `run.created_at`) em contexto async. Correção: extrair um helper síncrono `_read_final_meta(run, _final_task_output)` que retorna `(final_link, crew_name, created_at, org_id)` e chamá-lo via `sync_to_async`; usar `organization_id`/`uuid` (não `run.organization` nem `pk`) em todos os acessos.

**SEMPRE usar `lookup_field` do ViewSet ao chamar action via `asyncio.run_coroutine_threadsafe`/`sync_to_async`.** O `_create_page_from_run` chamava `PageViewSet.publish(request, pk=str(page.id))`, mas o `PageViewSet` tem `lookup_field = "uuid"` — erro `PageViewSet.publish() got an unexpected keyword argument 'pk'`. Correção: `publish(request, uuid=str(page.uuid))`. Ao invocar um action de ViewSet manualmente, confira sempre o `lookup_field` (default `pk`, mas pode ser `uuid`).

**SEMPRE gerar `slug` ao criar `Page` no callback de aprovação.** O modelo `Page` tem `unique_together = [("organization", "slug")]` e `slug = SlugField()` SEM default/auto-generation. Se o `_create_page_from_run` criar a Page com `title`/`html_content` mas sem `slug`, o primeiro run passa (slug vazio ok) mas o SEGUNDO run falha com `duplicate key value violates unique constraint "pages_page_organization_id_slug_30ccfd5f_uniq"` (Key (organization_id, slug)=(1, )). O callback ainda completa (page=nenhuma), mas gera erro no log. Correção: gerar slug a partir do título via `from django.utils.text import slugify; base_slug = slugify(page_title) or "entrega"` e passar `slug=base_slug` no `Page.objects.create`. Ao criar qualquer registro com `unique_together`, verifique se todos os campos não-default da constraint são preenchidos.

### DRF — SEMPRE verificar `@action` decorator em ViewSet methods

Quando um método em um ViewSet não tem o decorator `@action(detail=True/False, methods=[...])`, o DRF **não expõe a rota** — o frontend recebe 404. Sintoma: o método existe no código, a lógica está correta, mas a URL retorna "Não encontrado".

**Causa raiz comum:** o método foi adicionado sem o decorator, ou o decorator foi perdido durante um find-and-replace que corrompeu a estrutura do arquivo.

**Correção:** adicionar o decorator apropriado:
```python
from rest_framework.decorators import action

@action(detail=True, methods=["get"])  # para operações em um objeto específico
def download(self, request, **kwargs):
    ...

@action(detail=False, methods=["get"])  # para operações na coleção
def favorites(self, request):
    ...
```

**Verificação:** após adicionar o decorator, testar a URL diretamente via API (curl/requests) antes de testar no frontend.

### SEMPRE verificar a estrutura do arquivo após find-and-replace de blocos grandes

Quando você usa `content.replace(old, new)` para substituir um bloco grande (ex: uma função inteira), o texto de ancoragem pode não ser único o suficiente, e o bloco pode cair DENTRO de outra função ou entre funções, corrompendo a estrutura do arquivo.

**Sintomas:**
- O arquivo compila (`compile()` passa) mas a lógica fica quebrada
- Uma função aparece "dividida" em duas partes (cabeçalho + corpo separados por outra função)
- O decorator de uma função some e o corpo vira código solto

**Prevenção:**
1. Usar âncoras com **pelo menos 3 linhas de contexto** acima e abaixo do bloco alvo
2. Após a substituição, verificar visualmente as 10 linhas antes e depois do local da substituição
3. Verificar que funções adjacentes não foram afetadas (decorators, docstrings, indentação)
4. Se o arquivo ficar corrompido, **reescrever o arquivo inteiro** em vez de tentar mais patches

**Exemplo de corrupção (aconteceu em `knowledge/views.py`):**
```python
# ANTES da substituição — estrutura correta:
@action(detail=True, methods=["get"])
def download(self, request, **kwargs):
    """Download de pasta como ZIP."""
    import io, zipfile
    ...  # corpo completo

@action(detail=False, methods=["get"])
def favorites(self, request):
    ...

# DEPOIS da substituição — estrutura corrompida:
def download(self, request, **kwargs):  # ← @action perdido
    """Download de pasta como ZIP."""
    import io, zipfile
@action(detail=False, methods=["get"])  # ← favorites entrou no meio do download
def favorites(self, request):
    ...

        folder = KnowledgeFolder.objects.filter(...)  # ← corpo do download solto
        ...
```

## Padrões de Bugs no Frontend React

> **Menu lateral colapsável + sistema de ícones `data-icon`** (crewbotics-front): CSS não esconde text nodes — envolver labels de nav em `<span>`; ícones via `[data-icon]::before` com `-webkit-mask: var(--i)`. Padrão completo em `references/collapsible-sidebar-data-icon.md`.

### Mensagem vai para conversa nova ao invés da atual (AG-UI / @ag-ui/client)

Quando o usuário reporta "digitei na conversa X mas a mensagem foi para uma conversa nova", a causa raiz é que o `HttpAgent` foi criado **sem** o interceptor `runAgent` que garante que `agent.threadId` esteja setado antes de enviar a mensagem.

**Fluxo quebrado:**
1. Usuário clica em conversa → `switchToThread` é chamado
2. Usuário digita e envia → `HttpAgent.runAgent()` é chamado
3. O interceptor (se existir) tenta decidir qual `threadId` usar
4. Se o interceptor usa `ctrl.activeId` (React state) ou `base.threadId` (UUID aleatório do construtor), o backend recebe um UUID errado e **cria uma conversa nova**
5. Mensagem vai para a conversa nova, a antiga fica vazia

### Mensagem desaparece ao enviar nova mensagem (sendPrompt + switchToThread)

Quando o usuário reporta "a resposta do assistente sumiu depois que enviei outra mensagem", a causa raiz é que o `sendPrompt` chama `runtime.threads.switchToThread(activeId)` **antes** de fazer `append()`. O `switchToThread` do runtime chama `core.applyExternalMessages([])` que **limpa todas as mensagens atuais** — incluindo respostas parciais do assistente que ainda estão sendo streamadas. Depois ele re-fetch o histórico do backend, mas a resposta parcial **ainda não foi salva** no banco, então ela simplesmente desaparece.

**Sintoma:** Usuário envia mensagem enquanto o assistente está respondendo → resposta parcial some. Ou: usuário envia segunda mensagem → a primeira resposta desaparece.

**Correção:** Não chamar `switchToThread` quando o usuário já está na thread ativa. O interceptor `runAgent` já garante que `agent.threadId` está correto via `activeIdRef.current`:

```tsx
// ERRADO — switchToThread limpa mensagens atuais:
const sendPrompt = useCallback(async (prompt: string) => {
  if (activeId) {
    await runtime.threads.switchToThread(activeId);  // ← limpa mensagens!
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  }
}, [...]);

// CERTO — só faz append, sem switchToThread:
const sendPrompt = useCallback(async (prompt: string) => {
  if (activeId) {
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  } else {
    const conv = await chatApi.createSession();
    await adapter.onSwitchToThread(conv.uuid);
    runtime?.thread?.append?.({ role: "user", content: [{ type: "text", text: prompt }] });
  }
}, [...]);
```

**NÃO fazer:** chamar `switchToThread` dentro de `sendPrompt` quando `activeId` já está setado. O interceptor `runAgent` já injeta o `threadId` correto nos params.

### Botão "Nova conversa" não limpa área de mensagens

Quando o usuário clica em "Nova conversa" e a sidebar atualiza mas o `chat__msgs` continua mostrando a conversa anterior, a causa raiz é que o `onClick` chama apenas `adapter.onSwitchToNewThread()`, que cria a conversa no backend e atualiza a sidebar, mas **não limpa as mensagens atuais** no runtime.

**Correção:** Usar `runtime.threads.switchToNewThread` quando disponível — ele chama `core.applyExternalMessages([])` + `core.resetState()` para mostrar o estado vazio (`ThreadPrimitive.Empty`):

```tsx
// ERRADO — só atualiza sidebar, não limpa mensagens:
<button onClick={() => adapter.onSwitchToNewThread()}>

// CERTO — prefere runtime quando disponível:
<button onClick={() => {
  if (runtime?.threads?.switchToNewThread) {
    runtime.threads.switchToNewThread();
  } else {
    adapter.onSwitchToNewThread();
  }
}}>
**NÃO fazer:** chamar `runtime.threads.switchToThread(uuid)` — ele chama o adapter internamente E faz um segundo fetch. Chamar o adapter diretamente é a abordagem correta, desde que o adapter sette `agent.threadId` antes do fetch.

### Conversa auto-selecionada no boot não carrega mensagens

Quando o usuário entra em `/chat` e a conversa mais recente está marcada como ativa na sidebar mas o `chat__msgs` mostra o estado vazio, a causa raiz é que o `ThreadListProvider` auto-seleciona a conversa (seta `activeId` + `threadIdRef`) mas **não chama** `onSwitchToThread` porque o runtime ainda não existe. O `ChatReady` cria o runtime depois, mas não há mecanismo para carregar as mensagens da conversa auto-selecionada. Correção em 2 partes (provider + ChatReady), usando `bootReady` state + `runtimeRef`, sem `runtime` na deps (loop infinito). Ver seção abaixo "SEMPRE usar `runtimeRef`".

O hook `useAgUiRuntime` retorna um objeto NOVO a cada render. Se você colocar `runtime` nas dependências de um `useEffect`, ele dispara em loop infinito: effect → switchToThread → setState → re-render → novo runtime → effect → ... Use `runtimeRef` (ref) para acessar o runtime dentro do effect:

```tsx
// ERRADO — runtime muda a cada render, loop infinito:
const runtime = useAgUiRuntime({...});
useEffect(() => {
  runtime.threads.switchToThread(id);
}, [runtime]);  // ← loop infinito

// CERTO — runtimeRef é estável:
const runtimeRef = useRef(runtime);
runtimeRef.current = runtime;
useEffect(() => {
  const r = runtimeRef.current;
  r?.threads?.switchToThread(id);
}, [controller.bootReady]);  // ← sem runtime na deps
```

### SEMPRE adicionar `console.debug` no interceptor `runAgent`

Quando o bug de thread switching acontece, não há log no console para diagnosticar qual threadId foi usado. Adicione `console.debug("[runAgent]", ...)` em cada branch do interceptor (pending, activeId, fallback, new session):

```tsx
console.debug("[runAgent] using activeId:", activeId);
console.debug("[runAgent] fallback to mostRecent:", mostRecent.uuid);
console.debug("[runAgent] created new session:", conv.uuid);
```

### SEMPRE expor `window.__chatDebug` para debug remoto

Após criar o HttpAgent e o controller, exponha o estado do chat no console do browser:

```tsx
if (typeof window !== "undefined") {
  (window as any).__chatDebug = {
    agent,
    controller,
    get activeId() { return controller.activeId; },
    get agentThreadId() { return agent?.threadId; },
    get conversations() { return controller.conversations; },
  };
}
```

Isso permite que o usuário digite `__chatDebug` no console do DevTools para inspecionar o estado atual do chat.

**Causa raiz — DUAS armadilhas:**

1. **`ctrl.activeId` é React state, stale no closure.** O interceptor `base.runAgent = async function(...) { ... ctrl.activeId ... }` captura o valor de `activeId` no momento da criação do `HttpAgent` (que é criado uma vez, via `if (!agentRef.current)`). O React state `activeId` muda depois, mas o closure ainda vê o valor inicial (null).

2. **`base.threadId` NÃO é setado pelo runtime.** O construtor do `HttpAgent` gera um UUID aleatório para `this.threadId`. O runtime do AG-UI **não** seta `agent.threadId` quando troca de thread — ele só chama o adapter. Usar `base.threadId` como fallback é pior que não ter interceptor: o valor é sempre truthy (um UUID fake), então o interceptor passa um UUID inexistente para o backend, que cria uma conversa nova silenciosamente.

**Correção em 3 partes (2 arquivos):**

**1. `useConversationThreadList.tsx` — adapter `onSwitchToThread` seta `agent.threadId` ANTES do fetch:**

```tsx
onSwitchToThread: async (threadId: string) => {
  threadIdRef.current = threadId;
  // Seta agent.threadId ANTES de fazer o fetch — o HttpAgent usa
  // this.threadId no prepareRunAgentInput. Sem isso, o interceptor
  // runAgent ve o UUID gerado no construtor (conversa nova) em vez
  // do UUID da conversa que o usuario clicou.
  const agent = agentRef.current;
  if (agent) agent.threadId = threadId;
  setActiveId(threadId);
  const conv = await chatApi.getSession(threadId);
  // ... process messages ...
  return { messages };
},
```

**2. `useConversationThreadList.tsx` — expor `activeIdRef` no context:**

```tsx
// No tipo ThreadListController:
activeIdRef: React.MutableRefObject<string | null>;

// No provider:
value={{ adapter, conversations, activeId, activeIdRef, refresh, pendingThreadIdRef, agentRef }}
```

**3. `AguiChatPage.tsx` — interceptor `runAgent` usa `activeIdRef.current` (ref, não state):**

```tsx
const origRunAgent = base.runAgent.bind(base);
base.runAgent = async function (params: any, subscriber: any) {
  const ctrl = controller;
  const pendingId = ctrl.pendingThreadIdRef.current;
  if (pendingId) {
    ctrl.pendingThreadIdRef.current = null;
    base.threadId = pendingId;
    params = { ...params, threadId: pendingId };
    return origRunAgent(params, subscriber);
  }
  // Usa activeIdRef.current (ref, nao state) para evitar stale closure.
  // O adapter onSwitchToThread ja setou agent.threadId antes do fetch,
  // mas o interceptor pode ser chamado com params.threadId=null se o
  // runtime foi recriado (useAgUiRuntime retorna objeto novo a cada render).
  const activeId = ctrl.activeIdRef?.current;
  if (activeId) {
    base.threadId = activeId;
    params = { ...params, threadId: activeId };
    return origRunAgent(params, subscriber);
  }
  // Fallback: sem threadId ativo, cria ou pega a mais recente
  const conversations = ctrl.conversations;
  const mostRecent = conversations && conversations.length > 0 ? conversations[0] : null;
  if (mostRecent) {
    await ctrl.adapter.onSwitchToThread!(mostRecent.uuid);
    await ctrl.refresh();
    base.threadId = mostRecent.uuid;
  } else {
    const conv = await chatApi.createSession();
    await ctrl.adapter.onSwitchToThread!(conv.uuid);
    await ctrl.refresh();
    base.threadId = conv.uuid;
  }
  params = { ...params, threadId: base.threadId };
  return origRunAgent(params, subscriber);
};
```

**SEMPRE verificar se o `HttpAgent` tem o interceptor `runAgent`** — quando o `ChatReady` cria o agent diretamente (sem usar `AguiRuntimeProvider`), o interceptor que sincroniza `threadId` está faltando. O sintoma é mensagens indo para conversas novas.

**NÃO fazer:**
- Usar `ctrl.activeId` dentro do interceptor `runAgent` — é React state, o closure captura o valor inicial.
- Usar `base.threadId` como fallback — o construtor do `HttpAgent` gera um UUID aleatório, sempre truthy, que o backend interpreta como conversa nova.
- Assumir que o runtime seta `agent.threadId` ao trocar de thread — ele NÃO seta, só chama o adapter.

### Duplicate API call ao clicar em conversa do chat (AG-UI / @ag-ui/client)

> **"Chat indisponível" no upload de anexo** (ErrorBoundary capturando `throw` do `send` de attachments sem conversa ativa; backend OK) → ver `references/agui-chat-upload-attachment-errorboundary.md`.

> **Referência completa:** `references/agui-chat-thread-switching.md` — contém o guia de debugging completo com todas as variações do problema, código de backend e frontend, e a configuração que funciona.

Quando o usuário reporta "duas chamadas ao endpoint GET /conversations/{uuid}/" ao clicar em uma conversa, a causa raiz é que o `@ag-ui/client` HttpAgent tem um **setter** em `agent.threadId` que dispara um fetch **sempre que o valor muda**. O fluxo problemático:

1. `handleClick(uuid)` → `setActiveId(uuid)`
2. `useEffect` detecta `activeId` mudou → chama `runtime.threads.switchToThread(uuid)`
3. `switchToThread` chama o adapter `onSwitchToThread(uuid)` → **fetch #1**
4. `switchToThread` setta `agent.threadId = uuid` → **fetch #2** (HttpAgent detecta mudança)

**Correção definitiva:** o adapter deve settar `agent.threadId` **antes** de fazer o fetch. Quando o runtime tentar settar `agent.threadId` depois, o HttpAgent vê que é o **mesmo valor** e não re-fetch.

```tsx
// No adapter (useConversationThreadList.tsx):
onSwitchToThread: async (threadId: string) => {
  threadIdRef.current = threadId;
  // Seta agent.threadId ANTES de fazer o fetch, para que quando
  // o runtime settar agent.threadId depois, o HttpAgent veja o
  // mesmo valor e NAO faca um segundo fetch.
  const agent = agentRef.current;
  if (agent) agent.threadId = threadId;
  setActiveId(threadId);
  const conv = await chatApi.getSession(threadId);
  // ... process messages ...
  return { messages };
},
```

**Requisitos para funcionar:**
1. O `AguiRuntimeProvider` deve expor o `agent` via `controller.agentRef.current = agent` (após o `useMemo` que cria o agent)
2. O `ThreadListController` deve ter `agentRef: React.MutableRefObject<{ threadId: string | null } | null>`
3. O `handleClick` deve chamar **apenas** `adapter.onSwitchToThread(uuid)` — sem `runtime.threads.switchToThread`
4. O `useEffect` que sincroniza `activeId` com `agent.threadId` deve ser **removido** — o adapter já settou `agent.threadId` antes de `setActiveId`

**NÃO fazer:** chamar `runtime.threads.switchToThread(uuid)` — ele chama o adapter internamente E faz um segundo fetch. Chamar o adapter diretamente é a abordagem correta, desde que o adapter sette `agent.threadId` antes do fetch.

### Generative UI component nao renderiza no chat (CrewToolFallback)

Quando o usuário reporta "pedi para criar uma apresentação mas o card não apareceu no chat", a causa raiz é que o `CrewToolFallback` (em `CrewRunCard.tsx`) só detecta dispatches de crew (`run_id` + `status === "dispatched"`). Skills que retornam componentes Generative UI (como `PresentationCard`, `PlaybookCard`, etc.) passam batido — o fallback retorna `null` e o card nunca aparece.

**Sintoma no Network:** a chamada REST ao backend retorna 200 com o JSON contendo `{ "component": "PresentationCard", "props": {...} }`, mas o chat não renderiza nada.

**Correção em 2 passos:**

1. **`CrewRunCard.tsx`** — `CrewToolFallback` deve detectar `component` no resultado e renderizar o componente correspondente do `UI_REGISTRY`:
```tsx
import { UI_REGISTRY } from "@/components/generative-ui/registry";

export function CrewToolFallback({ result }: { result?: unknown }) {
  const r = result as Record<string, unknown>;
  // Generative UI component (PresentationCard, etc.)
  if (r && typeof r === "object" && "component" in r && typeof r.component === "string") {
    const Component = UI_REGISTRY[r.component];
    if (Component) {
      return <Component {...(r.props as Record<string, unknown>)} />;
    }
  }
  // Crew dispatch (existing logic)
  const isCrewDispatch = !!r && typeof r === "object" && "run_id" in r && r.status === "dispatched";
  if (!isCrewDispatch) return null;
  return <CrewCard result={r as CrewResult} />;
}
```

2. **`registry.tsx`** — `UI_REGISTRY` deve ser `export const`, não apenas `const`. Sem o export, o import no `CrewRunCard.tsx` falha com `Missing export`.

**NÃO fazer:** assumir que todo resultado de tool call é um dispatch de crew. Skills do Copilot podem retornar qualquer componente do `UI_REGISTRY`.

### ViewSet action ausente em modelo relacionado

Quando uma feature funciona para um modelo (ex: favoritar documentos) mas não para um modelo relacionado (ex: favoritar pastas), a causa raiz mais comum é que o `@action` decorator existe em um ViewSet mas não no outro. Sintoma: o frontend chama `/knowledge/docs/favorites/` e recebe dados, mas `/knowledge/folders/favorites/` retorna 404.

**Correção em 5 passos:**
1. Verificar se o action existe no ViewSet do modelo faltante
2. Adicionar o action seguindo o mesmo padrão do ViewSet que já funciona
3. Adicionar o endpoint correspondente no frontend (`endpoints.ts`)
4. Adicionar o hook React Query
5. Atualizar o componente que renderiza a lista para incluir os dados do novo endpoint

Este padrão é comum em pares Folder/Document, Pai/Filho, ou qualquer relação 1:N onde um ViewSet foi implementado primeiro e o outro ficou para trás.

Ver `references/padroes-bugs-chat-presentacoes.md` para título automático (is_new vs conv existente), SVG browser-vs-PPTX, e download autenticado via blob.

Ver `references/debug-running-process-drf-serializer-pitfalls.md` para: traceback de lib que o disco já não usa = processo antigo em memória (reiniciar servidor, não editar código); `@action` DRF com `url_path` (underscore vs hífen); adicionar campo ao serializer quebra teste de key-set; campo novo exige migration + `--create-db`.

Ver `references/playwright-windows-asyncio-loop.md` para export PNG: se falhar com `NotImplementedError` em `_make_subprocess_transport`, o event loop é Selector (não suporta subprocess) — forçar `WindowsProactorEventLoopPolicy` antes de `asyncio.run()`. Não confundir com "Executable doesn't exist" (browser não instalado → `python -m playwright install chromium`). **Para produção (ECS Linux/container) não usar Playwright/Chromium — preferir `resvg-py` (SVG→PNG em Rust, sem browser/lib nativa); a referência documenta por quê e como (import `resvg_py`, `svg_to_bytes(svg_string=<str>, width, height)`).**

**Preferir `resvg-py` em vez de Playwright/Chromium para SVG→PNG** — quando o export PNG de slides/carrossel não precisa de browser (o SVG já existe via `svg_renderer`), use `resvg-py` (wheel Rust, sem lib nativa, funciona no Windows e ECS Linux, sem baixar Chromium). `channel="chrome"`/`"msedge"` NÃO funciona em produção (container Linux sem browser). Ver `references/svg-to-png-resvg.md` para API (`resvg_py.svg_to_bytes`, `svg_string` aceita str não bytes) e pitfalls.

**Para export PNG de slides/carrosséis em produção (ECS Linux) ou quando o download do Chromium falha, NÃO use Playwright** — use `resvg-py` (SVG→PNG puro Rust, sem browser, sem lib nativa, funciona em Windows e Linux). O projeto já gera o SVG 1080×1350 via `svg_renderer.py`; basta convertê-lo. `cairosvg` e `svglib`+`reportlab` falham por exigirem libcairo nativa. Detalhes e API quirks em `references/svg-to-png-resvg-alternative.md`.

## Quality Gates, Handoff Templates e Dev→QA Loop (Fase 2 do Agency Plan)

Quando o pipeline NEXUS exige validação de qualidade entre tasks, implemente:

### Modelo
Adicione campos ao `CrewTemplateTask` (e `CrewInstanceTask`):
```python
quality_gate = models.BooleanField(default=False)       # True = task validadora
max_retries = models.PositiveIntegerField(default=3)     # tentativas antes de escalation
handoff_template = models.TextField(blank=True, default="")  # formato padrao de output
```

### Lógica no crew_runner.py
No `_build_and_run()`, após o kickoff, itere as tasks ordenadas. Para cada task com `quality_gate=True`, leia o output e verifique se começa com `PASS`, `WARN` ou `FAIL`:
- **PASS** → loga e segue
- **WARN** → loga aviso e segue
- **FAIL** → reexecuta a task anterior (do `context`) até `max_retries`. Se exceder, gera chave `_escalation_<task_key>` no output dict.

```python
for t in ordered_tasks:
    if not getattr(t, 'quality_gate', False):
        continue
    gate_output = out.get(t.task_key, "")
    gate_result = gate_output.strip().upper()
    if gate_result.startswith("FAIL"):
        for ctx_key in (t.context or []):
            if ctx_key in out:
                for attempt in range(1, t.max_retries + 1):
                    out[ctx_key] = f"[QUALITY GATE FAIL - tentativa {attempt}/{t.max_retries}]..."
                    if attempt >= t.max_retries:
                        out[f"_escalation_{t.task_key}"] = "ESCALATION: ..."
    elif gate_result.startswith("WARN"):
        logger.info(...)
    elif gate_result.startswith("PASS"):
        logger.info(...)
```

### Handoff template
Injete o `handoff_template` na `description` da task durante a criação:
```python
if getattr(t, 'handoff_template', None):
    desc = f"{desc}\n\n=== FORMATO DE SAÍDA (HANDOFF) ===\n{t.handoff_template}"
```

### Seed
Atualize a função de seed para incluir os novos campos:
```python
CrewTemplateTask.objects.create(
    ...,
    quality_gate=t.get("quality_gate", False),
    max_retries=t.get("max_retries", 3),
    handoff_template=t.get("handoff_template", ""),
)
```

### SEMPRE verificar divergência sync/async ao migrar features de runner

Quando uma feature (ex.: quality gate) existe no runner SÍNCRONO (`crew_runner.py` → `run_pipeline`) mas o caminho REAL de execução é o ASYNC (`crew_runner_async.py` → `run_pipeline_async`, usado por `run_crew` em `tasks_async.py`), a feature pode ter sido **silenciosamente perdida** na migração. O `run_crew_sync` usa o sync (com a feature), mas o `run_crew` async (o que roda de verdade) usa o async (sem a feature). Sintoma: o FAIL da crew é entregue como resultado final sem retry/escalation.

**Correção:** ao corrigir um bug de pipeline, verifique AMBOS os runners (`crew_runner.py` e `crew_runner_async.py`) e porte a lógica para os dois. Não assuma que o async espelha o sync.

### SEMPRE verificar que TODAS as funções que COPIAM tasks copiam os campos do quality gate

`hire_crew` (em `crews/services.py`) e `CpCrewSkill.execute` (em `chat/skills/cp_base_skill.py`) copiam tasks do template para a instância. Se não copiarem `quality_gate`, `max_retries`, `handoff_template`, as tasks copiadas ficam com `quality_gate=False` (default) — e o quality gate **nunca dispara**, mesmo com o runner corrigido. Sintoma: a crew se auto-avalia com FAIL e o retry/escalation não acontece. Correção: adicionar os 3 campos ao `CrewInstanceTask.objects.create/bulk_create` em TODAS as funções de cópia (não só na principal).

### SEMPRE definir `on_task_done` como SÍNCRONO mas NUNCA salvar ORM síncrono direto

O callback de progresso do CrewAI (`_make_cb` → `on_task_done(task_key, text)`) é chamado **sem await** dentro do runner. Se você definir `on_task_done` como `async def`, ele nunca é executado (a corrotina é criada e descartada) — o progresso ao vivo não grava nada. Portanto a função DEVE ser síncrona (`def`).

**PORÉM:** esse callback síncrono roda DENTRO do event loop do `kickoff_async`. Chamar `out.save()` (ORM síncrono) diretamente ali levanta `django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context`. Sintoma: a crew roda mas o run vira `ERROR` com esse traceback e o card mostra "Erro na execução".

**Correção:** dentro do callback síncrono, agendar o save numa thread do executor via `asyncio.run_coroutine_threadsafe` + `sync_to_async`:
```python
def _on_task_done(task_key, text):
    link = link_by_key.get(task_key)
    if not link or not text:
        return
    try:
        import asyncio
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Sem loop (raro) — salva direto.
        out = link.output
        out.content = sanitize_output(text)
        out.execution_status = ExecutionStatus.DONE
        out.save(update_fields=["content", "execution_status"])
        return

    def _save_sync(link_, text_):
        out_ = link_.output
        out_.content = sanitize_output(text_)
        out_.execution_status = ExecutionStatus.DONE
        out_.save(update_fields=["content", "execution_status"])

    async def _save():
        await sync_to_async(_save_sync)(link, text)

    asyncio.run_coroutine_threadsafe(_save(), loop)
```
Não faça `out.save()` inline dentro do callback (que é síncrono mas roda no loop do async).

### SEMPRE reconstruir cards de crew run a partir do `runStatus` no frontend (AG-UI)

Quando o usuário reporta "o card de execução sumiu após refresh e só o texto apareceu", a causa é que o `toThreadMessage` (em `useConversationThreadList.tsx`) só convertia mensagens com `uiComponent` ou texto em tool-calls — mensagens com `runStatus` (criadas por `post_run_status_message`) eram renderizadas só como texto. Correção em 3 partes:
1. **Backend** (`chat/run_status.py`): adicionar `crewName` ao `runStatus` (`sig = {"runId": ..., "status": ..., "crewName": ...}`) para o front renderizar o card após refresh.
2. **Frontend** (`toThreadMessage`): converter mensagens com `runStatus` em tool-call `execute_crew` com `result = { run_id, crew_name, status: "dispatched", finalOutput }` — assim o `CrewToolFallback`/`CrewCard` reconstrói o card e a história da conversa é preservada.
3. **`CrewCard`**: exibir `finalOutput.content` quando `runStatus === "DONE"` (o resultado aparece no card, não só como texto) e renderizar barra de progresso + lista de tasks a partir do `taskOutputs` do polling em `/crew-runs/<id>/`.

### SEMPRE mockar o módulo `crewai` INTEIRO (incl. submodule `crewai.tools`) ao testar o runner async

O `run_pipeline_async` faz `from crewai import LLM, Agent, Crew, Process, Task` E `from crewai.tools import tool` DENTRO da função. Para testar o quality gate no async com outputs controlados (FAIL/PASS), instale um módulo `crewai` fake no `sys.modules` **e** o submodule `crewai.tools` (com `tool` decorator). Também mocke `crews.builtin_tools.build_builtin_tools` (importado de `.builtin_tools` dentro da função — NÃO é atributo de `crew_runner_async`, então o patch path é `crews.builtin_tools.build_builtin_tools`, não `crews.crew_runner_async.build_builtin_tools`). O runner cria as Tasks na ordem de `ordered_tasks` sem passar `task_key` ao construtor — use um contador global para mapear a ordem de criação ao output esperado.

### SEMPRE testar o card de crew run no BROWSER via loop E2E (chat AG-UI)

Quando o bug é no card de execução de crew no chat, não confie só em testes de backend nem no `bun run build` — rode o fluxo real no browser. Receita completa em `references/agui-chat-crew-run-card-e2e.md`. Fluxo:

1. **Login** em `http://localhost:8080/chat` (o usuário de teste; se não houver credenciais, criar um usuário novo — AGENTS.md §13).
2. **Acionar a crew** — digitar "acione o time de presenca digital" e enviar. O Copilot pede contexto.
3. **Fornecer o contexto** — profissão/instagram/serviços. A crew é disparada (`status: "dispatched"`).
4. **Verificar progresso real** — ler as bolhas via `Array.from(document.querySelectorAll('.msg__bubble')).map(b=>b.innerText).join('\n---\n')`. O card deve mostrar barra "X de N etapas" + lista das tasks, NÃO um ícone genérico.
5. **Aguardar a execução** — 7 tasks com LLM levam 1-3 min. Poll o console a cada ~15-30s (a execução é em thread separada, sem callback ao browser).
6. **Verificar resultado no card** — quando DONE, o card deve exibir `finalOutput.content` no próprio card + botões Aprovar/Rejeitar.
7. **Clicar em "Aprovar entrega"** — o botão NÃO deve ficar "processando" para sempre. Deve receber o stream do `POST /chat/agui/resume/` (RUN_STARTED → crew.decision → RUN_FINISHED) e voltar ao estado normal. Isto valida que `on_crew_run_approved_callback` roda em thread separada (não bloqueia o resume). Confirmar via console que o botão não fica `disabled` com spinner `animate-spin`.
8. **Refresh (F5)** — recarregar e verificar que o card CONTINUA visível com o resultado (história preservada). Isto valida o `toThreadMessage` reconstruindo o card a partir do `runStatus`.
9. **Conversa única** — via `window.__chatDebug` confirmar `convCount` e `activeId` (sem duplicatas).

**Testar o endpoint resume direto (curl/urllib) para isolar travamento de botão:** se o botão ficar "processando", o problema é quase sempre o endpoint `POST /api/v1/chat/agui/resume/` que não retorna headers (timeout). Testar com `urllib.request.urlopen(req, timeout=15)`:
- **Timeout/`TimeoutError`** → o `_apply_decision` (e o callback de aprovação inline) está bloqueando o request. Causa raiz = `enqueue_task_sync` rodando o callback inline.
- **200 em ~2s com stream SSE** → correto. O `res.text()` do front vai resolver e o botão para de processar.

**Reiniciar o Daphne após editar `config/task_proxy.py`/`callbacks_async.py`/`tasks_async.py`:** esses módulos são importados no boot do ASGI — o `manage.py runserver`/Daphne NÃO faz auto-reload dessas mudanças. Matar o processo que escuta a porta 8000 (`netstat -ano | findstr :8000` → PID → `taskkill /PID <pid> /F`) e relançar. **Pitfall de lançamento:** ao subir via `execute_code`/subprocess, o sandbox Hermes injeta o site-packages dele no `PYTHONPATH`, causando conflito `cffi`/`lxml`/`_overlapped` (daphne falha no boot). Correção: setar `PYTHONPATH` APENAS para `C:\...\.venv\Lib\site-packages` (sem o do Hermes) + `PATH` com `.venv\Scripts` na frente, e usar `python.exe -m daphne` (o `daphne.exe` launcher pode pegar o HOME errado). Testar com `python -c "import asyncio, daphne"` antes de lançar.

**Confirmar estado real da crew:** ler `window.__chatDebug.activeId` (uuid da conversa) e checar `convCount` — se >1, há duplicata (regressão do interceptor `runAgent`).

**Documentar como LOOP:** gravar o teste em `.hermes/docs/testes-de-loop/LOOP-<data>-<slug>.md` com critérios de aprovação + tabela de resultados por tentativa (padrão `cp-goal-loop`). Atualizar a linha da tentativa ao concluir.

**Pitfall:** o snapshot do browser (`browser_snapshot`) não mostra o texto das bolhas do chat — use `browser_console` com o selector `.msg__bubble` para ler o conteúdo real. O botão de enviar só habilita depois de digitar (snapshot pode mostrar `disabled` — re-snapshot antes de clicar).

**SEMPRE renderizar o markdown do `finalOutput.content` no `CrewCard`** — quando o usuário reporta \"o card mostra o resultado mas sem formatação (negritos/listas viram `**texto**` literal)\", a causa é que o `CrewCard` renderiza `finalContent` num `<div className=\"whitespace-pre-wrap\">` (texto plano). Correção: usar `ReactMarkdown` + `remarkGfm` (os mesmos já usados no `AguiChatPage`), com a classe `markdown-body` para herdar o estilo do chat:
```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
...
<div className="text-sm text-foreground markdown-body break-words">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalContent}</ReactMarkdown>
</div>
```
**Verificar no browser:** `document.querySelectorAll('.msg__bubble .markdown-body')` e contar `strong`/`li` no card da entrega (ex.: `strong=26 li=25` para um PASS longo) — confirma que negritos e listas viraram HTML, não texto literal. Isto é um critério de aprovação próprio do loop E2E do card.

## IntegrationLayer (Fase 3 do Agency Plan)

Quando precisar unificar múltiplos backends de integração (Composio, WhatsApp, Asset Library) sob uma única interface:

### Estrutura
```python
def resolve_provider_type(slug: str) -> str:
    # Retorna "composio", "whatsapp", "asset" ou "unknown"

def execute_action(organization, provider_slug, action, params, user=None) -> dict:
    # Retorna {status: "ok"|"error", data: ..., error: ...}
    # NUNCA levanta exceção — sempre retorna dict com status

def list_available_actions(organization) -> list[dict]:
    # Lista acoes de todos os providers conectados

def check_integration_status(organization, provider_slug=None) -> dict:
    # Status de um ou todos providers

def validate_required_integrations(organization, required_providers) -> dict:
    # Retorna {valid, missing: [{provider, type, message}], connected: [...]}
```

### Regras
- **NUNCA levantar exceção** — sempre retornar `{status: "error", error: "mensagem"}`
- **Import local** dentro de cada `_execute_*` para evitar circular imports
- **Stub automático** quando o backend real não está disponível (ex: baileys não instalado)
- **Rate limiting** mínimo de 3s entre mensagens WhatsApp

## Agentic UI Components (Fase 4 do Agency Plan)

Skills do Copilot que retornam componentes Generative UI seguem este padrão:

### Backend (skill)
```python
@register_skill
class SomeSkill(BaseSkill):
    name = "skill_name"
    category = "Categoria"
    icon = "🎯"
    description = "..."
    parameters = {"type": "object", "properties": {...}}
    
    def execute(self, **kwargs) -> dict:
        # Processa...
        return {
            "component": "ComponentName",  # nome exato no UI_REGISTRY
            "props": { ... },              # props do componente React
        }
```

### Frontend (componente)
Criar em `src/components/generative-ui/ComponentName.tsx`:
```tsx
import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const ComponentName = ({ prop1, prop2 }: { prop1: string; prop2?: number }) => {
  return (
    <Card className="my-2">
      <CardHeader><CardTitle>{prop1}</CardTitle></CardHeader>
      <CardContent>{/* ... */}</CardContent>
    </Card>
  );
};
```

Registrar em `registry.tsx`:
```tsx
import { ComponentName } from "./ComponentName";
const UI_REGISTRY = { ..., ComponentName };
```

### Componentes padrão da Agentic UI
| Componente | Props | Uso |
|-----------|-------|-----|
| `PlaybookCard` | name, description, category, icon, agentCount, taskCount, slug, onSelect | Sugestão de playbook |
| `PlaybookList` | playbooks[], total, onSelect | Lista de playbooks |
| `IntegrationStatus` | playbookName, integrations[], allConnected, onConnect | Status de integrações |
| `WhatsAppQRCode` | qrCode, sessionId, expiresAt, onScanned, onRefresh | QR Code WhatsApp |
| `AssetUploader` | onUpload, maxFiles, accept | Upload drag-and-drop |
| `CrewProgress` | crewName, runId, status, totalTasks, completedTasks | Barra de progresso |
| `DeliverableGallery` | crewName, deliverables[], total | Grid de entregáveis |
| `ProposalPreview` | title, pdfUrl, onDownload, onView | Preview de PDF |
| `MetricsDashboard` | title, metrics[], period | Grid 2x2 de métricas |

## Script

O script `scripts/run.py` monta e executa a crew automaticamente com agentes embutidos (self-contained — não depende de diretório externo). Ele:

1. Cria os agentes CrewAI com definições embutidas no próprio script
2. Cria as tasks sequenciais: Developer → QA → Evidence
3. Executa a crew e reporta o resultado

Para rodar manualmente:

```bash
python .hermes/skills/cp-bug-fix/scripts/run.py "descrição do bug aqui"
```

## Agentes utilizados

| Agente | Arquivo | Função |
|--------|---------|--------|
| Backend Architect | `engineering/engineering-backend-architect.md` | Developer (back-end) |
| Frontend Developer | `engineering/engineering-frontend-developer.md` | Developer (front-end) |
| API Tester | `testing/testing-api-tester.md` | QA — validação funcional |
| Test Automation Engineer | `testing/testing-test-automation-engineer.md` | QA — criação de testes automatizados |
| Evidence Collector | `testing/testing-evidence-collector.md` | Verificação final com evidências |
