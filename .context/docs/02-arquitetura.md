# Arquitetura — Core Product Skills

> Disciplina: Arquitetura e Design (`cp-arquitetura`). Atualizado em 2026-08-18.

## Status

- [x] Concluído (arquitetura atual documentada)

## Visão em camadas

```
┌──────────────────────────────────────────────────────────────┐
│ CONSUMIDORES (fora deste repo)                               │
│   Hermes Agent            Claude Code                        │
│   $HERMES_SKILLS_DIR/creative/   ~/.claude/skills/           │
└───────────────▲──────────────────────▲───────────────────────┘
                │  scripts/install.sh (propagação)
┌───────────────┴──────────────────────┴───────────────────────┐
│ REPOSITÓRIO CANÔNICO (este repo)                             │
│                                                              │
│  skills/cp-orquestrador   ← ponto único de entrada           │
│      └── scripts/run.py   (4 agentes + NexusExecutor)        │
│                │ subprocess (contrato CLI `invoke`)          │
│      ┌─────────┴─────────────────────────────────┐           │
│      ▼                                           ▼           │
│  Pipeline (8 skills)                  Complementares (6)     │
│   cp-requisitos                        cp-bug-fix            │
│   cp-arquitetura                       cp-competitive-analysis│
│   cp-implementacao                     cp-goal-loop          │
│   cp-testes                            cp-manutencao         │
│   cp-seguranca                         cp-agilista           │
│   cp-devops                            cp-inicializador-doc  │
│   cp-documentacao                                            │
│   cp-qualidade                                               │
│                                                              │
│  skills/_shared/llm.py    ← resolução provider-agnostic      │
│  scripts/chat.py          ← acionamento direto (CLI)         │
│  scripts/claude_proxy.py  ← Claude Code como LLM (OpenAI API)│
└──────────────────────────────────────────────────────────────┘
                                │ escreve artefatos
                                ▼
                    .context/ do PROJETO-ALVO
```

## Componentes

| Componente | Caminho | Responsabilidade |
|-----------|---------|------------------|
| **Orquestrador** | `skills/cp-orquestrador/scripts/run.py` | Coordena crews, gerencia artefatos, aplica quality gates, executa o NEXUS nativo |
| **Skills de pipeline** | `skills/cp-{requisitos,arquitetura,implementacao,testes,seguranca,devops,documentacao,qualidade}/` | Uma disciplina de engenharia cada, com crew CrewAI própria |
| **Skills complementares** | `skills/cp-{bug-fix,competitive-analysis,goal-loop,manutencao,agilista,inicializador-doc}/` | Fluxos fora do pipeline linear |
| **Helper de LLM** | `skills/_shared/llm.py` | `build_crew_llm()` / `get_llm_config()` — resolve model/key/base |
| **Instalador** | `scripts/install.sh` | Propaga `skills/` para Hermes e Claude |
| **Chat direto** | `scripts/chat.py` | Aciona qualquer skill interativamente usando o `.env` |
| **Proxy Claude** | `scripts/claude_proxy.py` | API OpenAI-compatível delegando a `claude -p` |

## Anatomia de uma skill

```
skills/cp-<nome>/
├── SKILL.md          # frontmatter (name, description/gatilhos) + documentação
├── scripts/run.py    # self-contained: agentes CrewAI + CLI (argparse)
└── references/*.md   # conhecimento durável (pitfalls, inventários, procedimentos)
```

Cada `run.py` é **self-contained**: os agentes estão embutidos no próprio Python,
sem dependência de diretório externo de agentes.

## Contrato de acionamento (metadado `invoke`)

O orquestrador chama cada skill por `subprocess`. O contrato é declarado no dict
`CREWS` de `cp-orquestrador/scripts/run.py`:

| `briefing_arg` | Como o briefing é passado | Exemplo de skill |
|----------------|---------------------------|------------------|
| `positional` | argumento posicional | `cp-bug-fix`, `cp-competitive-analysis` |
| `goal` | `--goal <briefing>` | `cp-goal-loop` |
| `input` | posicional na 1ª fase; `--input <ctx>` nas seguintes | fases do pipeline |
| `daemon` | sem briefing — monta `--daemon` | `cp-agilista` |
| `dir` | sem briefing — monta `--dir <cwd>` | `cp-inicializador-doc` |

`invoke.output` indica se a skill aceita `--output`. **Não assuma** — `cp-bug-fix`,
`cp-goal-loop` e `cp-agilista` **rejeitam** `--output`. Ver
`skills/cp-orquestrador/references/skills-cli-inventory.md`.

## Fluxo de dados entre fases

```
briefing ─► cp-requisitos ─► requisitos.md
                                │  (_ctx_<fase>.txt: briefing + artefato anterior[:3000])
                                ▼
                          cp-arquitetura --input _ctx_arquitetura.txt ─► arquitetura.md
                                ▼
                          ... até a entrega
```

Artefatos vão para `cp-orquestrador/outputs/pipeline_<timestamp>/`, com
`pipeline_report.json` ao final. A documentação consolidada vai para
`.context/docs/` do projeto-alvo.

## Modos do orquestrador

| Modo | Fases |
|------|-------|
| `full` | requisitos → arquitetura → implementação → testes → segurança → devops → documentação → qualidade |
| `sprint` | requisitos → arquitetura → implementação → testes → devops |
| `micro` | implementação → testes |
| `security-audit` | segurança → qualidade |
| `documentation` | documentação → qualidade |
| `bugfix` / `competitive` / `full-dev` / `goal-loop` / `manutencao` / `agilista` / `inicializador-doc` | skill única |

## Resolução do LLM (`_shared/llm.py`)

Ordem, provider-agnostic:

1. Env vars do agente — `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_PROVIDER`
2. `.env` na raiz do projeto
3. Detecção por chave de provider (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …)
4. Default: `gemini/gemini-2.5-flash`

Providers mapeados: gemini/google, openai, anthropic/claude, ollama, openrouter,
deepseek, groq, mistral, cohere, together, xai/grok.

## Decisões arquiteturais

- **ADR-0002** — `cp-full-dev` fundido no orquestrador; o NEXUS roda em memória via
  `NexusExecutor`, eliminando um hop de subprocess e a skill separada.
- **ADR-0003** — LLM resolvido pelo helper `_shared/llm.py` em vez do default do
  CrewAI, evitando `OPENAI_API_KEY is required` com outro provider ativo.
- **ADR-0004** — Comunicação entre skills por `subprocess` + arquivos, não por
  import Python: mantém cada skill self-contained e instalável isoladamente.
- **ADR-0005** — `install.sh` faz `rm -rf` no destino antes de copiar: a cópia
  instalada é descartável e sempre reflete o repositório.

Registro completo: `.context/tracking/decisoes.md`.
