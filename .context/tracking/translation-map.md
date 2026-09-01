# Canonical PT→EN identifier map for the core-product-skills repo

This file is the single source of truth for translating Portuguese identifiers
to English across the repo. Use it EXACTLY. Do not invent alternatives.

## Skill directory / skill-name renames (ALREADY DONE — do not redo)

| Old (PT) | New (EN) |
|----------|----------|
| cp-agilista | cp-agile |
| cp-arquitetura | cp-architecture |
| cp-documentacao | cp-documentation |
| cp-implementacao | cp-implementation |
| cp-inicializador-doc | cp-doc-initializer |
| cp-manutencao | cp-maintenance |
| cp-orquestrador | cp-orchestrator |
| cp-qualidade | cp-quality |
| cp-requisitos | cp-requirements |
| cp-seguranca | cp-security |
| cp-testes | cp-testing |

Already-English (unchanged): cp-benchmark-to-spec, cp-bug-fix,
cp-competitive-analysis, cp-devops, cp-goal-loop.

## CLI flags (argparse) — translate flag name AND all references

| PT flag | EN flag |
|---------|---------|
| --duvida | --question |
| --mensagem | --message |
| --impedimento | --blocker |
| --erro | --error |
| --severidade | --severity |
| --resposta | --answer |
| --resume | --resume (keep) |
| --triage | --triage (keep) |
| --task | --task (keep) |
| --update-status | --update-status (keep) |
| --kanban-task | --kanban-task (keep) |
| --sync-trello | --sync-trello (keep) |
| --init | --init (keep) |
| --doc | --doc (keep) |
| --iterations | --iterations (keep) |
| --auto | --auto (keep) |
| --daemon | --daemon (keep) |
| --dir | --dir (keep) |
| --dry-run | --dry-run (keep) |
| --goal | --goal (keep) |
| --input | --input (keep) |
| --output | --output (keep) |
| --mode | --mode (keep) |
| --python | --python (keep) |
| --source | --source (keep) |
| --start-phase | --start-phase (keep) |
| --steps | --steps (keep) |
| --steps-file | --steps-file (keep) |
| --type | --type (keep) |
| --acceptance | --acceptance (keep) |
| --bug | --bug (keep) |
| --max-attempts | --max-attempts (keep) |
| --max-time | --max-time (keep) |

## Severity / priority values

| PT | EN |
|----|----|
| baixa | low |
| media | medium |
| alta | high |
| critica | critical |

## Frontmatter fields (task .md YAML)

| PT field | EN field |
|----------|----------|
| tipo | type |
| origem | source |
| descricao | description |
| prioridade | priority |
| status | status (keep) |
| assignee | assignee (keep) |
| created_at | created_at (keep) |
| updated_at | updated_at (keep) |
| tags | tags (keep) |
| title | title (keep) |
| id | id (keep) |

## Track types (TRILHAS / tipo values)

| PT | EN |
|----|----|
| iniciativa | initiative |
| task | task (keep) |
| bug | bug (keep) |
| debito-tecnico | tech-debt |

## Inbox subdirectories

| PT | EN |
|----|----|
| iniciativas | initiatives |
| tasks | tasks (keep) |
| bugs | bugs (keep) |
| debitos-tecnicos | tech-debt |

## Event names (constants)

| PT | EN |
|----|----|
| EVENT_DUVIDA | EVENT_QUESTION |
| EVENT_IMPEDIMENTO | EVENT_BLOCKER |
| EVENT_HUMAN_CLARIFICATION | EVENT_HUMAN_CLARIFICATION (keep) |
| EVENT_TASK_DISPATCHED | EVENT_TASK_DISPATCHED (keep) |
| EVENT_INBOX_TRIADO | EVENT_INBOX_TRIAGED |

## Class / function / variable renames (code identifiers)

