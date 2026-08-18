# BUG-04 — `"OK"` casado como substring gera PASS falso [Corrigido]

**Tipo**: Bug · **Severidade**: Média · **Aberto em**: 2026-08-18
**Relacionado**: BUG-03 (mesma função)

## Sintoma

`_check_quality_gate` testa `kw in output_upper` — **substring**, não palavra. A
`pass_keyword` `"OK"` aparece dentro de palavras comuns em mensagens de erro:

| Saída da skill | pass | fail | Gate |
|----------------|------|------|------|
| `Erro: invalid API t**ok**en` | 1 | 0 | **PASS** ❌ |
| `Br**ok**en pipeline` | 1 | 0 | **PASS** ❌ |
| `ModuleNotFoundError: No module named crewai` | 0 | 0 | WARN |
| `Traceback (most recent call last)` | 0 | 0 | WARN |

Qualquer erro de autenticação que mencione "token" — o caso mais frequente quando
falta credencial de LLM — é classificado como **sucesso**.

## Correção proposta

Casar por limite de palavra e não contar keywords curtas como substring:

```python
import re
def _count(keywords, text):
    return sum(1 for kw in keywords
               if re.search(rf"\b{re.escape(kw)}\b", text))
```

Considerar também remover `"OK"` da lista: é curta demais para ser sinal
confiável de quality gate.

## Critério de aceite

- `"invalid API token"` não produz PASS.
- `"Testes OK"` continua produzindo PASS.


---

## Resolucao

**Corrigido em 2026-08-18**, propagado aos agentes via `./scripts/install.sh`.
Verificado empiricamente com o harness de duas camadas (sem `crewai` / com
`crewai` stub e sem chave). Ver `.context/docs/04-qualidade-qa.md`.
