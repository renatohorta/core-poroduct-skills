---
name: cp-software-spec
description: "Software Spec & Knowledge Base — Unifica inicialização, engenharia reversa e especificação de software em modelo RUP conciso (.context/), gerando insumos acionáveis para replicação de código por agentes e refinando cards do Kanban em issues executáveis. Use when the user says 'initialize documentation', 'start project', 'docs setup', 'create context structure', 'reverse engineer', 'inspect codebase', 'document the system', 'specify screens', 'refine card', 'backlog to todo', 'ready for dev'."
---

# cp-software-spec — Software Spec & Knowledge Base

Unifica **inicialização**, **engenharia reversa** e **especificação de software**
em um modelo RUP conciso (`.context/`), gerando insumos acionáveis para a
replicação de código por agentes autônomos e refinando cards do Kanban em
**issues executáveis (Ready for Dev)**.

Substitui as skills legadas `cp-doc-initializer` e `cp-documentation`.

## Analogy

Imagine um **arquiteto de documentação** que organiza a casa antes da construção
e, depois, **mapeia a casa existente** para que outro construtor possa replicá-la:

```
[Repo root]
   ├── CLAUDE.md  ──► "use .context/ as source of truth"
   ├── AGENT.md   ──► "use .context/ as source of truth"
   └── .context/  ──► (single source of truth)
        ├── docs/          (RUP Operacional — 4 fases)
        ├── inbox/         (initiatives, tasks, bugs, tech debt)
        ├── tracking/      (progress + ADRs)
        └── kanban/        (pipeline de execução — cp-agile)
```

## Modes of operation

```bash
# Modo 1: Inicialização / Scaffold padrão (novo projeto)
python .hermes/skills/cp-software-spec/scripts/run.py --init

# Modo 2: Engenharia Reversa / Inspeção profunda (projeto existente)
python .hermes/skills/cp-software-spec/scripts/run.py --inspect /caminho/do/projeto

# Modo 3: Refinamento de Card para Issue Executável (Backlog -> ToDo)
python .hermes/skills/cp-software-spec/scripts/run.py --refine-card TASK-001
```

Flags comuns: `--dir <path>` (diretório do projeto), `--dry-run` (mostra o que
faria, sem criar), `--force` (sobrescreve docs mesmo com customizações manuais).

## Canonical structure in `.context/`

```
.context/
├── README.md                           # Índice central e System Prompt de contexto
├── docs/                               # Fonte Única da Verdade (RUP Operacional)
│   ├── 01-inception/
│   │   ├── vision-and-scope.md         # Visão de produto, atores e metas de negócio
│   │   └── requirements.md             # Requisitos Funcionais (FR) e Não-Funcionais (NFR)
│   ├── 02-elaboration/
│   │   ├── architecture.md             # Stack, diagramas C4/Mermaid e decisões estruturais
│   │   └── domain-model.md             # Entidades de domínio, agregados e casos de uso centrais
│   ├── 03-construction/
│   │   ├── api-contracts.md            # Contratos OpenAPI, endpoints, payloads e schemas
│   │   ├── ui-spec.md                  # Rotas, tokens de Design System, AppShell e Generative UI
│   │   └── data-dictionary.md          # Modelos de BD, migrations, tabelas e regras de persistência
│   └── 04-transition/
│       ├── test-strategy.md            # Pirâmide de testes, cobertura e comandos de execução
│       └── devops-infra.md             # Docker, CI/CD pipelines, variáveis e runbooks
├── inbox/                              # Rascunhos brutos e ideias não triadas
│   ├── .gitkeep
│   └── raw-ideas.md
├── kanban/                             # Pipeline de Execução Ágil
│   ├── README.md
│   ├── 1-backlog/                      # Cards aguardando priorização/refinamento
│   ├── 2-todo/                         # ISSUES ATIVAS: Prontas para desenvolvimento autônomo
│   ├── 3-doing/
│   ├── 4-review/
│   ├── 5-testing/
│   ├── 6-staging/
│   ├── 7-done/
│   └── blocked/
└── tracking/
    └── decisions.md                    # Registro contínuo de ADRs
```

