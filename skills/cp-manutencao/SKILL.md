---
name: cp-manutencao
description: "Manutenção e Evolução de Software — cria uma crew CrewAI com Analista de Bugs, Desenvolvedor de Correção, Engenheiro de Refatoração e Analista de Impacto para corrigir bugs, refatorar código e evoluir sistemas existentes. Use quando o usuário disser 'corrigir bug', 'refatorar', 'melhorar código', 'fazer manutenção', 'evoluir funcionalidade'."
---

# cp-manutencao — Manutenção e Evolução de Software

Cria uma crew CrewAI self-contained com 4 agentes especializados para manutenção e evolução de software: diagnosticar bugs, implementar correções, refatorar código e avaliar impacto de mudanças.

## Agentes

| Agente | Função |
|--------|--------|
| **Analista de Bugs** | Triage, reprodução, diagnóstico de bugs, análise de causa raiz. Debugger experiente que encontra a causa raiz enquanto outros tratam sintomas. |
| **Desenvolvedor de Correção** | Implementa correções mínimas e seguras. Desenvolvedor cirúrgico que corrige exatamente o que está quebrado, nada mais. |
| **Engenheiro de Refatoração** | Melhora código existente sem mudar comportamento. Engenheiro que deixa o código mais limpo do que encontrou, sem introduzir bugs. |
| **Analista de Impacto** | Avalia impacto de mudanças propostas, identifica regressões potenciais. Analista que pensa em todas as consequências antes de uma mudança ser feita. |

## Pipeline

```
[Analista de Bugs] ──► [Analista de Impacto] ──► [Dev Correção / Eng. Refatoração] ──► [Testes de Regressão] ──► Quality Gate
       │                       │                            │                              │                    │
       │  diagnóstico          │  avalia impacto            │  implementa                  │  valida             │  PASS/FAIL
       │  + causa raiz         │  + riscos                  │  correção/refatoração        │  + regressões       │
       └───────────────────────┴────────────────────────────┴──────────────────────────────┴─────────────────────┴──► PASS/FAIL
```

## Modos de Operação

| Modo | Descrição | Agentes envolvidos |
|------|-----------|-------------------|
| `bug-fix` | Corrigir um bug específico | Analista de Bugs → Analista de Impacto → Dev Correção → Testes |
| `refactor` | Refatorar código sem mudar comportamento | Analista de Impacto → Eng. Refatoração → Testes |
| `improvement` | Melhorar código existente (performance, legibilidade) | Analista de Impacto → Eng. Refatoração → Testes |
| `full` | Pipeline completo: diagnóstico → impacto → correção → testes | Todos os 4 agentes |

## Entrada

- **Descrição do bug / solicitação de melhoria** — texto direto ou arquivo via `--input`
- Pode incluir: stack trace, logs de erro, comportamento esperado vs. atual, sugestões de melhoria

## Saída

- Diagnóstico de causa raiz (Analista de Bugs)
- Relatório de análise de impacto com riscos identificados (Analista de Impacto)
- Código corrigido ou refatorado (Dev Correção / Eng. Refatoração)
- Testes de regressão validados
- Quality gate: veredito final PASS/FAIL

## Quality Gate

O Analista de Impacto emite o veredito final após validar os testes de regressão:
- **PASS** ✅ — Bug corrigido / código refatorado, testes passando, sem regressões
- **FAIL** ❌ — Problemas identificados que precisam ser resolvidos antes de considerar concluído

## Uso

```bash
# Corrigir um bug
python .hermes/skills/cp-manutencao/scripts/run.py "o endpoint /login retorna 500 quando o email tem acento" --mode bug-fix

# Refatorar código
python .hermes/skills/cp-manutencao/scripts/run.py "refatorar o módulo de pagamentos para usar Strategy Pattern" --mode refactor

# Melhorar código existente
python .hermes/skills/cp-manutencao/scripts/run.py "melhorar performance da query de relatórios" --mode improvement

# Pipeline completo
python .hermes/skills/cp-manutencao/scripts/run.py "corrigir bug no cálculo de frete e refatorar lógica de descontos" --mode full

# Com arquivo de entrada
python .hermes/skills/cp-manutencao/scripts/run.py --input relatorio_bug.md --mode bug-fix

# Salvar saída em diretório específico
python .hermes/skills/cp-manutencao/scripts/run.py "corrigir validação de CPF" --output ./correcoes

# Apenas ver a estrutura da crew
python .hermes/skills/cp-manutencao/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-manutencao/scripts/run.py \
  "Bug: ao criar um pedido com frete grátis (acima de R$ 200), o sistema aplica \
   desconto duplicado. Stack trace: ValueError no módulo de checkout. \
   Comportamento esperado: desconto aplicado apenas uma vez." \
  --mode bug-fix --output ./fix-frete
```

## Script

O script `scripts/run.py` é self-contained — todos os 4 agentes estão embutidos no próprio código Python. Não depende de diretório externo de agentes.
