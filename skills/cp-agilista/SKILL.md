---
name: cp-agilista
description: "Agilista — esteira de execução de tarefas com polling contínuo, loop bidirecional de feedback (dúvidas e impedimentos) e integração Trello/Local. Monitora o backlog, despacha tarefas para a cp-orquestrador, captura respostas humanas e desbloqueia a esteira. Use quando o usuário disser 'agilista', 'esteira de tarefas', 'kanban', 'monitorar backlog', 'despachar tarefas', 'polling de tarefas', 'feedback loop', 'dúvida', 'impedimento', 'resumir tarefa'."
---

# cp-agilista — Agilista (Esteira de Execução)

Agilista é o **maestro da esteira de execução**. Ele monitora continuamente o
backlog (local ou Trello), despacha tarefas prontas para a `cp-orquestrador`,
e gerencia o **loop bidirecional de feedback** — capturando dúvidas e impedimentos
da IA, e retomando tarefas quando o humano responde.

## Analogia

Imagine um **maestro de orquestra** que também é o **porteiro**:

```
[Backlog] ──► [Agilista detecta tarefa ready] ──► [Despacha p/ cp-orquestrador]
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

- Cria a estrutura automática de pastas locais em `.kanban/`:
  `1-backlog/`, `2-todo/`, `3-doing/`, `4-review/`, `5-testing/`, `6-staging/`,
  `7-done/` e `blocked/`.
- Varredura contínua de arquivos com `status: ready` (frontmatter YAML) ou
  integração com as tools MCP do Trello (`list_name="Backlog"`).
- Despacho padronizado do evento `TASK_DISPATCHED` para a `cp-orquestrador`.

### 2. `CPAgilistaFeedbackLoop` (Bidirecionalidade)

- **Dúvidas (`DUVIDA`)**: injeta comentário formatado
  (`❓ [Dúvida da IA - {origem}]`) no Trello com label `ai:waiting-human`, ou
  adiciona seção `## ❓ Dúvidas Pendentes` no arquivo local.
- **Impedimentos (`IMPEDIMENTO`)**: move o card/arquivo para `blocked/` e anexa
  log de erro e severidade.
- **Retomada (`resume_task`)**: captura a resposta humana e emite o evento
  `HUMAN_CLARIFICATION_RECEIVED` para desbloquear a esteira.

### 3. Template de Task `.md` e Matriz de Estados

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
| `DUVIDA` | IA (durante execução) | Humano (Trello/local) |
| `IMPEDIMENTO` | IA (durante execução) | blocked/ |
| `HUMAN_CLARIFICATION_RECEIVED` | Humano (resposta) | Esteira (desbloqueio) |

## Script

```bash
# Iniciar daemon de polling (local)
python .hermes/skills/cp-agilista/scripts/run.py --daemon --source local

# Iniciar daemon de polling (Trello)
python .hermes/skills/cp-agilista/scripts/run.py --daemon --source trello

# Registrar dúvida
python .hermes/skills/cp-agilista/scripts/run.py --duvida "task-123" --mensagem "Qual o escopo do MVP?"

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
