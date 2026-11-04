# Core Product Skills

Central repository for the **skills** propagated to the **Hermes Agent** and
**Claude Code** — the **single source of truth**: any change is made here and then
propagated to the agents via `scripts/install.sh`.

The skills implement the **Rational Unified Process (RUP)** — 9 disciplines, 21
roles — grounded in *The Rational Unified Process: An Introduction* (3rd ed.),
Philippe Kruchten.

**The agent running a skill is the LLM** (ADR-0012). The skills never call a
model and have no runtime dependency (standard library only): they hand the agent
a *work packet* — the RUP roles, missions, required artifacts and the context
already recorded — and then validate and record the agent's document into the
project's `.context/` (mandatory, ADR-0011). No API key, no proxy, no CrewAI: the
same model, with the same conversation context, writes the artifacts.

> History: the legacy Software Factory family (removed in ADR-0010) also used the
> `cp-` prefix; the current `cp-*` skills are the RUP skills, renamed from `rup-*`
> (ADR-0014). The CrewAI execution was replaced by the host-LLM model (ADR-0012).

## Guia rápido para o time (pt-BR)

São 15 skills que levam o RUP para dentro do Claude Code: discovery, backlog em
cards, desenvolvimento com TDD, debug, revisão, documentação e uma auditoria que
mede se os testes realmente pegam bugs. **O próprio Claude que você já usa faz
todo o trabalho**: as skills não chamam outra IA, não pedem API key e só
dependem do Python.

### 1. Pré-requisitos

- Claude Code instalado
- Python 3.10+ e git
- bash (no Windows, use o **Git Bash**)

### 2. Baixar e instalar

```bash
git clone https://github.com/renatohorta/core-poroduct-skills.git
cd core-poroduct-skills
bash scripts/install.sh --claude
```

As skills vão para `~/.claude/skills/`. Abra uma sessão nova do Claude Code e
digite `/cp-` para ver a lista. Para conferir antes, sem instalar nada:
`bash scripts/install.sh --claude --dry-run`.

### 3. Atualizar

```bash
cd core-poroduct-skills && git pull && bash scripts/install.sh --claude
```

Nunca edite a cópia instalada em `~/.claude/skills`: ela é apagada e reescrita
a cada instalação. Melhorias vão por PR neste repositório.

### 4. Primeiro uso num projeto

Todos os artefatos ficam na pasta `.context/` do projeto (docs, cards, roadmap,
decisões).

- Na primeira vez, o Claude **pede autorização** antes de criar ou alterar a
  `.context/`. Basta aprovar.
- Se o projeto já tiver documentação (`docs/`, `.specs/`, outra `.context/`),
  nada é apagado: o Claude pergunta e pode importar o que já existe.
- Projeto preparado antes desta versão? Peça "prepare o .context deste projeto"
  de novo: a nota no `CLAUDE.md`/`AGENT.md` é atualizada para o roteamento
  automático.
- Recomendado: commitar a `.context/` junto com o código.

### 5. Como usar: só peça

**Você não precisa saber o nome de nenhuma skill.** Descreva o que quer, em
linguagem natural, e o Claude passa pelo orquestrador
(`cp-orchestrator --route`), que lê o estado do projeto, escolhe a skill certa e
segue o fluxo sozinho (ADR-0017):

| Você diz… | O Claude faz |
|---|---|
| "quero uma tela de login com Google" | discovery → requisitos → backlog → build de cada task → review |
| "o checkout está dando erro 500" | abre um BUG, reproduz, teste de regressão, causa raiz, fix, review |
| "muda o texto do botão de pagar" | task direto no backlog → build → review (sem discovery) |
| "revisa o TK-012" | review do card e registro do veredito |
| "nossos testes servem pra alguma coisa?" | auditoria estática + teste de mutação + cards para as lacunas |
| "e agora?" / "continua" | o próximo passo que o estado do projeto indica |
| "documenta o projeto inteiro no padrão RUP" | governança + as 8 disciplinas, em ordem |

Ele só para e pergunta quando precisa de você: autorizar a `.context/`, a
conversa de discovery, confirmar os cards gerados, uma ambiguidade real ou algo
destrutivo/externo (push, deploy).

### 6. As skills por trás (se quiser chamar direto)

| Skill | Para quê |
|---|---|
| `cp-orchestrator` | Porta de entrada (`--route`), documentação RUP, estimativa (Use Case Points), plano de iteração |
| `cp-discover` | Antes de construir algo novo: problema, usuários, objetivos, o que fica fora |
| `cp-backlog` | Épicos, stories e tasks; releases e iterações; mover cards (`1-backlog` → `7-done`) |
| `cp-build TK-001` | Implementa em TDD (teste vermelho primeiro); testes do tipo `assert True` são rejeitados |
| `cp-debug` | BUG → reprodução → teste de regressão → causa raiz **antes** do fix |
| `cp-review TK-001` | Revisa um card em `4-review`: `approved` ou `changes requested` |
| `cp-test --audit` | "Os testes pegam bugs?": auditoria estática e teste de mutação. Num projeto nosso, 96% de cobertura pegaram só 76% dos mutantes |

