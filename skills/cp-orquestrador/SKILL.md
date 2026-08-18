---
name: cp-orquestrador
description: "Orquestrador da Fábrica de Software — coordena todo o pipeline de desenvolvimento executando crews especializadas em sequência, gerenciando artefatos entre fases e decidindo avanço/retrocesso baseado em quality gates. Use quando o usuário disser 'executar pipeline completo', 'fazer fábrica de software', 'entregar produto', 'coordenar desenvolvimento', 'gerenciar projeto'."
---

# cp-orquestrador — Orquestrador da Fábrica de Software

Orquestrador central do pipeline NEXUS. Coordena a execução de todas as crews especializadas (`cp-*`) em sequência, gerencia a passagem de artefatos entre fases, aplica quality gates e decide avanço/retrocesso.

## Pipeline Completo (9 fases)

```
[Requisitos] ──► [Arquitetura] ──► [Implementação] ──► [Testes] ──► [Segurança] ──► [DevOps] ──► [Documentação] ──► [Qualidade] ──► [Entrega]
      │                │                  │               │             │             │              │                │              │
  cp-requisitos   cp-arquitetura    cp-implementacao   cp-testes   cp-seguranca  cp-devops   cp-documentacao  cp-qualidade   Entrega
      │                │                  │               │             │             │              │                │              │
  [Quality Gate]  [Quality Gate]    [Quality Gate]   [Quality Gate] [Quality Gate] [Quality Gate] [Quality Gate] [Quality Gate]  [Entrega]
```

## Todas as skills cp-* acionáveis

O orquestrador é o **ponto único de entrada** para TODAS as skills `cp-*`. Além das 8
fases do pipeline, ele aciona as 6 skills complementares via modos dedicados:

| Modo | Skill | O que faz |
|------|-------|-----------|
| `bugfix` | `cp-bug-fix` | Corrige bugs (Developer → QA → Evidence Collector, máx. 3 retries) |
| `competitive` | `cp-competitive-analysis` | Inteligência competitiva (mercado, concorrentes, pricing, estratégia) |
| `full-dev` | **nativo** (merge de `cp-full-dev`) | Pipeline NEXUS completo (Discovery → ... → Operate), agora embutido no orquestrador |
| `goal-loop` | `cp-goal-loop` | Loop autônomo de tentativa-e-correção até atingir sucesso |
| `manutencao` | `cp-manutencao` | Manutenção/evolução (bug-fix, refactor, improvement, full) |
| `agilista` | `cp-agilista` | Esteira de execução: monitora backlog, despacha tarefas e gerencia feedback bidirecional (dúvidas, impedimentos, retomada) |
| `inicializador-doc` | `cp-inicializador-doc` | Inicializa a documentação: centraliza o contexto em `.context/` (fonte de verdade única) e cria ponteiros CLAUDE.md/AGENT.md |

> **Nota:** o `cp-full-dev` foi **fundido** no orquestrador. O pipeline NEXUS (7 fases,
> 39 agentes) agora roda nativamente via `NexusExecutor` — não depende mais da skill
> `cp-full-dev` (que foi eliminada). O modo `full-dev` executa o NEXUS em memória, com
> detecção automática de modo (full/sprint/micro) e quality gates por fase.

Cada skill é acionada respeitando sua interface CLI (metadado `invoke` no `CREWS`):
- `briefing_arg`: `positional` (arg posicional), `goal` (`--goal`, ex. goal-loop),
  `input` (`--input`, fases do pipeline), `daemon` (sem briefing posicional —
  monta `--daemon`, ex. agilista) ou `dir` (monta `--dir <cwd>`, ex. inicializador-doc)
- `output`: `True` se a skill aceita `--output`, `False` caso contrário

