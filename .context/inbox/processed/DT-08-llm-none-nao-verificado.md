# DT-08 — `build_crew_llm()` retorna None e ninguém verifica [Corrigido]

**Tipo**: Débito técnico / Bug · **Prioridade**: Alta · **Aberto em**: 2026-08-18
**Verificado empiricamente**: sim (13/13 skills que usam LLM)

## Contexto

`skills/_shared/llm.py` documenta explicitamente o contrato:

> "Retorna None se o crewai não estiver instalado ou se não houver chave
> configurada (**a skill pode então avisar** em vez de cair no default OpenAI)."

**Nenhuma skill implementa esse "avisar".** O padrão em todas as 13 é:

```python
_crew_llm = build_crew_llm()      # pode ser None
return Agent(..., llm=_crew_llm)  # nunca verificado
```

Busca por qualquer checagem de `_crew_llm` fora da atribuição e do `llm=`:
zero ocorrências.

## Evidência

Com `crewai` presente (stub instrumentado) e **sem chave**, cada skill:

| Skill | agentes criados | com `llm=None` | `LLM()` construído | chegou ao `kickoff()` |
|-------|----------------|----------------|--------------------|-----------------------|
| cp-requisitos | 4 | 4 | não | **sim** |
| cp-arquitetura | 5 | 5 | não | **sim** |
| cp-implementacao | 5 | 5 | não | **sim** |
| cp-testes | 5 | 5 | não | **sim** |
| cp-seguranca / devops / documentacao / qualidade / bug-fix / competitive-analysis / manutencao / orquestrador | 4 | 4 | não | **sim** |

Ou seja: 100% dos agentes ficam sem LLM e a execução avança até o `kickoff()`
**sem um único aviso**. Em CrewAI real, `Agent(llm=None)` cai no default OpenAI —
exatamente o `OPENAI_API_KEY is required` que o helper existe para evitar.

## Correção proposta

Falhar cedo, com mensagem que diz o que fazer. Em `build_crew()` de cada skill
(ou num helper novo `require_llm()` em `_shared/llm.py`):

```python
from _shared.llm import build_crew_llm, get_llm_config

def require_llm():
    llm = build_crew_llm()
    if llm is None:
        cfg = get_llm_config()
        print("❌ Nenhum LLM configurado.")
        print(f"   Modelo resolvido: {cfg['model']} (sem chave)")
        print("   Configure LLM_API_KEY/LLM_MODEL no ambiente ou em .env")
        print("   (veja .env.example). Use --dry-run para inspecionar sem LLM.")
        sys.exit(2)
    return llm
```

Chamar no início da execução real — **nunca** em `--dry-run`, que deve continuar
funcionando sem credencial.

## Critério de aceite

- Sem chave, a skill sai com código 2 e mensagem acionável, antes de montar a crew.
- Com `--dry-run`, a skill continua funcionando sem chave.


---

## Resolucao

**Corrigido em 2026-08-18**, propagado aos agentes via `./scripts/install.sh`.
Verificado empiricamente com o harness de duas camadas (sem `crewai` / com
`crewai` stub e sem chave). Ver `.context/docs/04-qualidade-qa.md`.