### 7. Dicas

- Cada skill tem um `SKILL.md` com tudo o que faz; o catálogo está em
  [`skills/README.md`](skills/README.md).
- As skills nunca rodam git: branch, commit e merge continuam com você. A única
  que roda testes é `cp-test --mutate`, e só em cópias temporárias do projeto.
- Dúvidas, bugs ou ideias: abra uma issue neste repositório.
> All of it remains in the git history.

## The RUP skills (`skills/cp-*`)

| Skill | Discipline | Roles |
|-------|------------|-------|
| `cp-orchestrator` | Project Management (governance) | 1 |
| `cp-environment` | Environment | 1 |
| `cp-business-modeling` | Business Modeling | 2 |
| `cp-requirements` | Requirements | 2 |
| `cp-analysis-design` | Analysis & Design | 5 |
| `cp-implementation` | Implementation | 2 |
| `cp-test` | Test + test-value audit (mutation) | 4 |
| `cp-ccm` | Configuration & Change Management | 2 |
| `cp-deployment` | Deployment | 2 |

## The execution skills (replace the superpowers plugin — ADR-0013)

Six more skills conduct the work and keep its state readable in `.context/`:
cards (epic, story, task, bug), a roadmap of releases and iterations, and cards
that move between kanban columns.

| Skill | Use it to |
|-------|-----------|
| `cp-context` | Check the project's `.context/`, **ask the user**, then adopt the RUP standard (`--init`), import existing docs |
| `cp-discover` | Talk before building: problem, users, goals, non-goals, anti-goals; recorded in Inception |
| `cp-backlog` | Create epics/stories/tasks, derive them from requirements, move cards, plan releases/iterations, generate the roadmap and board |
| `cp-build` | Start a task test-first, then finish it with a delivery whose tests are checked for value |
| `cp-debug` | Open a bug card, pin it with a regression test, record the root cause before the fix |
| `cp-review` | Review a card in `4-review` and record `approved` / `changes requested` |

15 skills in total: 9 document skills + 6 execution skills.

Full details: [`skills/README.md`](skills/README.md) and each skill's `SKILL.md`; architecture and
operation in [`.context/docs/`](.context/docs/).

## How a skill runs

```
agent ──► run.py "<briefing>" --phase P        ─► WORK PACKET (read-only)
                                                   roles · missions · required artifacts
                                                   briefing · earlier .context/ artifacts
agent writes ONE document: "# <Role>" + "## <Artifact>" for each required artifact
agent ──► run.py --record doc.md --phase P     ─► validates every "## <Artifact>"
                                                   writes .context/docs/<NN-phase>/cp-<skill>.md
                                                   logs   .context/tracking/rup-log.md
```

- **Front door**: the user never has to pick a skill. The agent runs
  `cp-orchestrator --route "<request>"`, which reads the state of `.context/`
  (authorization, discovery, requirements, board, open bugs), suggests the next
  step and lists every route with its command; the agent classifies the request
  and runs the chain itself (new feature: discover → requirements → backlog →
  build → review; bug: debug → build → review), stopping only at the gates
  (authorization, discovery answers, confirming cards, real ambiguity) (ADR-0017).
- **Chaining**: a discipline's packet embeds the governance artifact and the
  artifacts of the earlier disciplines recorded in the same phase. Run them in
  order and each builds on the previous ones.
- **Whole iteration**: `cp-orchestrator "<briefing>" --auto` prints the
  protocol (governance + 8 disciplines, in order, with the commands);
  `--status` shows what is recorded and the next pending step.
- **Sizing**: Use Case Points are computed by code (`--estimate`), never by the
  model; the governance packet tells the agent how.
- **Which `.context/`**: `--context-dir`, else `$RUP_CONTEXT_DIR`, else the
  nearest `.context/` up to the git root. Curated docs (`requirements.md`, …)
  are never touched — generated artifacts carry the `rup-` prefix.
- **Authorization**: every writing command needs the marker
  `.context/.rup-standard`. Without it the skill writes nothing and exits 5; the
  agent asks the user and, on approval, runs `cp-context --init` (ADR-0013).
- **Execution skills**: `cp-backlog` creates and moves cards
  (`.context/kanban/<column>/<ID>.md`), plans `.context/roadmap/` and generates
  `docs/06-roadmap.md` and `docs/06-board.md`; `cp-build --start/--finish`,
  `cp-debug --open/--diagnose` and `cp-review <ID>` / `--record` drive a task
  from `3-doing` to review. The skills never run git or your tests — except
  `cp-test --mutate` (below).