> ⚠️ NÃO assuma que toda skill aceita `--output` nem que o briefing entra como
> posicional — cada skill tem contrato CLI próprio. Ver
> `references/skills-cli-inventory.md` para o inventário completo por skill e o
> snippet de verificação. Pitfalls: `cp-goal-loop` só recebe briefing via `--goal`;
> `cp-bug-fix`/`cp-goal-loop`/`cp-agilista` rejeitam `--output`; `cp-agilista` não
> tem argumento posicional (só `--daemon`/`--duvida`/`--impedimento`/`--resume`);
> `cp-inicializador-doc` não tem posicional (só `--dir`/`--dry-run`).

## Regra de documentação em `.context/`

Toda skill `cp-*` documenta seus artefatos na estrutura **`.context/`** (fonte de
verdade única do projeto). O `cp-inicializador-doc` cria a estrutura; o orquestrador
escreve automaticamente o artefato de cada fase no arquivo de disciplina correto:

| Crew | Arquivo em `.context/docs/` |
|------|------------------------------|
| requisitos, competitive-analysis | `01-requisitos.md` |
| arquitetura, implementacao, manutencao | `02-arquitetura.md` |
| seguranca | `03-seguranca-lgpd.md` |
| testes, documentacao, qualidade, bug-fix | `04-qualidade-qa.md` |
| devops, goal-loop | `05-devops-operacoes.md` |
| agilista | `06-kanban.md` |

O `cp-agilista` também gera `.context/docs/06-kanban.md` com o estado do kanban
via `--doc`.

### Como adicionar uma skill nova ao orquestrador

Para conectar uma nova skill `cp-*` ao fluxo, edite `scripts/run.py` em 4 pontos:
1. **`SKILL_PATHS`** — adicione `"<chave>": SKILLS_DIR / "cp-<nome>" / "scripts" / "run.py"`
2. **`CREWS`** — adicione a crew com `name`, `skill`, `agents`, `inputs`, `outputs`,
   `quality_gate`, `cli_args` e o metadado `invoke` (o `briefing_arg` DEVE refletir
   como a skill realmente recebe o briefing — teste com `_build_cli_args`).
3. **`MODOS`** — adicione o modo com `crews: ["<chave>"]`.
4. **`_build_cli_args`** — se a skill usa um `briefing_arg` novo (ex.: `daemon`),
   adicione o branch correspondente.

Valide com: `python run.py "<briefing>" --mode <modo> --dry-run` (plano) e
`python run.py "<briefing>" --mode <modo> --auto` (execução). Se a skill não aceita
`--output`, o metadado `invoke.output=False` é OBRIGATÓRIO — sem ele o argparse da
skill rejeita o flag e a fase quebra.

Exemplos:
```bash
python run.py "o endpoint /login retorna 500" --mode bugfix --auto
python run.py "SaaS de clínicas; concorrentes: Doctoralia" --mode competitive --auto
python run.py "sistema de agendamento" --mode full-dev --auto
python run.py "deploy em staging funcionando" --mode goal-loop --auto
python run.py "refatorar módulo de pagamentos" --mode manutencao --auto
```

## Agentes

| Agente | Função |
|--------|--------|
| **Orquestrador de Pipeline** | Coordena execução sequencial/paralela das crews. Maestro de orquestra de software que conhece cada instrumento e quando tocar. |
| **Gestor de Artefatos** | Garante que outputs de uma crew viram inputs da próxima, versiona artefatos. Bibliotecário de software que organiza e versiona cada artefato produzido. |
| **Tomador de Decisão** | Decide avançar, pausar, ou retroceder baseado nos quality gates. Gerente de projeto experiente que sabe quando pressionar e quando recuar. |
| **Relator de Progresso** | Gera relatórios de status do pipeline, dashboards, resumos executivos. PM que transforma progresso técnico em relatórios que stakeholders entendem. |

## Modos de Operação

O orquestrador opera em **dois modos**:

### 🧪 Simulação (default)

Usa CrewAI para planejar, simular e documentar o pipeline. Ideal para:
- Planejamento antes de executar
- Apresentação para stakeholders
- Estimar esforço e riscos

### 🚀 Auto (--auto)

