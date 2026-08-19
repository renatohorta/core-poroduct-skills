# kanban/ — Esteira de Execução

Fonte de verdade do fluxo de tarefas, gerida pela skill `cp-agilista`. Quando o
Trello está configurado, ele é apenas uma **visão espelhada** — o que vale é o
que está aqui.

## Relação com `../inbox/`

`inbox/` é entrada bruta: rascunho de iniciativa, task, bug ou débito técnico.
Depois de triado, o item vira uma task aqui, em `1-backlog/`, com `status:`
preenchido — mova com `git mv` para preservar o histórico.

## Colunas

| Pasta | Significado |
|-------|-------------|
| `1-backlog/` | Entrada. O daemon varre aqui por tasks com `status: ready` |
| `2-todo/` | Priorizada, aguardando execução |
| `3-doing/` | Em execução (despachada para a `cp-orquestrador`) |
| `4-review/` | Aguardando revisão |
| `5-testing/` | Em teste |
| `6-staging/` | Homologação |
| `7-done/` | Concluída |
| `blocked/` | Dúvida ou impedimento aguardando resposta humana |

## Formato de uma task

Um arquivo `.md` por task, com frontmatter YAML. O campo `status:` deve
acompanhar a pasta em que o arquivo está.

```markdown
---
id: TASK-001
title: Título da task
status: ready
priority: media
assignee:
created_at: 2026-01-01T00:00:00
updated_at: 2026-01-01T00:00:00
tags: []
---

# Título da task

## Descrição

## Critérios de Aceitação

- [ ] ...
```

`status:` válidos: `backlog`, `ready`, `todo`, `doing`, `review`, `testing`,
`staging`, `done`, `blocked`. Só `ready` no `1-backlog/` é despachado.

## Comandos

```bash
# Monitorar o backlog e despachar tasks
python <skills>/cp-agilista/scripts/run.py --daemon

# Documentar o estado atual do kanban em ../docs/06-kanban.md
python <skills>/cp-agilista/scripts/run.py --doc
```
