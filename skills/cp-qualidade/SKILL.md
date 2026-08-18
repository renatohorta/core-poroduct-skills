---
name: cp-qualidade
description: "Garantia da Qualidade de Software — cria uma crew CrewAI com Auditor, Analista de Métricas, Engenheiro de Melhoria Contínua e Validador de Artefatos para auditar processos, medir métricas e garantir conformidade. Use quando o usuário disser 'auditar qualidade', 'medir métricas', 'verificar processo', 'garantir qualidade'."
---

# cp-qualidade — Garantia da Qualidade de Software

Cria uma crew CrewAI self-contained com 4 agentes especializados para auditar processos, medir métricas de qualidade, propor melhorias contínuas e validar artefatos de software.

## Agentes

| Agente | Função |
|--------|--------|
| **Auditor de Qualidade** | Revisa se processos estão sendo seguidos, verifica artefatos obrigatórios, aplica checklist rigoroso |
| **Analista de Métricas** | Coleta e analisa métricas (cobertura de testes, bugs, débito técnico, velocity) — transforma números em insights |
| **Engenheiro de Melhoria Contínua** | Propõe e implementa melhorias no processo — aplica Kaizen e Lean em times de software |
| **Validador de Artefatos** | Verifica se todos os artefatos obrigatórios existem e estão completos — não deixa passar documentação faltando |

## Pipeline

```
1. Auditoria de processo e artefatos (Auditor + Validador)
   ├── Auditor: verifica se processos estão sendo seguidos
   └── Validador: verifica se artefatos obrigatórios existem e estão completos

2. Análise de métricas (Analista de Métricas)
   └── Coleta métricas, calcula indicadores, identifica tendências

3. Propostas de melhoria (Eng. Melhoria Contínua)
   └── Com base em auditoria + métricas, propõe melhorias priorizadas

4. Quality Gate — Relatório final com veredito (todos os agentes)
   └── Compila tudo e emite PASS/FAIL com recomendações
```

## Quality Gate

- **Processos seguidos:** 100% dos processos obrigatórios verificados
- **Artefatos completos:** 100% dos artefatos obrigatórios presentes e completos
- **Cobertura de testes:** >= 80%
- **Débito técnico:** < 20% da base de código
- **Bugs críticos:** 0 em produção
- **Velocity:** dentro da média histórica do time
- **Veredito:** PASS (tudo ok) ou FAIL (algo abaixo do mínimo)

## Entrada

- Descrição do projeto/sistema sendo auditado
- Artefatos de todas as fases (requisitos, design, código, testes, deploy)
- Métricas disponíveis (opcional)
- Modo: audit, metrics, improvement, ou full

## Saída

Relatório de qualidade completo contendo:
- Resultados da auditoria de processo
- Checklist de artefatos verificados
- Métricas de qualidade (cobertura, bugs, débito técnico, velocity)
- Propostas de melhoria priorizadas
- Veredito final PASS/FAIL com justificativa

## Uso

```bash
# Modo completo (auditoria + métricas + melhoria)
python .hermes/skills/cp-qualidade/scripts/run.py "sistema de agendamento de consultas"

# Modo específico
python .hermes/skills/cp-qualidade/scripts/run.py "API de pagamentos" --mode audit

# Com arquivo de entrada
python .hermes/skills/cp-qualidade/scripts/run.py --input descricao.md

# Salvar relatório em arquivo
python .hermes/skills/cp-qualidade/scripts/run.py "app mobile" --output relatorio-qualidade.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-qualidade/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-qualidade/scripts/run.py \
  "sistema de agendamento de consultas médicas com autenticação, \
   CRUD de pacientes, agendamento com slots de horário, \
   e notificações por email" \
  --mode full \
  --output relatorio-qualidade.md
```

## Script

O script `scripts/run.py` é self-contained — todos os 4 agentes estão embutidos no próprio código Python. Não depende de diretório externo de agentes.