Executa as crews reais em sequência, passando artefatos entre fases e aplicando quality gates automaticamente. Ideal para:
- Execução real do pipeline do começo ao fim
- Integração contínua / esteira de deploy
- Uso como "gerente da fábrica" — um comando só

**Como o modo auto funciona:**

```
1. Recebe o briefing
2. Executa cp-requisitos → salva requisitos.md
3. Passa requisitos.md como input para cp-arquitetura
4. Executa cp-arquitetura → salva arquitetura.md
5. Passa arquitetura.md como input para cp-implementacao
6. ... continua até a última fase
7. Se um quality gate FAIL, o pipeline para e reporta
8. Gera relatório final com dashboard e métricas
```

## Quality Gates

Cada fase possui um quality gate que avalia:

- **PASS** → Avança para próxima fase
- **WARN** → Avança com ressalvas documentadas
- **FAIL** → Pipeline interrompe com recomendações de correção

No modo `--auto`, o quality gate é verificado automaticamente analisando a saída de cada skill. Se FAIL, o pipeline para e você pode corrigir e retomar com `--start-phase`.

## Uso

```bash
# Simulação (planejamento com CrewAI)
python .hermes/skills/cp-orquestrador/scripts/run.py "sistema de agendamento para clínicas"

# Execução automática (roda as crews de verdade)
python .hermes/skills/cp-orquestrador/scripts/run.py "sistema de agendamento" --auto

# Modo sprint automático
python .hermes/skills/cp-orquestrador/scripts/run.py "feature de relatório PDF" --mode sprint --auto

# Bug fix automático
python .hermes/skills/cp-orquestrador/scripts/run.py "corrigir erro de login" --mode micro --auto

# Auditoria de segurança
python .hermes/skills/cp-orquestrador/scripts/run.py "app financeiro" --mode security-audit --auto

# Documentação
python .hermes/skills/cp-orquestrador/scripts/run.py "API de pagamentos" --mode documentation --auto

# Com briefing de arquivo
python .hermes/skills/cp-orquestrador/scripts/run.py --input briefing.txt --auto

# Começar de uma fase específica (após correção)
python .hermes/skills/cp-orquestrador/scripts/run.py "sistema de estoque" --start-phase implementacao --auto

# Apenas ver o plano
python .hermes/skills/cp-orquestrador/scripts/run.py "sistema de agendamento" --dry-run

# Salvar artefatos em diretório específico
python .hermes/skills/cp-orquestrador/scripts/run.py "app de delivery" --output ./pipeline --auto
```

## Exemplo

```bash
python .hermes/skills/cp-orquestrador/scripts/run.py \
  "preciso de um sistema para clínica de estética onde a recepcionista agenda clientes, \
   a esteticista vê sua agenda do dia, e a dona da clínica quer relatórios de faturamento. \
   Também precisa enviar lembrete por WhatsApp automaticamente." \
  --mode full --output ./pipeline-relatorio.md
```

## Ponto Único de Entrada (Gerente da Fábrica)

O `cp-orquestrador` é o **gerente da fábrica de software** — direcione todos os pedidos para ele. Ele analisa o briefing, escolhe o modo, planeja as fases, define quality gates e gera o relatório.

### Modo Simulação (default)

Por padrão o orquestrador **simula** a execução — documenta o que cada fase produziria, sem chamar as outras skills. Útil para planejamento, apresentação a stakeholders e estimativa de esforço/risco.

### Modo `--auto` (executor real)

O modo `--auto` executa as crews reais em sequência, passando artefatos entre fases e aplicando quality gates automaticamente:
1. Planeja o pipeline
2. Chama `cp-requisitos` → recebe requisitos.md
3. Chama `cp-arquitetura --input requisitos.md` → recebe arquitetura.md
4. Chama `cp-implementacao --input arquitetura.md` → recebe código
5. ... até a entrega final
6. Gera relatório completo

Cada fase só avança se o quality gate passar. Se falhar, pausa e documenta o que precisa ser corrigido (retome com `--start-phase`). O modo `--auto` também aciona as skills complementares (`bugfix`, `competitive`, `full-dev`, `goal-loop`, `manutencao`).

