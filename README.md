# Core Product Skills

Repositório central das **skills de produto** da Fábrica de Software (CrewAI) e de
geração de carrosséis. Este é o **código-fonte canônico** das skills — a partir dele
você instala/atualiza as skills tanto no **Hermes Agent** quanto no **Claude Code**.

## O que é

Este repositório contém o código base (SKILL.md + scripts + references + templates)
das skills customizadas. Ele serve como **fonte única de verdade**: qualquer alteração
é feita aqui e depois propagada para os agentes (Hermes e Claude) via o script de
instalação.

## Skills incluídas

### Fábrica de Software (CrewAI) — `cp-*`

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

### Carrosséis de Instagram

| Skill | Função |
|-------|--------|
| `universal-carousel` | Geração de carrosséis ponta a ponta (escolhe template, injeta conteúdo, renderiza PNG 1080x1350) |
| `universal-carousel-template-creator` | Criação/reconstrução de templates HTML/CSS de carrossel |
| `instagram-carousel-generator` | Renderer determinístico "Modern Minimalist Coral" (PIL) |

## Estrutura do repositório

```
core-poroduct-skills/
├── README.md                 # Este arquivo
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
    ├── ... (todas as skills)
    └── instagram-carousel-generator/
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

## Portabilidade

As skills são **portáveis** — não contêm paths de SO/máquina hardcoded nem valores
pessoais fixos. Fontes são resolvidas por plataforma (Windows/macOS/Linux) via
`shutil.which`/env vars, e paths de projeto usam env vars + defaults relativos.

## Licença

Uso interno. © Renato Sacramento Horta.
