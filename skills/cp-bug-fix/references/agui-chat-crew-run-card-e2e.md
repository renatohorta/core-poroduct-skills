# E2E Test of the Crew Run Card in Chat (AG-UI)

Browser test-loop recipe for the crew run card bug in chat
(BUG-20260807). Passes end-to-end in the local environment (backend :8000,
frontend :8080) and validates all criteria: real progress, result in the
card, history preserved after refresh, single conversation, quality gate.

## Prerequisites

- Backend and frontend running (check: `urllib` on `http://localhost:8000/api/`
  and `http://localhost:8080`).
- The bash terminal may be broken (WSL relay) — use `execute_code` (Python)
  for git/subprocess and `browser_*` for the UI. For files use Python
  (`open(p,'w',encoding='utf-8').write(...)`) — Hermes' `write_file`/`patch`
  fails on Windows when the bash relay is broken.

## Scenario (real bug conversation)

1. Log in at `http://localhost:8080/chat` (renato.horta@gmail.com / teste123).
2. Type and send: `acione o time de presenca digital`.
3. Copilot replies asking for context (profession, instagram, services).
4. Send: `eu quero criar uma academia de ia, onde ensino lideres de tecnologia
   a trabalhar com agentes de ia e criar automacoes de processos. meu perfil atual é novo`.
   - If Copilot has memory of the previous conversation (FAIL on the generic
     proposal), it asks for the specific services — provide the AI consulting list.
5. Crew fires. Wait 1-3 min (7 tasks with LLM, execution in a separate thread).

## Checks (via browser_console)

Read the chat bubbles (the snapshot does NOT show their text):
```js
Array.from(document.querySelectorAll('.msg__bubble')).map(b => b.innerText).join('\n---\n')
```

### Criterion 1 — real progress
During execution, the card must show:
```
Crew acionada: <nome>
Executando…
X de N etapas concluídas
Y%
🔎 Agent A
🎨 Agent B
...
```
(before the fix: only "Executando…" + generic image, without the task list).

### Criterion 2 — result in the card
When DONE, the card displays `finalOutput.content` in the card itself + buttons
"Aprovar entrega" / "Rejeitar". (before: the card asked for approval without
showing the result).

### Criterion 3 — refresh preserves history
Press F5. The most recent conversation must load and the card must REMAIN visible
with the result (rebuilt via `toThreadMessage` from the `runStatus`).

### Criterion 4 — single conversation
```js
window.__chatDebug ? JSON.stringify({activeId: window.__chatDebug.activeId, convCount: (window.__chatDebug.conversations||[]).length}) : "sem debug"
```
Expected: `convCount: 1` and `activeId` == the conversation thread.

### Criterion 5 — quality gate
If the crew self-evaluated, the card shows `PASS`/`FAIL`. With PASS, the gate passed.
With persistent FAIL, there should be retry/escalation (see `run_pipeline_async`).

### Criterion 6 — result markdown rendered
The `finalOutput.content` in the card must render markdown (bold, lists,
headings), not plain text with literal `**`/`*`. Verify by counting HTML
elements in the delivery card:
```js
(() => { const els = document.querySelectorAll('.msg__bubble .markdown-body');
  const res = []; els.forEach((c,i) => { const strong=c.querySelectorAll('strong').length;
  const li=c.querySelectorAll('li').length; res.push(i+': strong='+strong+' li='+li); });
  return res.join('\n'); })()
```
Delivery card expected with `strong>0` and `li>0` (e.g. `strong=26 li=25` for a
long PASS). Fix: `CrewRunCard.tsx` uses `ReactMarkdown` + `remarkGfm` with the
`markdown-body` class (before: `whitespace-pre-wrap` = plain text).

## Expected result (real loop attempt 1)

All criteria passed on the first try. The card showed "0 de 7 etapas" with the
list of the 7 tasks; ended with PASS (Reality Checker); after F5 the card remained
visible with the result and buttons; `convCount: 1`.

## Backend/frontend touched for the fix

- `crews/crew_runner_async.py` — quality gate (FAIL→retry→escalation) + handoff_template
- `crews/services.py` (hire_crew) and `chat/skills/cp_base_skill.py` — copy
  quality_gate/max_retries/handoff_template from the template tasks
- `crews/tasks_async.py` — synchronous `on_task_done` writes live progress
- `chat/run_status.py` — `crewName` in runStatus
- `useConversationThreadList.tsx` — `toThreadMessage` rebuilds the card from runStatus
- `CrewRunCard.tsx` — progress bar + final result in the card
- `src/lib/api/types.ts` — typed ChatMessage.runStatus

## Automated tests created

- `tests/crews/test_quality_gate_async.py` — quality gate in async (mock crewai)
- `tests/chat/test_run_status_message.py` — runStatus with crewName + finalOutput

## Loop documentation

`.hermes/docs/testes-de-loop/LOOP-<data>-crew-run-card.md` — template with
criteria + results table per attempt.
