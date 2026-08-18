# Qualidade e QA — Core Product Skills

> Disciplinas: Testes (`cp-testes`), Qualidade (`cp-qualidade`), Documentação
> (`cp-documentacao`), Bug-fix (`cp-bug-fix`). Atualizado em 2026-08-18.

## Status

- [x] Concluído (diagnóstico inicial)
- ⚠️ **Sem testes automatizados** — maior gap de qualidade do repositório

## Estado atual (2026-08-18, após a rodada de correções)

| Métrica | Valor |
|---------|-------|
| Skills `cp-*` | 15 |
| Testes automatizados | **158** (+1 skip: daemon do agilista) |
| Tempo da suíte | ~2min, sem nenhuma credencial |
| Pipeline de CI | ✅ GitHub Actions (Linux 3.12/3.13 bloqueante, Windows informativo) |
| Manifesto de dependências | ✅ `requirements.txt` (crewai>=1.15,<2) + `requirements-dev.txt` |
| Linter/formatter | ❌ Nenhum |

### Cobertura da suíte

| Arquivo | O que garante |
|---------|---------------|
| `tests/test_smoke.py` | `--help` em toda skill (mesmo sem `crewai`); `--dry-run` sem credencial; exit codes 2/3 com mensagem acionável |
| `tests/test_contrato_invoke.py` | `invoke` × `argparse` — inclusive executando a linha que o orquestrador montaria |
| `tests/test_quality_gate.py` | Regressão de BUG-03 e BUG-04 |
| `tests/test_claude_proxy_auth.py` | Autenticação do proxy e bind em localhost |
| `tests/test_higiene.py` | Segredos e paths de máquina em arquivo versionado |

O teste `test_comando_montado_pelo_orquestrador_e_aceito` foi validado
reintroduzindo o BUG-05: falhou apontando o comando exato e a mensagem da skill.

**O que a suíte não cobre**: a lógica interna das crews (montagem de tasks,
encadeamento entre agentes) e qualquer comportamento que dependa de resposta de
LLM — deliberado, por serem caros e não-determinísticos.

## Estratégia de teste — implementada



Como as skills são scripts CLI self-contained, o teste de maior retorno é o
**smoke test de contrato CLI** — barato, determinístico e pega a classe de bug
mais frequente (skill chamada com flag que ela rejeita).

| Nível | Escopo | Como |
|-------|--------|------|
| **Smoke (P0)** | Cada skill responde a `--help` e a `--dry-run` com exit 0 | `pytest` parametrizado sobre `skills/*/scripts/run.py` |
| **Contrato (P0)** | O `invoke` declarado no orquestrador bate com o `argparse` real da skill | Parsear `add_argument` de cada `run.py` e comparar com `CREWS[...]['invoke']` |
| **Integração (P1)** | `install.sh --dry-run` lista todas as skills e o `_shared` | Assert na saída |
| **Unitário (P1)** | `_shared/llm.py`: ordem de resolução e mapeamento de provider | `pytest` com `monkeypatch` de env |
| **E2E (P2)** | Um pipeline curto (`--mode inicializador-doc --auto`) em tempdir | Assert na estrutura `.context/` gerada |

## Checklist de qualidade por mudança

Antes de considerar uma alteração de skill concluída:

- [ ] `python skills/cp-<nome>/scripts/run.py --help` retorna 0
- [ ] `python .../run.py "<briefing>" --dry-run` mostra o plano esperado
- [ ] Se o contrato CLI mudou, `CREWS[...]['invoke']` foi atualizado no orquestrador
- [ ] `./scripts/install.sh --dry-run` continua listando a skill
- [ ] `git status --short` conferido antes do commit (evita commit parcial)
- [ ] Documentação da disciplina atualizada em `.context/docs/`

## Execução sem LLM configurada — auditoria de 2026-08-18

Pergunta auditada: **as skills rodam sem uma LLM configurada?**

