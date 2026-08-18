# BUG-03 — Quality gate ignora o exit code: skill que crasha vira "sucesso" [Corrigido]

**Tipo**: Bug · **Severidade**: **Alta** · **Aberto em**: 2026-08-18
**Verificado empiricamente**: sim

## Sintoma

Uma skill que morre com traceback e exit code 1 é aprovada com WARN, e o pipeline
reporta sucesso ao final:

```
$ python cp-orquestrador/scripts/run.py "teste sem llm" --mode bugfix --auto

  ⏱️  0.1s | Quality Gate: WARN
  ⚠️  Fase aprovada com ressalvas: Não foi possível determinar o resultado
  📄 Preview:
  Traceback (most recent call last):
    File "...cp-bug-fix/scripts/run.py", line 17, in <module>
      from crewai import Agent, Task, Crew, Process
  ModuleNotFoundError: No module named 'crewai'

  ✅ Pipeline concluído com sucesso!          ← reporta SUCESSO
     Fases: 1 | ✅ 0 | ⚠️  1 | ❌ 0 | ⏭️  0
```

## Causa

`_check_quality_gate(self, crew_key, output_text)` recebe **apenas o texto** da
saída e conta palavras-chave. O `returncode` do `subprocess.run` nunca é lido —
`grep -n "returncode" run.py` retorna zero ocorrências no orquestrador.

Um crash não contém nenhuma das `fail_keywords` (`FAIL`, `FALHOU`, `REPROVADO`,
`BLOQUEADO`, `CRÍTICO`…), então cai no ramo default → WARN → pipeline continua.

## Impacto

Num pipeline `full` (8 fases), a fase 1 pode crashar, todas as seguintes rodarem
sobre um artefato vazio, e o relatório final dizer "concluído com sucesso". O
quality gate — a principal garantia do orquestrador — não protege contra o modo
de falha mais comum.

## Correção proposta

`returncode != 0` é FAIL incondicional, antes de qualquer análise de texto:

```python
def _check_quality_gate(self, crew_key, output_text, returncode=0):
    if returncode != 0:
        return {"status": "FAIL",
                "detail": f"Skill terminou com exit code {returncode}"}
    ...
```

E na chamada (linha ~1193): `gate = self._check_quality_gate(ck, output, result.returncode)`.

## Critério de aceite

- Fase cuja skill sai com código ≠ 0 recebe FAIL e interrompe o pipeline.
- O relatório final não reporta sucesso quando alguma fase falhou.


---

## Resolucao

**Corrigido em 2026-08-18**, propagado aos agentes via `./scripts/install.sh`.
Verificado empiricamente com o harness de duas camadas (sem `crewai` / com
`crewai` stub e sem chave). Ver `.context/docs/04-qualidade-qa.md`.