## Script

O script `scripts/run.py` é self-contained — todos os 4 agentes estão embutidos no próprio código Python. Ele lista as crews disponíveis, simula a execução do pipeline (modo default) e executa as crews reais em sequência (modo `--auto`), acionando todas as skills `cp-*` via subprocess. Não depende de diretório externo de agentes.

## Manutenção do roadmap e inbox (crewbotics-back)

Antes de reportar "o que falta" ou atualizar `.hermes/roadmap/tasks.md`, SEMPRE cruze o
estado do roadmap/inbox contra o código real (modelos, endpoints, testes) — o roadmap
frequentemente marca como pendente coisas já implementadas (e às vezes no app errado).
Ver `references/roadmap-inbox-manutencao.md` para o procedimento completo: verificação
de estado real, convenção inbox→processed (features `[Concluído]` e bugs `[Corrigido]`
movidos via `git mv`), frontend em outro repo, e o pitfall de escrita mascarando
placeholders de exemplo.

## Windows: relay bash intermitente

Neste host Windows, `terminal`/`write_file` às vezes falham com
`execvpe(/bin/bash) failed: No such file or directory` (relay WSL intermitente).
Quando isso ocorrer, use `execute_code` com Python puro (subprocess/open) — não
passa pelo relay. Ver `references/windows-wsl-bash-relay-workaround.md`.

## Execução do pipeline (crewbotics-back) — pitfalls reais

Ao executar o pipeline de desenvolvimento (rodar testes, commitar, validar), ver
`references/dev-pipeline-execucao.md` para lições duráveis: testes rodam com
`uv run pytest` (não há `.venv` próprio), testes que tocam banco falham sem
`.env`/Postgres (pré-existente, não é sua mudança), SEMPRE conferir
`git status --short` antes de commitar (commit pode sair incompleto se nem todos
os arquivos foram staged), fechar imagens PIL antes de deletar tempdir no Windows,
e usar `True`/`False` (não `true`/`false`) em dicts de parameters Python.

## Skill design: auto-detecte o modo, não dependa do LLM lembrar de um flag

Ao adicionar um modo de renderização alternativo a uma skill (ex.: `card_mode` para
alternar entre executor de cards e renderer de marca), NÃO dependa de um flag opcional
que o LLM precisa lembrar de setar — o LLM chama a skill via function calling e decide
os parâmetros por conta própria, então um flag `default=False` cego faz o modo novo
nunca ser acionado. O modo correto deve ser DETECTADO automaticamente a partir do
prompt (ex.: padrão de "data + título" em lista → cards de lançamento). Ver
`references/skill-design-auto-detect.md` para a regra completa e a heurística de
detecção.

## Debug: "código certo localmente mas não funciona no app"

Antes de debugar uma skill que parece não ter efeito no app web, confirme de QUAL
diretório o processo do backend (porta 8000) está rodando — pode estar subindo de um
CLONE antigo do repo (ex.: `PycharmProjects\crewbotics-back`) que não tem a feature,
enquanto o trabalho real fica em outro clone (ex.: `Documents\Professional\...`).
Verificar o CommandLine do listener via PowerShell e comparar o arquivo da skill entre
os clones. Ver `references/debug-backend-clone-errado.md` para o passo a passo.

## Carrossel de currículo/perfil (caso de uso novo, não coberto)

`instagram_carousel_skill.py` hoje cobre: (a) cards de lançamento com data (detecção
automática) e (b) carrossel narrativo de marca. NÃO cobre bem "carrossel do MEU
currículo/perfil + foto real" — cai no caminho de marca genérico, ignora a foto e
reusa o template fallback `constellation` (layout idêntico ao caso anterior, o que
confunde o usuário). Para esse caso é preciso um executor dedicado: currículo →
slides + foto no cover. Ao depurar "gerou layout igual ao pedido anterior", confira
se a skill realmente consumiu a entrada nova ou caiu no fallback.
