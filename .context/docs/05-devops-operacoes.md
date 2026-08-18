# DevOps e Operações — Core Product Skills

> Disciplina: DevOps/Infra (`cp-devops`), Loop autônomo (`cp-goal-loop`).
> Atualizado em 2026-08-18.

## Status

- [x] Concluído (operação atual documentada)
- ⚠️ Sem CI/CD — deploy é manual via `install.sh`

## Modelo de "deploy"

Não há servidor: o "deploy" é a **propagação das skills** deste repositório para os
diretórios de skills dos agentes.

```
skills/  ──[ scripts/install.sh ]──►  Hermes:  $HERMES_SKILLS_DIR/creative/<skill>/
                                  └─►  Claude:  $CLAUDE_SKILLS_DIR/<skill>/
                                       (+ _shared na raiz de skills, em ambos)
```

### Comandos

```bash
./scripts/install.sh                        # Hermes + Claude
./scripts/install.sh --hermes               # apenas Hermes
./scripts/install.sh --claude               # apenas Claude
./scripts/install.sh --skill cp-requisitos  # apenas uma skill
./scripts/install.sh --dry-run              # simula, não copia
```

### Destinos e overrides

| Env var | Default (Windows) | Default (Linux/macOS) |
|---------|-------------------|----------------------|
| `HERMES_SKILLS_DIR` | `%LOCALAPPDATA%\hermes\skills` | `~/.hermes/skills` |
| `CLAUDE_SKILLS_DIR` | `~/.claude/skills` | `~/.claude/skills` |

No Hermes as skills vão para a categoria `creative/`; no Claude ficam flat.
`_shared` **não** é skill — vai para a raiz de skills nos dois destinos.

### Semântica da cópia

`install.sh` faz `rm -rf "$dst"` e recopia: a instalação é **descartável** e sempre
reflete o repositório. Nunca edite a cópia instalada — será perdida.
Após copiar, `__pycache__/` e `outputs/` são removidos do destino.

## Ambiente de execução

| Item | Situação |
|------|----------|
| Runtime | Python 3 (host: 3.14 em Windows) |
| Dependência principal | `crewai` — **não declarada** em manifesto (ver DT-05) |
| Interpretador usado pelo orquestrador | Python do agente hospedeiro (ex.: venv do Hermes) |
| Shell do `install.sh` | bash (Git Bash no Windows) |
| Configuração | `.env` na raiz (template em `.env.example`) |

### Pitfall — encoding no Windows

O console Windows usa cp1252 e quebra na saída UTF-8 das skills. Rode com:

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python skills/cp-orquestrador/scripts/run.py ...
```

Correção definitiva pendente: DT-01.

### Pitfall — relay bash intermitente no Windows

`terminal`/`write_file` podem falhar com
`execvpe(/bin/bash) failed: No such file or directory`. Contorne usando Python puro
(`subprocess`/`open`) via `execute_code`. Ver
`skills/cp-orquestrador/references/windows-wsl-bash-relay-workaround.md`.

## Configuração de LLM

Resolução provider-agnostic (`skills/_shared/llm.py`), nesta ordem:

1. Env vars do agente: `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_PROVIDER`
2. `.env` na raiz do projeto
3. Detecção por chave de provider (`GEMINI_API_KEY`, `OPENAI_API_KEY`, …)
4. Default: `gemini/gemini-2.5-flash`

### Claude Code como LLM das crews

```bash
python scripts/claude_proxy.py --port 8090   # expõe /v1/chat/completions → `claude -p`
python scripts/claude_proxy.py --test        # testa uma chamada
```

```env
LLM_MODEL=openai/claude-sonnet-4
LLM_API_BASE=http://localhost:8090/v1
LLM_API_KEY=<qualquer valor — o proxy ignora, o CrewAI exige>
LLM_PROVIDER=openai
```

> O proxy escuta em `127.0.0.1` e **não tem autenticação** (ver SEC-02).
> `DEFAULT_PORT` no código é 8080, mas o README recomenda 8090 para evitar conflito
> com frontends — passe `--port 8090` explicitamente até DOC-01 ser resolvido.

## Observabilidade

| Sinal | Onde |
|-------|------|
| Log de execução do pipeline | stdout do `run.py` (fase, quality gate, tempo) |
| Artefatos por fase | `skills/cp-orquestrador/outputs/pipeline_<timestamp>/<fase>.md` |
| Relatório estruturado | `.../pipeline_<timestamp>/pipeline_report.json` |
| Progresso de projeto | `.context/tracking/progresso.md` |

Não há métricas agregadas, alertas ou retenção de logs — adequado ao uso local.

## Runbook

| Situação | Ação |
|----------|------|
| Skill não aparece no Claude | Confirmar `~/.claude/skills/<skill>/SKILL.md`; reiniciar o agente |
| Skill não aparece no Hermes | Confirmar `$HERMES_SKILLS_DIR/creative/<skill>/`; recarrega no próximo turno |
| `OPENAI_API_KEY is required` | `.env` sem `LLM_*` — configurar provider correto |
| `UnicodeEncodeError` | Rodar com `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` |
| Fase falhou no `--auto` | Corrigir e retomar com `--start-phase <fase>` |
| `Permissão negada` no install | `chmod +x scripts/install.sh` (Linux/macOS) |
| Mudança "sem efeito" | Verificar de qual clone do repo o processo está rodando |

## Pendências

- **DT-05** — Sem manifesto de dependências: criar `requirements.txt` fixando
  `crewai` (e transitivas relevantes).
- **DT-06** — Sem CI: adicionar workflow que rode `install.sh --dry-run` + smoke
  tests a cada push.
- **DT-01** — Corrigir encoding UTF-8 na saída do orquestrador (Windows).

## Decisões

- Distribuição por cópia de diretório (não por pacote instalável): mantém o ciclo
  editar→propagar em um comando e sem build.
