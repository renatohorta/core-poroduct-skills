---
name: cp-seguranca
description: "Segurança de Software — cria uma crew CrewAI com Analista de Segurança, Penetration Tester, Especialista em Compliance e Engenheiro de Correção para analisar vulnerabilidades, testar invasões e garantir conformidade. Use quando o usuário disser 'auditar segurança', 'fazer pentest', 'verificar vulnerabilidades', 'garantir compliance', 'OWASP'."
---

# cp-seguranca — Segurança de Software

Cria uma crew CrewAI com agentes especializados para executar o ciclo completo de segurança de software:

1. **Analista de Segurança** — Revisa código e arquitetura contra OWASP Top 10, identifica vulnerabilidades
2. **Penetration Tester** — Executa testes de invasão automatizados, pensa como atacante
3. **Especialista em Compliance** — Verifica conformidade (LGPD, GDPR, SOC2, ISO 27001)
4. **Engenheiro de Correção** — Implementa correções de vulnerabilidades encontradas

## Agentes

| Agente | Função |
|--------|--------|
| Analista de Segurança | Revisa código e arquitetura contra OWASP Top 10, encontra vulnerabilidades onde ninguém mais olha |
| Penetration Tester | Executa testes de invasão automatizados, pensa como atacante para proteger o sistema |
| Especialista em Compliance | Verifica conformidade com LGPD, GDPR, SOC2, ISO 27001 e regulamentações aplicáveis |
| Engenheiro de Correção | Implementa correções de vulnerabilidades sem introduzir novas |

## Entrada

Código-fonte + descrição da arquitetura. Pode ser:
- Texto direto no argumento: `"sistema de login com JWT"`
- Arquivo: `--input codigo.txt`

## Saída

Relatório de segurança completo contendo:
- Análise de vulnerabilidades (OWASP Top 10)
- Resultados de testes de penetração
- Verificação de compliance (LGPD/GDPR/SOC2)
- Correções implementadas
- Quality gate: PASS/FAIL (zero vulnerabilidades críticas/altas)

## Quality Gate

O Analista de Segurança re-analisa o código pós-correção e emite veredito PASS/FAIL.
Se FAIL, o ciclo de correção deve ser repetido até que não haja vulnerabilidades críticas ou altas.

## Modos

| Modo | Gatilho | Agentes |
|------|---------|---------|
| **code-review** | Revisão de código estática | Analista de Segurança |
| **pentest** | Teste de penetração | Penetration Tester |
| **compliance** | Verificação de conformidade | Especialista em Compliance |
| **full** | Ciclo completo (default) | Todos os 4 agentes |

## Uso

```bash
# Ciclo completo
python .hermes/skills/cp-seguranca/scripts/run.py "sistema de login com JWT e autenticação 2FA"

# Modo específico
python .hermes/skills/cp-seguranca/scripts/run.py --mode pentest "API REST com upload de arquivos"

# Com arquivo de entrada
python .hermes/skills/cp-seguranca/scripts/run.py --input src/app.py --mode full

# Salvar saída em arquivo específico
python .hermes/skills/cp-seguranca/scripts/run.py "sistema de pagamento" --output relatorio.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-seguranca/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-seguranca/scripts/run.py \
  "API REST em Django que gerencia dados de pacientes. \
   Tem autenticação JWT, upload de exames em PDF, \
   e compartilhamento de prontuários entre médicos. \
   Precisa estar em conformidade com LGPD."
```

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.
