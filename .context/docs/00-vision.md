# Visão do Produto — Core Product Skills

> Fonte de verdade: `.context/`. Atualizado em 2026-08-18.

## Status

- [x] Concluído (visão inicial documentada)

## O que é

**Core Product Skills** é o repositório canônico das skills `cp-*` da **Fábrica de
Software** — um conjunto de skills baseadas em CrewAI que orquestram agentes
especializados para executar o ciclo completo de desenvolvimento de software, do
requisito à entrega, com quality gates entre fases.

Este repositório é o **código-fonte único**: qualquer alteração é feita aqui e
propagada para os agentes consumidores (**Hermes Agent** e **Claude Code**) via
`scripts/install.sh`.

## Problema que resolve

Sem este repositório, cada agente teria sua própria cópia divergente das skills,
com paths hardcoded e configuração de LLM acoplada a um provider. Isso gerava:

- **Divergência** entre a skill instalada no Hermes e a instalada no Claude.
- **Retrabalho** ao corrigir o mesmo bug em dois lugares.
- **Acoplamento a provider** — as crews caíam no default OpenAI do CrewAI
  (`OPENAI_API_KEY is required`) mesmo com outro provider configurado.

## Proposta de valor

| Pilar | Como se materializa |
|-------|---------------------|
| **Fonte única de verdade** | Skills editadas em `skills/`, propagadas por `install.sh` |
| **Ponto único de entrada** | `cp-orquestrador` aciona todas as demais skills por modo |
| **Provider-agnostic** | `skills/_shared/llm.py` resolve o LLM do agente hospedeiro |
| **Portabilidade** | Zero paths de SO/máquina e zero valores pessoais hardcoded |
| **Quality gates** | Cada fase só avança com PASS/WARN; FAIL interrompe o pipeline |

## Usuários

| Persona | Uso |
|---------|-----|
| **Hermes Agent** | Consome as skills instaladas em `$HERMES_SKILLS_DIR/creative/` |
| **Claude Code** | Consome as skills instaladas em `~/.claude/skills/` |
| **Desenvolvedor/mantenedor** | Edita as skills aqui e roda `install.sh` |
| **Operador via CLI** | Aciona skills diretamente por `scripts/chat.py` |

## Escopo

**Dentro do escopo**
- Código-fonte das 15 skills `cp-*` (SKILL.md + `scripts/run.py` + `references/`)
- Helper compartilhado de LLM (`skills/_shared/llm.py`)
- Script de instalação/propagação (`scripts/install.sh`)
- Ferramentas de apoio: chat direto (`scripts/chat.py`) e proxy OpenAI-compatível
  para usar o Claude Code como LLM (`scripts/claude_proxy.py`)

**Fora do escopo**
- Runtime dos agentes (Hermes Agent e Claude Code são projetos separados)
- Os projetos-alvo onde o pipeline é executado (ex.: `crewbotics-back`)
- Hospedagem/infra de LLM — o repositório apenas resolve credenciais e endpoints

## Princípios de design

1. **Skill é self-contained** — cada `run.py` embute seus próprios agentes; não
   depende de diretório externo de agentes.
2. **O orquestrador é o gerente da fábrica** — direcione todo pedido para ele; ele
   escolhe o modo, planeja as fases e aplica os quality gates.
3. **Contrato CLI explícito** — o metadado `invoke` descreve como cada skill recebe
   briefing (`positional`/`goal`/`input`/`daemon`/`dir`) e se aceita `--output`.
   Nunca assuma; teste com `--dry-run`.
4. **Auto-detecção sobre flags opcionais** — o modo correto deve ser detectado do
   contexto, não depender de o LLM lembrar de setar um flag.
5. **Documentação em `.context/`** — nunca em `.hermes/` ou `.claude/`.

## Decisões

- **ADR-0001** — Fonte de verdade em `.context/` (ver `.context/tracking/decisoes.md`).
- **ADR-0002** — `cp-full-dev` fundido no `cp-orquestrador` (pipeline NEXUS nativo).
- **ADR-0003** — LLM provider-agnostic via `skills/_shared/llm.py`.
