# Core Product Skills

Repositório central das **skills da Fábrica de Software** (CrewAI). Este é o
**código-fonte canônico** das skills `cp-*` — a partir dele você instala/atualiza
as skills tanto no **Hermes Agent** quanto no **Claude Code**.

## O que é

Este repositório contém o código base (SKILL.md + scripts + references) das skills
`cp-*` da Fábrica de Software. Ele serve como **fonte única de verdade**: qualquer
alteração é feita aqui e depois propagada para os agentes (Hermes e Claude) via o
script de instalação.

## Skills incluídas

Pipeline completo de desenvolvimento orquestrado por crews de agentes CrewAI.

| Skill | Função |
|-------|--------|
| `cp-orquestrador` | **Gerente da fábrica** — coordena todas as crews em sequência, gerencia artefatos e aplica quality gates. Inclui o pipeline NEXUS nativo (merge de `cp-full-dev`). |
| `cp-requisitos` | Engenharia de Requisitos (Analista de Negócios, Especificador, Validador, PO Proxy) |
| `cp-arquitetura` | Arquitetura e Design (Arquiteto de Software, Dados, API, UX, Revisor) |
| `cp-implementacao` | Implementação (Dev Backend, Frontend, Mobile, Revisor, Integrador) |
| `cp-testes` | Testes (Unitário, Integração, E2E, Performance, Analista) |
| `cp-seguranca` | Segurança (Analista, Pentester, Compliance, Engenheiro de Correção) |
| `cp-devops` | DevOps e Infra (CI/CD, Infra, Monitoramento, Segurança de Infra) |
| `cp-documentacao` | Documentação (Redator Técnico, Usuário, Diagramador, Revisor) |
| `cp-qualidade` | Qualidade (Auditor, Métricas, Melhoria Contínua, Validador) |
| `cp-bug-fix` | Correção de bugs (Developer → QA → Evidence Collector, máx. 3 retries) |
| `cp-competitive-analysis` | Inteligência competitiva (Mercado, Competidores, Pricing, Estrategista) |
| `cp-goal-loop` | Loop autônomo de tentativa-e-correção até atingir sucesso |
| `cp-manutencao` | Manutenção e evolução (bug-fix, refactor, improvement, full) |
| `cp-agilista` | Esteira de execução — monitora backlog, despacha tarefas e gerencia feedback bidirecional (dúvidas, impedimentos, retomada) |
| `cp-inicializador-doc` | Inicializador de documentação — centraliza o contexto em `.context/` (fonte de verdade única) e cria ponteiros CLAUDE.md/AGENT.md |

## Estrutura do repositório

```
core-poroduct-skills/
├── README.md                 # Este arquivo
├── requirements.txt          # Dependencias de runtime (crewai)
├── requirements-dev.txt      # + pytest
├── pytest.ini
├── .github/workflows/ci.yml  # CI
├── tests/                    # Suite (nao usa credencial de LLM)
├── docs/
│   ├── INSTALLATION.md       # Como instalar/atualizar em Hermes e Claude
│   ├── ARCHITECTURE.md       # Arquitetura da Fábrica de Software
│   └── SKILLS.md             # Catálogo detalhado de cada skill
├── scripts/
│   └── install.sh            # Instala/atualiza as skills nos agentes
└── skills/
    ├── cp-orquestrador/
    │   ├── SKILL.md
    │   ├── scripts/run.py
    │   └── references/*.md
    ├── cp-requisitos/
    ├── ... (todas as skills cp-*)
    └── cp-testes/
```

## Instalação rápida

```bash
# Instala/atualiza todas as skills no Hermes e no Claude
./scripts/install.sh

# Apenas no Hermes
./scripts/install.sh --hermes

# Apenas no Claude
./scripts/install.sh --claude

# Apenas uma skill específica
./scripts/install.sh --skill cp-requisitos
```

Veja [docs/INSTALLATION.md](docs/INSTALLATION.md) para detalhes.

## Desenvolvimento e testes

```bash
# Ambiente (uv e bem mais rapido que pip para as ~135 transitivas do crewai)
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt

# Suite completa — nao precisa de nenhuma credencial de LLM
.venv/Scripts/python.exe -m pytest        # Windows
.venv/bin/python -m pytest                # Linux/macOS
```

