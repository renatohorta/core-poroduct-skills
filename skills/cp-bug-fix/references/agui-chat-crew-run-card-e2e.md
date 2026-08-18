# Teste E2E do Card de Execução de Crew no Chat (AG-UI)

Receita de loop de teste browser para o bug do card de crew run no chat
(BUG-20260807). Passa de ponta a ponta no ambiente local (backend :8000,
frontend :8080) e valida todos os critérios: progresso real, resultado no
card, história preservada após refresh, conversa única, quality gate.

## Pré-requisitos

- Backend e frontend rodando (verificar: `urllib` em `http://localhost:8000/api/`
  e `http://localhost:8080`).
- O terminal bash pode estar quebrado (WSL relay) — usar `execute_code` (Python)
  para git/subprocess e `browser_*` para a UI. Para arquivos usar Python
  (`open(p,'w',encoding='utf-8').write(...)`) — o `write_file`/`patch` do Hermes
  falha no Windows quando o bash relay está quebrado.

## Cenário (conversa real do bug)

1. Login em `http://localhost:8080/chat` (renato.horta@gmail.com / teste123).
2. Digitar e enviar: `acione o time de presenca digital`.
3. Copilot responde pedindo contexto (profissão, instagram, serviços).
4. Enviar: `eu quero criar uma academia de ia, onde ensino lideres de tecnologia
   a trabalhar com agentes de ia e criar automacoes de processos. meu perfil atual é novo`.
   - Se o Copilot tiver memória da conversa anterior (FAIL na proposta genérica),
     ele pergunta os serviços específicos — fornecer a lista de consultoria em IA.
5. Crew dispara. Aguardar 1-3 min (7 tasks com LLM, execução em thread separada).

## Verificações (via browser_console)

Ler as bolhas do chat (o snapshot NÃO mostra o texto delas):
```js
Array.from(document.querySelectorAll('.msg__bubble')).map(b => b.innerText).join('\n---\n')
```

### Critério 1 — progresso real
Durante a execução, o card deve mostrar:
```
Crew acionada: <nome>
Executando…
X de N etapas concluídas
Y%
🔎 Agent A
🎨 Agent B
...
```
(antes do fix: só "Executando…" + imagem genérica, sem lista de tasks).

### Critério 2 — resultado no card
Quando DONE, o card exibe `finalOutput.content` no próprio card + botões
"Aprovar entrega" / "Rejeitar". (antes: card pedia aprovação sem mostrar o
resultado).

### Critério 3 — refresh preserva história
Dar F5. A conversa mais recente deve carregar e o card deve CONTINUAR visível
com o resultado (reconstruído via `toThreadMessage` a partir do `runStatus`).

### Critério 4 — conversa única
```js
window.__chatDebug ? JSON.stringify({activeId: window.__chatDebug.activeId, convCount: (window.__chatDebug.conversations||[]).length}) : "sem debug"
```
Esperado: `convCount: 1` e `activeId` == thread da conversa.

### Critério 5 — quality gate
Se a crew se auto-avaliou, o card mostra `PASS`/`FAIL`. Com PASS, gate passou.
Com FAIL persistente, deveria haver retry/escalation (ver `run_pipeline_async`).

### Critério 6 — markdown do resultado renderizado
O `finalOutput.content` no card deve renderizar markdown (negritos, listas,
títulos), não texto plano com `**`/`*` literais. Verificar contando elementos
HTML no card da entrega:
```js
(() => { const els = document.querySelectorAll('.msg__bubble .markdown-body');
  const res = []; els.forEach((c,i) => { const strong=c.querySelectorAll('strong').length;
  const li=c.querySelectorAll('li').length; res.push(i+': strong='+strong+' li='+li); });
  return res.join('\n'); })()
```
Card da entrega esperado com `strong>0` e `li>0` (ex.: `strong=26 li=25` p/ um
PASS longo). Fix: `CrewRunCard.tsx` usa `ReactMarkdown` + `remarkGfm` com classe
`markdown-body` (antes: `whitespace-pre-wrap` = texto plano).

## Resultado esperado (tentativa 1 do loop real)

Todos os critérios passaram de primeira. O card mostrou "0 de 7 etapas" com a
lista das 7 tasks; terminou com PASS (Reality Checker); após F5 o card continuou
visível com o resultado e botões; `convCount: 1`.

## Backend/frontend tocados para o fix

- `crews/crew_runner_async.py` — quality gate (FAIL→retry→escalation) + handoff_template
- `crews/services.py` (hire_crew) e `chat/skills/cp_base_skill.py` — copiam
  quality_gate/max_retries/handoff_template das tasks do template
- `crews/tasks_async.py` — `on_task_done` síncrono grava progresso ao vivo
- `chat/run_status.py` — `crewName` no runStatus
- `useConversationThreadList.tsx` — `toThreadMessage` reconstrói card a partir do runStatus
- `CrewRunCard.tsx` — barra de progresso + resultado final no card
- `src/lib/api/types.ts` — ChatMessage.runStatus tipado

## Testes automatizados criados

- `tests/crews/test_quality_gate_async.py` — quality gate no async (mock crewai)
- `tests/chat/test_run_status_message.py` — runStatus com crewName + finalOutput

## Documentação do loop

`.hermes/docs/testes-de-loop/LOOP-<data>-crew-run-card.md` — template com
critérios + tabela de resultados por tentativa.