> **Não existe `05-project-management/` nem raiz plana de `docs/`.** Todo o
> gerenciamento de tarefas reside exclusivamente no pipeline `kanban/`.

## Reverse engineering (`--inspect`)

Quando executado sobre uma base existente, o agente de análise estática deve:

1. **Inspecionar o ecossistema técnico**:
   - Manifestos: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.
   - Rotas & Telas: `src/routes/**`, páginas, componentes `AppShell` e catálogos de Generative UI.
   - APIs & Schemas: Controladores, rotas FastAPI/Express, schemas Pydantic/Zod/OpenAPI.
   - Banco de Dados: Prisma schema, modelos SQLAlchemy/Django, migrations SQL.
   - Infraestrutura: `Dockerfile`, `docker-compose.yml`, workflows GitHub Actions.
2. **Gerar documentos orientados à replicação de código**:
   - Evitar textos longos e narrativos.
   - Priorizar: tabelas de schemas, snippets de contratos de tipos, comandos
     reproduzíveis e diagramas Mermaid.
3. **Idempotência**:
   - Não sobrescrever arquivos de documentação se já contiverem customizações
     manuais profundas, a menos que solicitado com `--force`.

## Backlog -> ToDo promotion (executable issue)

Quando um card é promovido de `1-backlog/` para `2-todo/`, ele é transformado e
validado como uma **Issue Executável (Ready for Dev)** com Definition of Ready
(DoR), contratos de API, schemas e arquivos-alvo definidos.

### Schema obrigatório do card em `2-todo/` (`kanban/2-todo/{ID}.md`)

```markdown
---
id: TASK-042
title: "Implementar autenticação via Magic Link"
type: feature # feature | bug | tech-debt
status: ready
assigned_to: agent-coder
context_refs:
  - .context/docs/02-elaboration/architecture.md
  - .context/docs/03-construction/api-contracts.md
---

### 1. Contexto & Objetivo
Explicação objetiva da mudança e qual valor agrega ao sistema.

### 2. Arquivos Alvo
- **Modificar**: `src/auth/service.py`
- **Criar**: `src/auth/magic_link.py`
- **Testes**: `tests/test_magic_link.py`

### 3. Critérios de Aceite (DoR / DoD)
- [ ] O endpoint `POST /auth/magic-link` recebe `{ "email": "string" }` e retorna 200 OK.
- [ ] Token gerado possui tempo de expiração de 15 minutos e uso único.
- [ ] Cobertura de testes unitários para o fluxo >= 85%.

### 4. Insumos Técnicos e Contratos de Dados
```json
{
  "request": {
    "email": "user@domain.com"
  },
  "response": {
    "status": "success",
    "expires_at": 1741389600
  }
}
```

### 5. Passos de Validação e Execução
1. `pytest tests/test_magic_link.py -v`
2. `ruff check .`
```

## Specifying an app's SCREENS (UI generator / Lovable)

Quando o pedido é "especificar todas as telas do sistema para gerar variações de
layout" (em Lovable ou similar), o inventário NÃO deve ser dirigido apenas por
rotas. Pitfall real que já nos pegou: listar só `src/routes/*.tsx` deixa de fora
os **componentes dinâmicos** renderizados em superfícies conversacionais (chat),
que são telas/cards de primeira classe para o gerador.

Receita completa de inventário:
1. **Rotas (file-based)**: `src/routes/**/*.tsx` → uma entrada por rota.
2. **Layout/shell compartilhado**: o `AppShell`/layout (side rail + statusbar) é
   o esqueleto que TODAS as telas internas compartilham — documente uma vez e
   marque quais telas o usam (internas) e quais são fullscreen sem rail (auth).
