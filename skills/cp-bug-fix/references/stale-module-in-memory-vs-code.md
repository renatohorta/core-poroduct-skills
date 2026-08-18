# Traceback de código DESATUALIZADO em memória (vs. código no disco)

Quando o usuário cola um traceback que referencia uma biblioteca/módulo que **já foi
removido ou trocado no código do disco**, a causa raiz provavelmente NÃO é o código —
é o processo do servidor (Daphne/runserver) rodando com os **módulos antigos carregados
em memória** desde antes do merge do fix.

## Caso real (10/08/2026)

Usuário reportou "ao clicar em download das PNGs do carrossel, o sistema dá erro":

```
NotImplementedError
  File ".../playwright/_impl/_transport.py", line 120, in connect
    self._proc = await asyncio.create_subprocess_exec(...)
  File ".../asyncio/base_events.py", line 528, in _make_subprocess_transport
    raise NotImplementedError
ERROR  Falha no export PNG do carrossel
```

O traceback aponta para Playwright (`playwright/_impl/_connection.py`). Mas o
`png_export.py` **no disco já usava `resvg-py`** (o fix Playwright→resvg tinha sido
mergeado dias antes). O Daphne em execução ainda tinha o módulo antigo com Playwright
na memória.

## Diagnóstico (NÃO re-fixar o código primeiro)

1. **Verificar o código real no disco** — `grep` por import real (`from playwright`,
   `async_playwright`, `p.chromium`, `sync_playwright`) no fluxo do bug. Se só aparecer
   em comentários/docstrings, o código já está correto.
   - Falso-positivo: o nome da lib em comentários (`# via Playwright`) NÃO é uso real.
2. **Testar o artefato diretamente no backend** — ex: `export_carousel_pngs(state, dir, n)`
   com o state real. Se gera PNGs sem erro, o fix já está válido e no disco.
3. **Verificar servidor ativo** — `netstat -ano | findstr :8000`. Se está rodando desde
   antes do merge do fix, **reinicie o Daphne** (matar PID da porta + relançar).
   Não toque no código.
4. **Registrar** o bug como `[Corrigido]` com a nota "o código já estava correto; o
   processo precisava ser reiniciado".

## Generalização para reidratação/persistência no frontend

O mesmo vale para bugs de persistência que "voltaram": se os fixes de reidratação
(`bootReady` + `runtimeRef` no `ChatReady`, `pendingThreadIdRef` no interceptor
`runAgent`, auto-título) JÁ estão no código, valide no browser antes de alterar qualquer
coisa:

1. Subir backend (Daphne :8000) + frontend (Vite :8080).
2. Login (criar usuário de teste se preciso — AGENTS.md §13).
3. Enviar mensagem → confirmar persistência no backend (`ChatMessage.objects.filter`).
4. Reload (F5) → verificar que a conversa é reidratada na sidebar + histórico no chat,
   sem duplicata (via `window.__chatDebug`: `convCount` deve ser 1).

Nesse caso (BUG-20260731 chat-conversa-nao-salva), o bug já estava corrigido pelos fixes
de reidratação; a validação no browser confirmou, sem editar código.