- **Do the tests catch bugs?** `cp-test "<briefing>" --audit` prints the audit
  protocol (A0–A8): baseline, static audit, mutation testing of the risky modules
  in disposable copies, survivor triage, cards for the real gaps (ADR-0016).

## Repository structure

```
core-poroduct-skills/
├── README.md                 # This file
├── CLAUDE.md / AGENT.md      # Context for coding agents working on this repo
├── requirements.txt          # Runtime dependencies: none (stdlib only)
├── requirements-dev.txt      # pytest
├── .github/workflows/ci.yml  # CI
├── .context/                 # Operational context (source of truth for agents)
├── tests/                    # Suite (no LLM, 309 tests, ~10 s)
├── scripts/install.sh        # Installs/updates the skills in the agents
└── skills/
    ├── README.md
    ├── _shared/              # helpers, not a skill
    │   ├── rup.py            # phases, ordered disciplines, exit codes
    │   ├── discipline.py     # work packet + --record engine
    │   ├── context.py        # .context/ resolution, writing, authorization marker
    │   ├── consent.py        # --status/--init/--import, pointer note
    │   ├── frontmatter.py    # card frontmatter parser/writer
    │   ├── cards.py          # cards, moves, roll-up, derivation
    │   ├── roadmap.py        # releases, iterations, generated views
    │   ├── testcheck*.py     # test-value checks (Python ast, JS/TS patterns)
    │   ├── testaudit.py      # static audit of a whole suite
    │   ├── router.py         # front door: state of .context/ + routes (--route)
    │   └── mutation.py       # mutation testing: mutants, runner, report, triage
    ├── cp-orchestrator/     # front door (--route), governance, iteration protocol, UCP
    ├── cp-<discipline>/     # SKILL.md + scripts/run.py (roles as data) + references/
    └── cp-{context,discover,backlog,build,debug,review}/   # execution skills
```

## Quick install

```bash
./scripts/install.sh                       # every skill, Hermes + Claude
./scripts/install.sh --hermes | --claude   # one agent
./scripts/install.sh --skill cp-requirements
./scripts/install.sh --dry-run
```

Destinations, overrides and runbook: [`.context/docs/04-transition/devops-infra.md`](.context/docs/04-transition/devops-infra.md).

## Development and testing

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt
.venv/bin/python -m pytest                # Linux/macOS (.venv/Scripts/python.exe on Windows)
```

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | Every skill: stdlib only (`python -S`), packet with roles/artifacts/record command, exit 1 on missing briefing or unreadable `--input`, `SKILL.md` teaches `--record`, well-formed specs (9 document skills, 21 roles). Orchestrator: registry == skill dirs, `--list`, `--discipline`, `--auto` protocol order, sizing instructions; UCP exact/validated/CLI. `install.sh` plan and installed copies running in the Claude and Hermes layouts |
| `tests/test_context_persistence.py` | `.context/` resolution, layout, provenance, log, curated docs untouched; `--record` per skill (file/stdin), rejection of missing artifacts, exit 4; packets read-only; chaining in RUP order and per phase, cap on earlier artifacts; `--status`; caller's project resolution; sizing artifact; guard that the suite never writes into this repo |
| `tests/test_consent.py`, `tests/test_rup_context.py` | Authorization marker and exit 5 on writing commands, non-destructive `--init`/upgrade, pointer note, import leaves originals untouched |
| `tests/test_frontmatter.py`, `tests/test_cards.py`, `tests/test_roadmap.py` | Card parser/writer, IDs, criteria, moves, History, roll-up, derivation, roadmap files and generated views |
| `tests/test_testcheck.py`, `tests/test_rup_{discover,build,debug,review}.py` | Test-value checks (trivial tests, criterion links, red evidence), start/finish with good and bad deliveries, bug flow, review verdicts |
| `tests/test_rup_test_audit.py` | cp-test audit: mutant generator, runner (kill/survive/timeout/error, resume, changed-tree refusal, budget, lines), report, triage rules, static audit, CLI and consent; mutation steps in cp-build/cp-review/cp-debug/orchestrator |
| `tests/test_higiene.py` | No committed secrets, no machine paths in code |

CI (`.github/workflows/ci.yml`): Python 3.12/3.13 on Linux (blocking) and Windows
(informative), plus `install.sh --dry-run`, on pushes to `main` and on PRs.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error: missing briefing, unreadable `--input`, document missing required artifacts, invalid sizing model |
| 4 | `.context/` not writable |
| 5 | Needs authorization: `.context/` lacks the `.rup-standard` marker — ask the user, then `cp-context --init` |

Exit 1 also covers an invalid card/document and a rejected delivery.

## Portability

No hardcoded OS/machine paths or personal values. Each `run.py` finds `_shared/`
next to the skill (repository, Claude Code) or one level up (Hermes, which nests
skills in a category directory).

## License

Internal use. © Renato Sacramento Horta.
