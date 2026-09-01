---
name: cp-inicializador-doc
description: "Inicializador de Documentação — centraliza o contexto do projeto em .context/ (fonte de verdade única), cria arquivos ponte CLAUDE.md e AGENT.md na raiz, ingere o vision.md e gera a estrutura completa de documentação cobrindo todas as disciplinas de engenharia (requisitos, arquitetura, segurança/LGPD, qualidade/QA, devops/operações, inbox, tracking e o kanban da esteira). Use quando o usuário disser 'inicializar documentação', 'iniciar projeto', 'setup de docs', 'criar estrutura de contexto', 'inicializar repo', 'preparar documentação do projeto'."
---

# cp-inicializador-doc — Inicializador de Documentação

Centraliza o contexto do projeto em **`.context/`** como fonte de verdade única,
eliminando a poluição de diretórios como `.hermes/` ou `.claude/`. Cria arquivos
ponte na raiz (`CLAUDE.md` e `AGENT.md`) que instruem qualquer agente a usar
exclusivamente `.context/`.

## Analogia

Imagine um **arquiteto de documentação** que organiza a casa antes da obra:

```
[Raiz do repo]
   ├── CLAUDE.md  ──► "use .context/ como fonte de verdade"
   ├── AGENT.md   ──► "use .context/ como fonte de verdade"
   └── .context/  ──► (fonte de verdade única)
        ├── docs/          (disciplinas de engenharia)
        ├── inbox/         (iniciativas, tasks, bugs, débitos)
        ├── tracking/      (rastreamento de progresso)
        └── kanban/        (esteira de execução — cp-agilista)
```

## Uso

```
/carregar skill cp-inicializador-doc
inicializar documentação do projeto
```

Ou:

```
inicialize a documentação deste repositório
```

## Estrutura gerada em `.context/`

```
.context/
├── README.md                 # Índice da fonte de verdade
├── docs/
|│   ├── 00-vision.md          # Visão do produto + Iniciativas (épicos)
|│   ├── 01-requisitos.md      # Requisitos (cp-requisitos)
|│   ├── 02-arquitetura.md     # Arquitetura (cp-arquitetura)
|│   ├── 03-seguranca-lgpd.md  # Segurança/LGPD (cp-seguranca)
|│   ├── 04-qualidade-qa.md    # Qualidade/QA (cp-qualidade, cp-testes)
|│   ├── 05-devops-operacoes.md# DevOps/Operações (cp-devops)
|│   └── 06-kanban.md          # Kanban/esteira (cp-agilista)
|├── inbox/
|│   ├── iniciativas/          # Iniciativas de produto (épicos) — entrada bruta
|│   ├── tasks/                # Tarefas
|│   ├── bugs/                 # Bugs
|│   └── debitos-tecnicos/     # Débitos técnicos
|├── tracking/
|│   ├── progresso.md          # Progresso geral do projeto
|│   └── decisoes.md           # Registro de decisões (ADRs)
|└── kanban/                   # Esteira de execução (cp-agilista)
|    ├── README.md             # Colunas, formato da task, comandos
|    ├── 1-backlog/            # Entrada; o daemon varre por `status: ready`
|    ├── 2-todo/
|    ├── 3-doing/
|    ├── 4-review/
|    ├── 5-testing/
|    ├── 6-staging/
|    ├── 7-done/
|    └── blocked/              # Dúvidas e impedimentos aguardando resposta
```

O kanban nasce **na inicialização**, não no primeiro run do `cp-agilista`: a
esteira precisa de fila desde o dia 1, e `.context/docs/06-kanban.md` referencia
`.context/kanban/`. As colunas são criadas com `.gitkeep` porque o git não
versiona diretório vazio. As constantes espelham `KANBAN_COLUMNS`/`BLOCKED_DIR`
de `cp-agilista/scripts/run.py` — alterar uma exige alterar a outra.

`inbox/` é entrada bruta (rascunho); depois de triado, o item vira task em
`kanban/1-backlog/`.

**Iniciativas (épicos)** não têm arquivo separado em `tracking/`: a visão
agregada de iniciativas e seu status faz parte de `docs/00-vision.md`. Cada
iniciativa agrega múltiplos cards do kanban e o conteúdo de cada card individual
(task, bug, débito técnico) está no próprio card dentro de `kanban/`.

