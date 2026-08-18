# Kanban / Esteira — Core Product Skills

> Disciplina: Esteira de execução (`cp-agilista`). Atualizado em 2026-08-18.

## Status

- [x] Backlog inicial registrado
- Fonte de verdade do kanban: **local** (`.context/inbox/`). Trello, se conectado,
  é apenas uma visão espelhada.

## Fluxo

```
.context/inbox/{iniciativas,tasks,bugs,debitos-tecnicos}/
        │  cp-agilista (polling)
        ▼
   cp-orquestrador  ──► skill do modo adequado ──► .context/docs/<disciplina>.md
        │
        └─► dúvida/impedimento ──► volta ao inbox aguardando resposta humana
```

## Board

### 🔵 Backlog

_(vazio — todo o backlog levantado na inicializacao foi concluido em 2026-08-18)_

Trabalho novo entra por `.context/inbox/`.

### 🟡 Em andamento

_(vazio)_

### 🟢 Concluido

| ID | Item | Data |
|----|------|------|
| DT-02 | Suite de smoke tests (`--help`, `--dry-run`, exit codes) | 2026-08-18 |
| DT-03 | Validacao do contrato `invoke` x `argparse` | 2026-08-18 |
| DT-04 | Autenticacao opcional no `claude_proxy.py` (`CLAUDE_PROXY_TOKEN`) | 2026-08-18 |
| DT-05 | `requirements.txt` + `requirements-dev.txt` | 2026-08-18 |
| DT-06 | CI (GitHub Actions: Linux 3.12/3.13 + Windows informativo) | 2026-08-18 |
| DOC-01 | Porta do proxy alinhada em 8090 | 2026-08-18 |
| BUG-03 | Quality gate reprova por exit code != 0 | 2026-08-18 |
| BUG-04 | Quality gate casa keywords por palavra inteira | 2026-08-18 |
| BUG-05 | `cp-goal-loop` deriva passo unico do `--goal` | 2026-08-18 |
| DT-07 | `crewai` com import guardado — `--help` em 15/15 | 2026-08-18 |
| DT-08 | `require_llm()` falha cedo com mensagem acionavel | 2026-08-18 |
| DT-01 | `setup_console()` forca UTF-8 no stdout/stderr | 2026-08-18 |
| INIT-01 | Inicializacao da documentacao em `.context/` | 2026-08-18 |

## Convenções

- Um arquivo `.md` por item, dentro da pasta de inbox correspondente.
- Item concluído: marcar `[Concluído]` (feature) ou `[Corrigido]` (bug) no título e
  mover com `git mv` para a pasta de processados, preservando o histórico.
- Prioridade segue MoSCoW, alinhada a `.context/docs/01-requisitos.md`.