Método: cada skill executada com `--help` e `--dry-run` em ambiente com as 15
variáveis de credencial removidas (`LLM_*`, `GEMINI_API_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, …) e sem `.env` na raiz. Depois repetido com um stub
instrumentado de `crewai` no `PYTHONPATH`, para separar "falta a lib" de
"falta a chave".

### Resultado — antes × depois das correções

| Cenário | Antes | Depois |
|---------|-------|--------|
| `--help` sem `crewai` | 3/15 skills funcionam | **15/15** ✅ |
| `--dry-run` sem `crewai` | traceback `ModuleNotFoundError` | mensagem acionável, exit 3 |
| `--dry-run` com `crewai`, sem chave | funciona | funciona (inalterado) ✅ |
| Execução real sem chave | 4–5 agentes com `llm=None` chegam ao `kickoff()` **sem aviso** | falha antes de montar a crew, exit 2, mensagem acionável |
| Skill crasha durante o pipeline | gate WARN → "✅ Pipeline concluído com sucesso" | gate **FAIL** → pipeline interrompe |

### Veredito por skill (mantém-se após as correções)

| Skill | Roda sem LLM? | Observação |
|-------|---------------|------------|
| `cp-inicializador-doc` | ✅ **Sim, integralmente** | Python puro, determinístico — nem importa `crewai` |
| `cp-agilista` | ✅ **Sim, integralmente** | Python puro; o daemon/kanban não usa LLM |
| `cp-orquestrador` | ⚠️ **Parcial** | `--dry-run` (plano) e `--auto` funcionam; o modo simulação (default) exige LLM |
| as outras 12 | ❌ **Não, por design** | Uma crew CrewAI **é** uma chamada de LLM |

A dependência de LLM nas 12 skills é inerente e não foi removida — o que mudou é
que agora elas **falham bem**: `--help` sempre funciona, `--dry-run` permite
inspecionar a crew sem credencial, e a falha diz o que fazer em vez de exibir um
traceback.

### Limitação conhecida

`--dry-run` **sem `crewai` instalado** não monta a crew (sai com código 3 e
instrução de instalação). Montar a crew exige as classes reais do CrewAI. Só
`--help` é garantido sem a lib.

### Códigos de saída padronizados

| Código | Significado |
|--------|-------------|
| 0 | Sucesso |
| 1 | Erro de uso (briefing ausente, argumento inválido) |
| **2** | Nenhum LLM configurado (`require_llm`) |
| **3** | `crewai` não instalado (`require_crewai`) |

## Bugs e defeitos conhecidos

| ID | Defeito | Severidade | Estado |
|----|---------|-----------|--------|
| DOC-01 | Porta do `claude_proxy.py` divergente entre README (8090) e código (8080) | Baixa | 🔵 Aberto |
| ~~BUG-03~~ | ~~Quality gate ignora exit code~~ | Alta | ✅ Corrigido 2026-08-18 |
| ~~BUG-04~~ | ~~`"OK"` como substring gera PASS falso~~ | Média | ✅ Corrigido 2026-08-18 |
| ~~BUG-05~~ | ~~Modo `goal-loop` quebrado (falta `--steps`)~~ | Média | ✅ Corrigido 2026-08-18 |
| ~~DT-01~~ | ~~`UnicodeEncodeError` no console Windows~~ | Média | ✅ Corrigido 2026-08-18 |

Itens resolvidos em `.context/inbox/processed/`; abertos em `.context/inbox/`.

## Pitfalls duráveis (lições registradas)

1. **Nunca assuma o contrato CLI de uma skill** — `--output` não é universal;
   briefing nem sempre é posicional. Consulte
   `skills/cp-orquestrador/references/skills-cli-inventory.md`.
2. **`git status --short` antes de commitar** — commits saem incompletos quando
   nem todos os arquivos foram staged.
3. **Não dependa de flag opcional que o LLM precise lembrar de setar** — o modo
   correto deve ser auto-detectado do contexto.
4. **"Código certo mas sem efeito no app"** — confirme de qual clone do repositório
   o processo está rodando antes de debugar a lógica.
5. **Roadmap mente** — cruze o estado declarado contra o código real antes de
   reportar "o que falta".

## Documentação

| Artefato | Local | Estado |
|----------|-------|--------|
| Visão geral e instalação rápida | `README.md` | ✅ Atualizado |
| Instalação detalhada | `docs/INSTALLATION.md` | ✅ |
| Arquitetura | `docs/ARCHITECTURE.md` | ✅ |
| Catálogo de skills | `docs/SKILLS.md` | ✅ |
| Contexto canônico | `.context/` | ✅ Inicializado nesta rodada |
| Ponteiros para agentes | `CLAUDE.md`, `AGENT.md` | ✅ |

> Nota: `docs/` (documentação **do repositório**, voltada a humanos) e `.context/`
> (contexto **do projeto**, fonte de verdade para agentes) coexistem. `.context/`
> prevalece em caso de divergência.

## Decisões

- Priorizar smoke + contrato antes de qualquer teste de crew: testar o LLM em si é
  caro, não-determinístico e não pega os bugs que de fato ocorrem.


## Artefato — Correção de Bug (NEXUS-Micro) (2026-08-18 13:26)

```

Traceback (most recent call last):
  File "C:\Users\renat\.claude\skills\cp-bug-fix\scripts\run.py", line 17, in <module>
    from crewai import Agent, Task, Crew, Process
ModuleNotFoundError: No module named 'crewai'

```


## Artefato — Correção de Bug (NEXUS-Micro) (2026-08-18 13:36)

```

[X] crewai nao instalado - necessario para executar esta skill.
    Instale com:  pip install crewai
    (--help continua funcionando sem a lib.)


```
