---
name: cp-agilista
description: "Agilista — esteira de execução de tarefas com polling contínuo, loop bidirecional de feedback (dúvidas e impedimentos) e integração Trello/Local. O LOCAL (.context/kanban/) é sempre a fonte de verdade; o Trello é apenas uma visão espelhada. Monitora o backlog, despacha tarefas para a cp-orquestrador, captura respostas humanas e desbloqueia a esteira. Use quando o usuário disser 'agilista', 'esteira de tarefas', 'kanban', 'monitorar backlog', 'despachar tarefas', 'polling de tarefas', 'feedback loop', 'dúvida', 'impedimento', 'resumir tarefa'."
---

# cp-agilista — Agilista (Esteira de Execução)

Agilista é o **maestro da esteira de execução**. Ele monitora continuamente o
backlog **local** (`.context/kanban/`), despacha tarefas prontas para a `cp-orquestrador`,
e gerencia o **loop bidirecional de feedback** — capturando dúvidas e impedimentos
da IA, e retomando tarefas quando o humano responde.

## Arquitetura: Local é a fonte de verdade

```
[Local .context/kanban/]  ──(fonte de verdade)──►  [Trello (espelho/visão)]
      ▲                                              │
      └────────────── sincroniza estado ──────────────┘
```

- **O LOCAL (`.context/kanban/`) é SEMPRE a fonte de verdade.** Todas as decisões
  (scan, movimentação, dúvidas, impedimentos, retomada) acontecem no local.
- **O Trello é apenas uma VISÃO ESPELHADA** do estado local. Se o espelhamento
  estiver habilitado (`--sync-trello`), cada mudança local é refletida no Trello.
- **O Trello NUNCA decide o estado** — apenas exibe o que está no local.

## Analogia

Imagine um **maestro de orquestra** que também é o **porteiro**:

```
[Backlog local] ──► [Agilista detecta tarefa ready] ──► [Despacha p/ cp-orquestrador]
                                                          │
                    ┌─────────────────────────────────────┘
                    ▼
              [IA tem dúvida?] ──► [❓ Dúvida p/ humano] ──► [Aguarda resposta]
                    │                                              │
                    └── [IA bloqueada?] ──► [🚧 Impedimento] ──► [blocked/]
                                                                   │
                    [Humano responde] ◄────────────────────────────┘
                          │
                          ▼
              [HUMAN_CLARIFICATION_RECEIVED] ──► [Desbloqueia esteira]
```

## Uso

```
/carregar skill cp-agilista
iniciar esteira
```

Ou:

```
agilista, monitore o backlog e despache as tarefas prontas
```

## Componentes

### 1. `CPAgilistaDaemon` (Polling & Watcher)

- Cria a estrutura automática de pastas locais em `.context/kanban/`:
  `1-backlog/`, `2-todo/`, `3-doing/`, `4-review/`, `5-testing/`, `6-staging/`,
  `7-done/` e `blocked/`.
- Varredura contínua do **local** por arquivos com `status: ready` (frontmatter YAML).
- Despacho padronizado do evento `TASK_DISPATCHED` para a `cp-orquestrador`.
- Se `--sync-trello`, espelha cada despacho no Trello (visão).

### 2. `CPAgilistaFeedbackLoop` (Bidirecionalidade)

- **Dúvidas (`DUVIDA`)**: adiciona seção `## ❓ Dúvidas Pendentes` no arquivo local
  (e espelha no Trello com label `ai:waiting-human` se habilitado).
- **Impedimentos (`IMPEDIMENTO`)**: move o arquivo local para `blocked/` e anexa
  log de erro e severidade.
- **Retomada (`resume_task`)**: captura a resposta humana no local e emite o evento
  `HUMAN_CLARIFICATION_RECEIVED` para desbloquear a esteira.

### 3. `TrelloMirror` (Espelho/Visão)

- Reflete o estado local no Trello (cria/atualiza cards conforme a coluna local).
- Se as tools MCP do Trello não estiverem disponíveis, o espelhamento é
  desabilitado silenciosamente — o local continua funcionando sozinho.

### 4. Template de Task `.md` e Matriz de Estados

- Esquema com frontmatter YAML completo para versionamento via Git.

## Matriz de Estados

| Estado | Pasta | Descrição |
|--------|-------|-----------|
| `backlog` | `1-backlog/` | Tarefa aguardando priorização |
| `ready` | `1-backlog/` | Pronta para despacho (flag `status: ready`) |
| `todo` | `2-todo/` | Despachada, aguardando execução |
| `doing` | `3-doing/` | Em execução pela cp-orquestrador |
| `review` | `4-review/` | Aguardando revisão |
| `testing` | `5-testing/` | Em testes |
| `staging` | `6-staging/` | Em staging |
| `done` | `7-done/` | Concluída |
| `blocked` | `blocked/` | Impedida, aguardando humano |

## Eventos

| Evento | Origem | Destino |
|--------|--------|---------|
| `TASK_DISPATCHED` | Agilista (daemon) | cp-orquestrador |
| `DUVIDA` | IA (durante execução) | Humano (local + espelho Trello) |
| `IMPEDIMENTO` | IA (durante execução) | blocked/ |
| `HUMAN_CLARIFICATION_RECEIVED` | Humano (resposta) | Esteira (desbloqueio) |

## Script

```bash
# Iniciar daemon de polling (sempre lê do local)
python .hermes/skills/cp-agilista/scripts/run.py --daemon

# Iniciar daemon com espelhamento Trello (visão do local)
python .hermes/skills/cp-agilista/scripts/run.py --daemon --sync-trello

# Sincronizar o estado local inteiro para o Trello (one-shot)
python .hermes/skills/cp-agilista/scripts/run.py --sync-trello

# Registrar dúvida (no local; espelha no Trello se habilitado)
python .hermes/skills/cp-agilista/scripts/run.py --duvida "task-123" --mensagem "Qual o escopo do MVP?" --sync-trello

# Registrar impedimento
python .hermes/skills/cp-agilista/scripts/run.py --impedimento "task-123" --erro "Falha de conexão" --severidade alta

# Retomar tarefa (resposta humana)
python .hermes/skills/cp-agilista/scripts/run.py --resume "task-123" --resposta "O MVP cobre login e cadastro"
```

## Integração com o orquestrador

O `cp-agilista` é acionado pelo `cp-orquestrador` via o modo `agilista`:

```bash
python .hermes/skills/cp-orquestrador/scripts/run.py "iniciar esteira" --mode agilista --auto
```

O daemon despacha `TASK_DISPATCHED` para o orquestrador, que executa a tarefa
via o pipeline adequado (full, sprint, micro, etc.).
