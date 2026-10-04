# Traceback of OUTDATED code in memory (vs. code on disk)

When the user pastes a traceback that references a library/module that **has already been
removed or changed in the on-disk code**, the root cause is probably NOT the code —
it is the server process (Daphne/runserver) running with the **old modules loaded
in memory** since before the fix was merged.

## Real case (10/08/2026)

User reported "when clicking download of the carousel PNGs, the system gives an error":

```
NotImplementedError
  File ".../playwright/_impl/_transport.py", line 120, in connect
    self._proc = await asyncio.create_subprocess_exec(...)
  File ".../asyncio/base_events.py", line 528, in _make_subprocess_transport
    raise NotImplementedError
ERROR  Falha no export PNG do carrossel
```

The traceback points to Playwright (`playwright/_impl/_connection.py`). But the
`png_export.py` **on disk already used `resvg-py`** (the Playwright→resvg fix had been
merged days before). The running Daphne still had the old module with Playwright
in memory.

## Diagnosis (do NOT re-fix the code first)

1. **Check the real code on disk** — `grep` for a real import (`from playwright`,
   `async_playwright`, `p.chromium`, `sync_playwright`) in the bug flow. If it only appears
   in comments/docstrings, the code is already correct.
   - False positive: the lib name in comments (`# via Playwright`) is NOT real usage.
2. **Test the artifact directly in the backend** — e.g. `export_carousel_pngs(state, dir, n)`
   with the real state. If it generates PNGs without error, the fix is already valid and on disk.
3. **Check the active server** — `netstat -ano | findstr :8000`. If it has been running since
   before the fix was merged, **restart Daphne** (kill the PID on the port + relaunch).
   Do not touch the code.
4. **Record** the bug as `[Corrigido]` with the note "the code was already correct; the
   process needed to be restarted".

## Generalization to frontend rehydration/persistence

The same applies to persistence bugs that "came back": if the rehydration fixes
(`bootReady` + `runtimeRef` in `ChatReady`, `pendingThreadIdRef` in the `runAgent`
interceptor, auto-title) are ALREADY in the code, validate in the browser before changing
anything:

1. Start the backend (Daphne :8000) + frontend (Vite :8080).
2. Log in (create a test user if needed — AGENTS.md §13).
3. Send a message → confirm persistence in the backend (`ChatMessage.objects.filter`).
4. Reload (F5) → verify that the conversation is rehydrated in the sidebar + history in the chat,
   without a duplicate (via `window.__chatDebug`: `convCount` must be 1).

In that case (BUG-20260731 chat-conversa-nao-salva), the bug was already fixed by the
rehydration fixes; the browser validation confirmed it, without editing code.