3. **Componentes dinâmicos / Generative UI**: qualquer `registry` de cards que o
   backend renderiza dentro do chat (`render_*_tool`, `uiPayload.component`) SÃO
   telas para o gerador. Inventarie cada card (header, body, states, actions) e a
   regra de contrato (ex.: card de aprovação só encaminha a decisão ao backend).
4. **Design system obrigatório**: defina tokens (cores, fontes, componentes
   recorrentes) antes das telas — é o que mantém as variações coerentes.
5. **Estados por tela**: loading / error (com retry) / empty / populated — exija todos.
6. **Não mudar escopo**: variação é de layout, não de funcionalidade.

Reuse o esqueleto pronto em `templates/spec-telas-lovable.md` (estrutura +
checklist de inventário) como ponto de partida.

## Bridge files at the root

- **`CLAUDE.md`** — instrui Claude Code a usar `.context/` como fonte de verdade.
- **`AGENT.md`** — instrui Hermes Agent (e outros agentes) a usar `.context/`.

Ambos apontam para `.context/README.md` e proíbem a criação de `.hermes/`/`.claude/`.

## Initialization flow (`--init`)

1. **README + pointers** — cria `.context/README.md`, `CLAUDE.md` e `AGENT.md` na
   raiz (sobrescreve se já existirem; são infraestrutura).
2. **docs/ RUP** — cria os arquivos das 4 fases **apenas se não existirem**.
   Conteúdo já populado por skills ou edição manual é preservado intacto.
   `vision-and-scope.md` usa seu próprio `VISION_TEMPLATE`, com a seção
   `## Initiatives (Epics)`.
3. **inbox/ + tracking/ + kanban/** — cria as pastas e READMEs de infraestrutura (sobrescreve).
4. **Tracking → kanban migration** — se `tracking/tasks.md`, `tracking/bugs.md`
   ou `tracking/tech-debt.md` existirem, extrai cada seção e injeta no card
   correspondente do kanban. Idempotente: cards já com `## Tracking content` são ignorados.
5. **`vision.md` ingestion** — se existir na raiz, move para
   `.context/docs/01-inception/vision-and-scope.md`.
6. **Gap report** — apresenta resumo executivo e perguntas de esclarecimento por fase.

### Idempotency rules

| Target | Overwrites? | Reason |
|--------|-------------|--------|
| `docs/**/*.md` | **No** | Content may already be populated |
| `README.md`, `CLAUDE.md`, `AGENT.md` | Yes | Infrastructure, no customization |
| `inbox/*/README.md` | Yes | Standardized template |
| `tracking/progress.md`, `tracking/decisions.md` | Yes | Standardized template |
| `kanban/README.md`, `.gitkeep` | Yes | Infrastructure |
| Existing kanban cards | **No** | `migrate_tracking_to_kanban()` skips if it already has `## Tracking content` |

## Script

```bash
# Initialize documentation (uses the current directory)
python .hermes/skills/cp-software-spec/scripts/run.py --init

# Initialize in a specific directory
python .hermes/skills/cp-software-spec/scripts/run.py --init --dir /path/to/project

# Reverse-engineer an existing codebase
python .hermes/skills/cp-software-spec/scripts/run.py --inspect /path/to/project

# Refine a backlog card into an executable issue
python .hermes/skills/cp-software-spec/scripts/run.py --refine-card TASK-001

# Dry run (shows what it would do, without creating)
python .hermes/skills/cp-software-spec/scripts/run.py --init --dry-run
```

## Integration with the orchestrator

`cp-software-spec` é acionado pelo `cp-orchestrator` via o modo `software-spec`:

```bash
python .hermes/skills/cp-orchestrator/scripts/run.py "initialize documentation" --mode software-spec --auto
```

## Global rule: every cp-* skill documents in `.context/`

Every `cp-*` skill (requirements, architecture, implementation, testing, security,
devops, documentation, quality, bug-fix, competitive-analysis, goal-loop,
maintenance, agile) must **document its artifacts in `.context/`** following
the RUP structure above. The `cp-software-spec` guarantees the structure exists;
the other skills write their outputs in the corresponding files of `.context/docs/`.
