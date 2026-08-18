---
name: cp-arquitetura
description: "Arquitetura e Design de Software — cria uma crew CrewAI com Arquiteto de Software, Arquiteto de Dados, Arquiteto de API, UX Architect e Revisor Técnico para definir arquitetura, modelar dados, desenhar APIs e validar decisões. Use quando o usuário disser 'definir arquitetura', 'modelar dados', 'desenhar API', 'criar ADR', 'fazer design do sistema'."
---

# cp-arquitetura — Arquitetura e Design de Software

Cria uma crew CrewAI com agentes especializados para executar o ciclo completo de arquitetura e design de software:

1. **Arquiteto de Software** — Define arquitetura (monolito, microsserviços, modular monolith), padrões, decisões arquiteturais
2. **Arquiteto de Dados** — Modela banco de dados, schema, migrações, índices
3. **Arquiteto de API** — Desenha contratos REST/GraphQL, OpenAPI, versionamento
4. **UX Architect** — Desenha fluxos de usuário, protótipos, jornadas
5. **Revisor Técnico** — Valida decisões arquiteturais, identifica riscos, sugere alternativas

## Agentes

| Agente | Função |
|--------|--------|
| Arquiteto de Software | Define arquitetura, padrões, decisões arquiteturais (ADRs) |
| Arquiteto de Dados | Modela banco de dados, schema, migrações, índices |
| Arquiteto de API | Desenha contratos REST/GraphQL, OpenAPI, versionamento |
| UX Architect | Desenha fluxos de usuário, protótipos, jornadas |
| Revisor Técnico | Valida decisões, identifica riscos, sugere alternativas |

## Entrada

Documento de requisitos ou briefing do sistema — descrição do problema, funcionalidades, restrições. Pode ser:
- Texto direto no argumento: `"sistema de agendamento para clínicas"`
- Arquivo: `--input requisitos.md`

## Saída

Documento de arquitetura completo contendo:
- **Decisões Arquiteturais (ADRs)** — contexto, decisão, consequências
- **Diagrama C4** (nível 1-2: contexto e containers)
- **Schema de Dados** — entidades, relacionamentos, índices
- **Contratos de API** — endpoints, payloads, versionamento
- **Fluxos de Usuário** — jornadas, protótipos de navegação
- **Quality Gate** — veredito PASS/FAIL do Revisor Técnico

## Quality Gate

O Revisor Técnico emite veredito PASS/FAIL. Se FAIL, o documento precisa de correções antes de seguir para implementação.

## Uso

```bash
# Briefing direto
python .hermes/skills/cp-arquitetura/scripts/run.py "sistema de agendamento para clínicas"

# Briefing de arquivo
python .hermes/skills/cp-arquitetura/scripts/run.py --input requisitos.md

# Salvar saída em arquivo específico
python .hermes/skills/cp-arquitetura/scripts/run.py "app de estoque" --output docs/arquitetura.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-arquitetura/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-arquitetura/scripts/run.py \
  "sistema de agendamento para clínicas de estética com agendamento online, \
   gestão de agenda da esteticista, relatórios de faturamento para a dona, \
   e lembretes automáticos por WhatsApp. Precisa ser web, multi-clínica, \
   com planos de assinatura mensal."
```

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.
