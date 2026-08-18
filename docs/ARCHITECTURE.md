# Arquitetura da Fábrica de Software

A Fábrica de Software é um conjunto de skills CrewAI que orquestram agentes
especializados para executar o ciclo completo de desenvolvimento de software —
do requisito à entrega — com quality gates entre fases.

## Visão geral

```
                    ┌─────────────────────────────┐
                    │     cp-orquestrador         │
                    │  (Gerente da Fábrica)       │
                    │  - coordena crews           │
                    │  - gerencia artefatos       │
                    │  - aplica quality gates     │
                    └─────────────┬───────────────┘
                                  │ aciona (modos)
        ┌────────────┬────────────┼────────────┬──────────────┐
        ▼            ▼            ▼            ▼              ▼
   [Pipeline]   [Complementares] [NEXUS]   [Carrosséis]   [Análise]
   cp-requisitos cp-bug-fix      full-dev   universal-     cp-competitive-
   cp-arquitetura cp-goal-loop   (nativo)   carousel       analysis
   cp-implementacao cp-manutencao           instagram-
   cp-testes                                  carousel-
   cp-seguranca                               generator
   cp-devops
   cp-documentacao
   cp-qualidade
```

## Pipeline principal (modo `full`)

```
[Requisitos] → [Arquitetura] → [Implementação] → [Testes] → [Segurança] → [DevOps] → [Documentação] → [Qualidade] → [Entrega]
     │              │                │              │           │            │             │              │
 cp-requisitos  cp-arquitetura  cp-implementacao cp-testes  cp-seguranca cp-devops  cp-documentacao cp-qualidade
     │              │                │              │           │            │             │              │
 [Quality Gate] [Quality Gate]  [Quality Gate] [Quality Gate][Quality Gate][Quality Gate][Quality Gate][Quality Gate]
```

Cada fase produz um artefato que alimenta a próxima. O quality gate decide:
- **PASS** → avança
- **WARN** → avança com ressalvas documentadas
- **FAIL** → interrompe o pipeline

## Modos de operação

| Modo | Crews | Uso |
|------|-------|-----|
| `full` | 8 fases do pipeline | Projeto completo |
| `sprint` | requisitos → arquitetura → implementação → testes → devops | Feature |
| `micro` | implementação → testes | Bug fix rápido |
| `security-audit` | segurança → qualidade | Auditoria de segurança |
| `documentation` | documentação → qualidade | Documentação |
| `bugfix` | cp-bug-fix | Correção de bug |
| `competitive` | cp-competitive-analysis | Inteligência competitiva |
| `full-dev` | NEXUS nativo | Pipeline NEXUS completo |
| `goal-loop` | cp-goal-loop | Loop autônomo |
| `manutencao` | cp-manutencao | Manutenção/evolução |

## Pipeline NEXUS (nativo no orquestrador)

O `cp-full-dev` foi **fundido** no `cp-orquestrador`. O pipeline NEXUS (7 fases,
39 agentes) roda nativamente via `NexusExecutor`:

```
Discovery → Strategy → Foundation → Build → Hardening → Launch → Operate
```

Com detecção automática de modo (full/sprint/micro) e quality gates por fase.

## Contrato de acionamento (metadado `invoke`)

Cada crew no orquestrador carrega metadado `invoke` que descreve como a skill é
acionada via CLI:

- `briefing_arg`: `positional` (arg posicional), `goal` (`--goal`), ou `input` (`--input`)
- `output`: `True` se a skill aceita `--output`, `False` caso contrário

Isso garante que o orquestrador chame cada skill respeitando sua interface real.

## Portabilidade

Todas as skills são portáveis:
- **Zero paths de SO/máquina hardcoded** (C:\Windows, C:\Users, etc.)
- **Zero valores pessoais fixos** (handles, nomes de máquina)
- Paths de projeto usam env vars + defaults relativos
