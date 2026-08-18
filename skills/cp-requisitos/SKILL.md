---
name: cp-requisitos
description: "Engenharia de Requisitos — cria uma crew CrewAI com Analista de Negócios, Especificador, Validador e PO Proxy para elicitar, especificar, validar e priorizar requisitos de software. Use quando o usuário disser 'levantar requisitos', 'especificar', 'documentar requisitos', 'fazer análise de negócio', 'criar user stories', ou precisar transformar um briefing em documento de requisitos."
---

# cp-requisitos — Engenharia de Requisitos

Cria uma crew CrewAI com agentes especializados para executar o ciclo completo de engenharia de requisitos:

1. **Analista de Negócios** — Elicitação: entrevista o briefing, descobre regras de negócio, stakeholders, riscos
2. **Especificador de Requisitos** — Especificação: user stories, casos de uso, critérios de aceitação (BDD), requisitos não-funcionais
3. **Validador de Requisitos** — Validação: verifica completude, consistência, clareza, testabilidade, viabilidade
4. **Product Owner (Proxy)** — Priorização: MoSCoW, definição de MVP, dependências

## Agentes

| Agente | Função |
|--------|--------|
| Analista de Negócios | Entrevista stakeholders, descobre regras de negócio implícitas |
| Especificador de Requisitos | Redige user stories, casos de uso, critérios de aceitação |
| Validador de Requisitos | Verifica consistência, completude, viabilidade |
| Product Owner (Proxy) | Prioriza e valida alinhamento com visão do produto |

## Entrada

Briefing do cliente — descrição do problema, domínio, necessidades. Pode ser:
- Texto direto no argumento: `"sistema de agendamento para clínicas"`
- Arquivo: `--input briefing.txt`

## Saída

Documento de requisitos completo contendo:
- Análise de negócio (stakeholders, regras, riscos)
- Épicos e features
- User stories com critérios de aceitação (BDD)
- Casos de uso (fluxo principal + alternativos)
- Regras de negócio formais
- Requisitos não-funcionais
- Backlog priorizado (MoSCoW)
- Sugestão de MVP

## Quality Gate

O Validador de Requisitos emite veredito PASS/FAIL. Se FAIL, o documento precisa de correções antes de seguir para a próxima fase.

## Uso

```bash
# Briefing direto
python .hermes/skills/cp-requisitos/scripts/run.py "sistema de agendamento para clínicas"

# Briefing de arquivo
python .hermes/skills/cp-requisitos/scripts/run.py --input briefing.txt

# Salvar saída em arquivo específico
python .hermes/skills/cp-requisitos/scripts/run.py "app de estoque" --output docs/requisitos.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-requisitos/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-requisitos/scripts/run.py \
  "preciso de um sistema para clínica de estética onde a recepcionista agenda clientes, \
   a esteticista vê sua agenda do dia, e a dona da clínica quer relatórios de faturamento. \
   Também precisa enviar lembrete por WhatsApp automaticamente."
```

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.