| PT | EN |
|----|----|
| CPAgilistaDaemon | CPAgileDaemon |
| CPAgilistaFeedbackLoop | CPAgileFeedbackLoop |
| add_duvida | add_question |
| add_impedimento | add_blocker |
| duvida() | question() |
| impedimento() | blocker() |
| resume_task | resume_task (keep) |
| mensagem | message |
| resposta | answer |
| erro | error |
| severidade | severity |
| origem | source |
| tipo | type |
| trilha | track |
| TRILHAS | TRACKS |
| DEFAULT_TRILHA | DEFAULT_TRACK |
| TRILHA_PATTERNS | TRACK_PATTERNS |
| triagem | triage |
| esteira | pipeline |
| execucao | execution |
| tarefa | task |
| orquestrador | orchestrator |
| agilista | agile |
| inicializador | initializer |
| requisito(s) | requirement(s) |
| arquitetura | architecture |
| implementacao | implementation |
| seguranca | security |
| documentacao | documentation |
| qualidade | quality |
| manutencao | maintenance |
| artefato(s) | artifact(s) |
| fase(s) | phase(s) |
| relatorio | report |
| analise | analysis |
| correcao | fix |
| evidencia | evidence |
| validador | validator |
| especificador | specifier |
| redator | writer |
| diagramador | diagrammer |
| revisor | reviewer |
| auditor | auditor |
| metricas | metrics |
| melhoria | improvement |
| integrador | integrator |
| desenvolvedor | developer |
| engenheiro | engineer |
| analista | analyst |
| especialista | specialist |
| estrategista | strategist |
| mercado | market |
| concorrente(s) | competitor(s) |
| posicionamento | positioning |
| diagnostico | diagnosis |
| corretor | fixer |
| executor | executor |
| gestor | manager |
| tomador-de-decisao | decision-maker |
| relator-de-progresso | progress-reporter |
| orquestrador-de-pipeline | pipeline-orchestrator |
| gestor-de-artefatos | artifact-manager |
| progresso | progress |
| decisao | decision |
| fonte | source |
| verdade | truth |
| espelho | mirror |
| despacho | dispatch |
| retomada | resume |
| objetivo | goal |
| alcancado | reached |
| completo | full |
| completos | complete |
| pendentes | pending |
| concluido | completed |
| falhou | failed |
| encontrada | found |
| importado(s) | imported |
| nada | nothing |
| nenhum | none |
| sucesso | success |
| briefing | briefing (keep) |
| pipeline | pipeline (keep) |
| kanban | kanban (keep) |
| sprint | sprint (keep) |
| micro | micro (keep) |
| full | full (keep) |
| nativo | native |
| memoria | memory |
| discovery | discovery (keep) |
| operate | operate (keep) |
| monitor | monitor (keep) |
| deploy | deploy (keep) |
| infra | infra (keep) |
| observabilidade | observability |
| provisionamento | provisioning |

## MODOS / CREWS keys in cp-orchestrator run.py

| PT key | EN key |
|--------|--------|
| requisitos | requirements |
| arquitetura | architecture |
| implementacao | implementation |
| testes | testing |
| seguranca | security |
| devops | devops (keep) |
| documentacao | documentation |
| qualidade | quality |
| manutencao | maintenance |
| agilista | agile |
| inicializador-doc | doc-initializer |
| bug-fix | bug-fix (keep) |
| competitive-analysis | competitive-analysis (keep) |
| goal-loop | goal-loop (keep) |
| full-dev | full-dev (keep) |
| full | full (keep) |
| sprint | sprint (keep) |
| micro | micro (keep) |
| security-audit | security-audit (keep) |
| documentation | documentation (keep) |
| bugfix | bugfix (keep) |
| competitive | competitive (keep) |

## NEXUS agent role keys (already English mostly, keep)

engineering-*, design-*, marketing-*, product-*, project-*, support-*,
testing-* — these are already English. Keep as-is.

## Section headers in task .md template

| PT | EN |
|----|----|
| ## Descrição | ## Description |
| ## Critérios de Aceitação | ## Acceptance Criteria |
| ## Dúvidas Pendentes | ## Pending Questions |
| ## Log de Impedimentos | ## Blockers Log |
| ### ❓ [Dúvida da IA | ### ❓ [AI Question |
| ### 🚧 [Impedimento] | ### 🚧 [Blocker] |
| ### ✅ [Resposta Humana] | ### ✅ [Human Answer] |

## Kanban doc headers

| PT | EN |
|----|----|
| # Kanban / Esteira de Execução | # Kanban / Execution Pipeline |
| ## Estado do Kanban | ## Kanban State |
| ## Tarefas por coluna | ## Tasks by column |
| | Coluna | Tarefas | | | Column | Tasks | |
| prioridade | priority |

## IMPORTANT RULES

1. Translate ALL user-facing strings (help text, print messages, docstrings,
   comments, SKILL.md prose, README, docs) to English.
2. Keep code identifiers consistent: if you rename a function/class/variable,
   rename ALL its usages in the same file AND across files that import it.
3. Keep the kanban column names (1-backlog, 2-todo, 3-doing, 4-review,
   5-testing, 6-staging, 7-done, blocked) UNCHANGED — they are the on-disk
   contract shared by cp-agile and cp-doc-initializer and asserted in tests.
4. Keep status values (backlog, ready, todo, doing, review, testing, staging,
   done, blocked) UNCHANGED — asserted in tests.
5. Keep the task id prefixes (INIT, TASK, BUG, DT) UNCHANGED.
6. Keep the .context/ directory structure and file names (docs/00-vision.md,
   docs/06-kanban.md, inbox/, kanban/, tracking/) UNCHANGED — they are the
   on-disk contract.
7. Keep env var names (KANBAN_ROOT, INBOX_ROOT, LLM_*, etc.) UNCHANGED.
8. Keep the quality-gate keyword logic (PASS/FAIL/WARN, TRACEBACK, FALHOU,
   CRÍTICO) — translate the PT keywords to English equivalents (TRACEBACK,
   FAILED, CRITICAL) and update the tests that assert on them.
9. Do NOT translate the NEXUS agent role keys (engineering-*, etc.).
10. Do NOT touch .venv/, outputs/, __pycache__/, .git/.
