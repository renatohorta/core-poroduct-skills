# .context/ — Fonte de Verdade do Projeto

**Projeto**: Core Product Skills — repositório canônico das skills `cp-*` da
Fábrica de Software (CrewAI), propagadas para o **Hermes Agent** e o **Claude Code**.

Este diretório é a **fonte de verdade única** do contexto do projeto. Todos os
agentes devem ler e escrever contexto aqui, **nunca** em `.hermes/` ou `.claude/`.

## Por onde começar

| Quero… | Leia |
|--------|------|
| Entender o produto | `docs/00-vision.md` |
| Saber o que o sistema faz e o que falta | `docs/01-requisitos.md` |
| Entender como funciona por dentro | `docs/02-arquitetura.md` |
| Instalar/operar/depurar | `docs/05-devops-operacoes.md` |
| Ver o que está na fila | `docs/06-kanban.md` |
| Saber por que algo é assim | `tracking/decisoes.md` |

## Estrutura

### docs/ — Disciplinas de engenharia
| Arquivo | Disciplina | Skill que escreve |
|---------|-----------|-------------------|
| `00-vision.md` | Visão do produto | `cp-inicializador-doc` |
| `01-requisitos.md` | Requisitos | `cp-requisitos`, `cp-competitive-analysis` |
| `02-arquitetura.md` | Arquitetura | `cp-arquitetura`, `cp-implementacao`, `cp-manutencao` |
| `03-seguranca-lgpd.md` | Segurança/LGPD | `cp-seguranca` |
| `04-qualidade-qa.md` | Qualidade/QA | `cp-testes`, `cp-documentacao`, `cp-qualidade`, `cp-bug-fix` |
| `05-devops-operacoes.md` | DevOps/Operações | `cp-devops`, `cp-goal-loop` |
| `06-kanban.md` | Kanban/esteira | `cp-agilista` |

### inbox/ — Entrada de trabalho
Um arquivo `.md` por item.

- `iniciativas/` — Iniciativas de produto
- `tasks/` — Tarefas
- `bugs/` — Bugs (`DT-01`, `DOC-01`)
- `debitos-tecnicos/` — Débitos técnicos (`DT-02` … `DT-06`)

### tracking/ — Rastreamento
- `progresso.md` — Progresso geral e próximos passos
- `decisoes.md` — Registro de decisões (ADR-0001 … ADR-0006)

## Regras

1. Toda skill `cp-*` documenta seus artefatos em `docs/`, conforme o mapa acima.
2. Trabalho novo entra por `inbox/`, não direto em `docs/`.
3. Decisão relevante vira ADR em `tracking/decisoes.md` — com contexto e
   consequências, não só a conclusão.
4. Em divergência entre `.context/` e `docs/` (documentação humana do repositório),
   **`.context/` prevalece**.

## Relação com `docs/` na raiz

`docs/` (`ARCHITECTURE.md`, `INSTALLATION.md`, `SKILLS.md`) é documentação de
apresentação, voltada a leitores humanos. `.context/` é o contexto operacional,
voltado a agentes — inclui estado real, gaps e pendências.
