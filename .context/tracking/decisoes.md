# Registro de Decisões (ADRs) — Core Product Skills

> Cada decisão importante é registrada aqui com contexto e justificativa.

---

## ADR-0001 — Fonte de verdade em `.context/`

**Data**: 2026-08-18 · **Status**: Aceita

**Contexto**: O contexto do projeto se espalhava por `.hermes/` e `.claude/`,
poluindo o repositório e amarrando a documentação a um agente específico.

**Decisão**: Todo contexto é lido e escrito em `.context/`. `CLAUDE.md` e `AGENT.md`
na raiz são apenas ponteiros. É proibido criar `.hermes/`/`.claude/` para contexto.

**Consequências**: Documentação portável entre agentes; um único lugar a consultar.
`docs/` continua existindo para documentação voltada a humanos — em caso de
divergência, `.context/` prevalece.

---

## ADR-0002 — `cp-full-dev` fundido no `cp-orquestrador`

**Data**: anterior a 2026-08-18 · **Status**: Aceita

**Contexto**: O pipeline NEXUS (7 fases, 39 agentes) vivia numa skill separada,
acionada pelo orquestrador via subprocess — um hop extra e duas superfícies para
manter em sincronia.

**Decisão**: O NEXUS roda nativamente no orquestrador via `NexusExecutor`; a skill
`cp-full-dev` foi eliminada. O acesso é pelo modo `full-dev`.

**Consequências**: Menos indireção e detecção automática de modo (full/sprint/micro).
Em troca, o `run.py` do orquestrador ficou maior e concentra mais responsabilidade.

---

## ADR-0003 — Resolução de LLM provider-agnostic

**Data**: anterior a 2026-08-18 · **Status**: Aceita

**Contexto**: Sem `llm=` explícito, o CrewAI cai no default OpenAI e falha com
`OPENAI_API_KEY is required` mesmo com outro provider configurado.

**Decisão**: `skills/_shared/llm.py` resolve o LLM na ordem: env vars do agente →
`.env` do projeto → detecção por chave de provider → default
`gemini/gemini-2.5-flash`. Toda skill usa `build_crew_llm()`.

**Consequências**: As skills funcionam com o LLM do agente hospedeiro (Hermes ou
Claude) sem alteração de código. `_shared` precisa ser propagado para a **raiz** de
skills de cada agente, não para a categoria.

---

## ADR-0004 — Comunicação entre skills por subprocess + arquivos

**Data**: anterior a 2026-08-18 · **Status**: Aceita

**Contexto**: O orquestrador precisa acionar 14 outras skills.

**Decisão**: Acionamento por `subprocess.run` com lista de argumentos (sem
`shell=True`), passando contexto por arquivo (`_ctx_<fase>.txt`) e recebendo
artefatos em `outputs/pipeline_<timestamp>/`.

**Consequências**: Cada skill permanece self-contained e instalável isoladamente,
e uma skill que trave não derruba o orquestrador (timeout de 600s/fase). Em troca,
o contrato CLI vira acoplamento implícito — daí o metadado `invoke` (e o DT-03,
que propõe validá-lo automaticamente).

---

## ADR-0005 — Instalação por cópia destrutiva

**Data**: anterior a 2026-08-18 · **Status**: Aceita

**Contexto**: Cópias instaladas divergiam do repositório quando editadas no destino.

**Decisão**: `install.sh` faz `rm -rf "$dst"` antes de copiar; `__pycache__/` e
`outputs/` são removidos do destino após a cópia.

**Consequências**: A instalação é sempre um espelho fiel do repositório e edições
locais são descartadas por design. Risco: apontar `HERMES_SKILLS_DIR`/
`CLAUDE_SKILLS_DIR` para um diretório com conteúdo próprio apaga esse conteúdo.

---

## ADR-0006 — Auto-detecção de modo em vez de flag opcional

**Data**: anterior a 2026-08-18 · **Status**: Aceita

**Contexto**: Modos alternativos de skill controlados por flag opcional com
`default=False` nunca eram acionados — o LLM chama a skill por function calling e
decide os parâmetros sozinho, sem "lembrar" do flag.

**Decisão**: O modo correto é **detectado** a partir do conteúdo da entrada, não
declarado por flag.

**Consequências**: Skills funcionam sem instrução extra ao LLM. Exige heurística de
detecção explícita e testada — e um fallback claro, para evitar cair em template
genérico sem sinal de que a detecção falhou.