## Arquivos ponte na raiz

- **`CLAUDE.md`** — instrui o Claude Code a usar `.context/` como fonte de verdade.
- **`AGENT.md`** — instrui o Hermes Agent (e outros agentes) a usar `.context/`.

Ambos apontam para `.context/README.md` e proíbem a criação de `.hermes/`/`.claude/`.

## Fluxo de inicialização

1. **README + ponteiros** — cria `.context/README.md`, `CLAUDE.md` e `AGENT.md` na raiz (sobrescreve se já existirem, são infraestrutura).
2. **docs/ disciplinares** — cria `docs/00-vision.md` a `docs/06-kanban.md` **só se não existirem**. Conteúdo já populado por skills ou edição manual é preservado intacto. `00-vision.md` usa `VISION_TEMPLATE` próprio, com seção `## Iniciativas (Épicos)`.
3. **inbox/ + tracking/ + kanban/** — cria as pastas e READMEs de infraestrutura (sobrescrevem).
4. **Migração tracking → kanban** — se `tracking/tasks.md`, `tracking/bugs.md` ou `tracking/debitos-tecnicos.md` existirem, extrai cada seção de conteúdo e injeta no card kanban correspondente (`kanban/{coluna}/{ID}.md`). Os tracking files são movidos para `tracking/_backup_pre_migracao/`. Idempotente: cards já com `## Conteúdo do tracking` são ignorados.
5. **Ingestão do `vision.md`** — se existir na raiz, move para `.context/docs/00-vision.md`.
6. **Relatório de gaps** — apresenta resumo executivo e perguntas clarificatórias segmentadas por disciplina para sanar dúvidas antes da implementação.

### Regras de idempotência

| Alvo | Sobrescreve? | Motivo |
|------|-------------|--------|
| `docs/*.md` | **Não** | Conteúdo já pode estar populado |
| `README.md`, `CLAUDE.md`, `AGENT.md` | Sim | Infraestrutura, sem customização |
| `inbox/*/README.md` | Sim | Template padronizado |
| `tracking/progresso.md`, `tracking/decisoes.md` | Sim | Template padronizado |
| `kanban/README.md`, `.gitkeep` | Sim | Infraestrutura |
| Cards kanban existentes | **Não** | `migrate_tracking_to_kanban()` pula se já tem `## Conteúdo do tracking` |

### Estrutura canônica do tracking

`tracking/` contém apenas:
- `progresso.md` — progresso geral do projeto (gerido pelo orquestrador)
- `decisoes.md` — registro de ADRs

Tasks individuais (bug, débito técnico, task de feature) têm **conteúdo completo dentro do card kanban** (`kanban/{coluna}/{ID}.md`), não em arquivos de tracking separados. Iniciativas/épicos (visão agregada de múltiplos cards) ficam em `docs/00-vision.md`.

## Script

```bash
# Inicializar documentação (usa o diretório atual)
python .hermes/skills/cp-inicializador-doc/scripts/run.py

# Inicializar em um diretório específico
python .hermes/skills/cp-inicializador-doc/scripts/run.py --dir /caminho/do/projeto

# Dry run (mostra o que faria, sem criar)
python .hermes/skills/cp-inicializador-doc/scripts/run.py --dry-run
```

## Integração com o orquestrador

O `cp-inicializador-doc` é acionado pelo `cp-orquestrador` via o modo
`inicializador-doc`:

```bash
python .hermes/skills/cp-orquestrador/scripts/run.py "inicializar documentação" --mode inicializador-doc --auto
```

## Regra global: toda skill cp-* documenta em `.context/`

Toda skill `cp-*` (requisitos, arquitetura, implementação, testes, segurança,
devops, documentação, qualidade, bug-fix, competitive-analysis, goal-loop,
manutencao, agilista) deve **documentar seus artefatos em `.context/`** seguindo
a estrutura acima. O `cp-inicializador-doc` garante que a estrutura exista; as
demais skills escrevem seus outputs nos arquivos correspondentes de `.context/docs/`.
