# CLAUDE.md — Contexto do Projeto

**Projeto**: Core Product Skills — repositório canônico das skills `cp-*` da
Fábrica de Software (CrewAI), propagadas para o Hermes Agent e o Claude Code.

**Fonte de verdade: `.context/`**

Leia e escreva todo o contexto do projeto em `.context/`. **NÃO** crie nem use
`.hermes/` ou `.claude/` para contexto.

- Visão geral: `.context/README.md`
- Disciplinas de engenharia: `.context/docs/`
- Entrada de trabalho: `.context/inbox/`
- Rastreamento e ADRs: `.context/tracking/`

## Regras essenciais deste repositório

1. **Edite as skills aqui**, em `skills/` — a cópia instalada no agente é
   descartada e reescrita a cada `./scripts/install.sh`.
2. **`_shared` não é skill** — é helper compartilhado; vai para a raiz de skills
   do agente, não para a categoria.
3. **Nunca assuma o contrato CLI de uma skill** — `--output` não é universal e o
   briefing nem sempre é posicional. Consulte
   `skills/cp-orquestrador/references/skills-cli-inventory.md` e valide com
   `--dry-run`.
4. **Windows**: rode as skills com `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` até
   `DT-01` ser corrigido.
5. **Antes de commitar**: confira `git status --short` — commits parciais são o
   erro mais comum aqui.
