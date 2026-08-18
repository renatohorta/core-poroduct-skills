# Requisitos — Core Product Skills

> Disciplina: Engenharia de Requisitos (`cp-requisitos`). Atualizado em 2026-08-18.

## Status

- [x] Concluído (requisitos iniciais derivados do código existente)

## Contexto

Os requisitos abaixo foram **derivados por engenharia reversa** do código e da
documentação existentes (`README.md`, `docs/`, `scripts/`, `skills/`). Requisitos
novos devem entrar por `.context/inbox/iniciativas/`.

## Requisitos funcionais

| ID | Requisito | Prioridade | Estado |
|----|-----------|-----------|--------|
| RF-01 | Manter o código-fonte canônico de todas as skills `cp-*` em `skills/` | Must | ✅ Implementado |
| RF-02 | Propagar as skills para Hermes e Claude via `scripts/install.sh` | Must | ✅ Implementado |
| RF-03 | Permitir instalação seletiva (`--hermes`, `--claude`, `--skill`, `--dry-run`) | Must | ✅ Implementado |
| RF-04 | Resolver o LLM do agente hospedeiro sem acoplar a um provider | Must | ✅ Implementado (`_shared/llm.py`) |
| RF-05 | Expor um ponto único de entrada (`cp-orquestrador`) para todas as skills | Must | ✅ Implementado |
| RF-06 | Aplicar quality gate (PASS/WARN/FAIL) entre fases do pipeline | Must | ✅ Implementado |
| RF-07 | Passar artefatos de uma fase como input da próxima | Must | ✅ Implementado |
| RF-08 | Permitir retomada do pipeline a partir de uma fase (`--start-phase`) | Should | ✅ Implementado |
| RF-09 | Suportar simulação do pipeline sem executar as crews (default / `--dry-run`) | Should | ✅ Implementado |
| RF-10 | Acionar skills diretamente via CLI interativa (`scripts/chat.py`) | Should | ✅ Implementado |
| RF-11 | Usar o Claude Code como LLM das crews via proxy OpenAI-compatível | Could | ✅ Implementado (`scripts/claude_proxy.py`) |
| RF-12 | Inicializar a documentação de um projeto-alvo em `.context/` | Must | ✅ Implementado (`cp-inicializador-doc`) |
| RF-13 | Monitorar backlog e despachar tarefas com feedback bidirecional | Should | ✅ Implementado (`cp-agilista`) |
| RF-14 | Executar o pipeline NEXUS (7 fases, 39 agentes) nativamente | Should | ✅ Implementado (modo `full-dev`) |

## Requisitos não-funcionais

| ID | Requisito | Critério de aceite | Estado |
|----|-----------|--------------------|--------|
| RNF-01 | **Portabilidade** | Zero paths de SO/máquina hardcoded; paths via env var + default relativo | ✅ |
| RNF-02 | **Sem dados pessoais no código** | Zero handles/nomes de máquina fixos nos scripts | ✅ |
| RNF-03 | **Segredos fora do repositório** | `.env` no `.gitignore`; apenas `.env.example` versionado | ✅ |
| RNF-04 | **Self-containment das skills** | Cada `run.py` embute seus agentes; sem diretório externo | ✅ |
| RNF-05 | **Encoding UTF-8 no Windows** | Execução com `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` | ⚠️ Gap conhecido (DT-01) |
| RNF-06 | **Timeout por fase** | 600s por fase no modo `--auto` | ✅ |
| RNF-07 | **Cobertura de testes automatizados** | Suíte executável no repositório | ❌ Gap (DT-02) |

## Backlog priorizado (MoSCoW)

**Must (ainda pendente)**
- Nenhum item aberto — o núcleo funcional está implementado.

**Should**
- DT-01: corrigir `UnicodeEncodeError` do `cp-orquestrador` em console Windows cp1252.
- DT-02: criar suíte de testes (mínimo: smoke test de `--dry-run` de cada skill).
- DT-03: validação automatizada do contrato `invoke` de cada skill.

**Could**
- CI que rode `install.sh --dry-run` + smoke tests a cada push.
- Versionamento semântico das skills e changelog.

**Won't (por ora)**
- Publicação das skills como pacote distribuível (uso interno).

## Regras de negócio

- **RN-01** — Toda alteração de skill é feita **neste repositório**; editar a cópia
  instalada no agente é proibido (será sobrescrita no próximo `install.sh`).
- **RN-02** — `_shared` é helper compartilhado, **não** é skill: vai para a raiz de
  skills do agente, não para a categoria.
- **RN-03** — Toda skill `cp-*` documenta seus artefatos em `.context/docs/`,
  conforme o mapa crew→arquivo definido em `.context/README.md`.

## Decisões

- Requisitos derivados do estado real do código, não de um briefing prévio; o
  `00-vision.md` é a fonte da intenção do produto.