A suite (158 testes) **nunca chama LLM**: testar o modelo e caro, lento e
nao-deterministico, e nao pega os bugs que de fato ocorrem aqui — que sao de
contrato CLI e de tratamento de erro.

| Arquivo | O que garante |
|---------|---------------|
| `tests/test_smoke.py` | `--help` funciona em toda skill (mesmo sem `crewai`); `--dry-run` roda sem credencial; falta de LLM/lib sai com codigo e mensagem acionavel |
| `tests/test_contrato_invoke.py` | O metadado `invoke` do orquestrador bate com o `argparse` real — inclusive rodando a linha de comando que o orquestrador montaria |
| `tests/test_quality_gate.py` | O quality gate reprova por exit code e nao aprova por substring |
| `tests/test_claude_proxy_auth.py` | Autenticacao do proxy e bind restrito a localhost |
| `tests/test_higiene.py` | Nenhum segredo versionado, nenhum path de maquina no codigo |

CI em `.github/workflows/ci.yml`: roda a suite em Python 3.12 e 3.13 no Linux
(bloqueante) e no Windows (informativo), mais `install.sh --dry-run`.

### Codigos de saida das skills

| Codigo | Significado |
|--------|-------------|
| 0 | Sucesso |
| 1 | Erro de uso (briefing ausente, argumento invalido) |
| 2 | Nenhum LLM configurado |
| 3 | `crewai` nao instalado |

`--help` funciona sempre, e `--dry-run` inspeciona a crew sem credencial.

## Portabilidade

As skills são **portáveis** — não contêm paths de SO/máquina hardcoded nem valores
pessoais fixos. Paths de projeto usam env vars + defaults relativos.

## LLM das skills (provider-agnostic)

As skills CrewAI usam o **LLM do agente onde estão sendo chamadas** (Hermes/Claude),
com fallback para um `.env` local. O helper `skills/_shared/llm.py` resolve o LLM
na ordem:

1. Env vars do agente (`LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_PROVIDER`)
2. `.env` na raiz do projeto (mesma convenção do crewbotics-back)
3. Detecção de chave por provider (`GEMINI_API_KEY`, `OPENAI_API_KEY`, etc.)
4. Default: `gemini/gemini-2.5-flash`

Isso evita que as skills caiam no default OpenAI do CrewAI (`OPENAI_API_KEY is
required`) mesmo com outro provider configurado.

## Conversa direta com as skills (scripts/chat.py)

O `scripts/chat.py` permite acionar qualquer skill cp-* de forma interativa,
usando o LLM do `.env` (sem depender do agente):

```bash
python scripts/chat.py --list                          # lista as skills
python scripts/chat.py cp-requisitos "sistema de agendamento"
python scripts/chat.py cp-requisitos "briefing" --dry-run
```

O script detecta automaticamente o Python com `crewai` instalado (`.venv` do
projeto) e carrega o `.env`.

## Usar o Claude Code como LLM das crews (scripts/claude_proxy.py)

As crews CrewAI podem usar o **Claude Code como LLM** (via OAuth, sem precisar de
`ANTHROPIC_API_KEY`). O `scripts/claude_proxy.py` expõe uma API OpenAI-compatível
que delega cada chamada ao comando `claude -p`:

```bash
# 1. Inicia o proxy (porta 8090, evita conflito com frontends na 8080)
python scripts/claude_proxy.py --port 8090

# 2. Testa uma chamada
python scripts/claude_proxy.py --test
```

Depois, configure o `.env` das skills para apontar para o proxy:

```env
LLM_MODEL=openai/claude-sonnet-4
LLM_API_BASE=http://localhost:8090/v1
LLM_API_KEY=***   # o proxy ignora, mas o CrewAI exige
LLM_PROVIDER=openai
```

> **Nota:** o proxy usa o modelo padrão do Claude Code (não passa `--model` para
> modelos genéricos). Para escolher um modelo específico, defina `CLAUDE_MODEL`
> no ambiente (ex: `claude-opus-4`).

## Licença

Uso interno. © Renato Sacramento Horta.
