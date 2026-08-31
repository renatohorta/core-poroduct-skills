---
name: cp-benchmark-to-spec
description: "Benchmark para Especificação Técnica — transforma um produto de referência (concorrente ou benchmark) em documentação técnica completa e replicável. Recebe insumos (URLs, pesquisa web, screenshots), faz crawler da documentação, extrai o design system das telas e gera a especificação RUP (Inception → Elaboration → Construction → Transition) + gestão de projeto (épicos/histórias/tasks) para o time de desenvolvimento reconstruir o produto. Use quando o usuário disser 'replicar produto', 'engenharia reversa', 'benchmark para spec', 'gerar documentação técnica de um produto', 'crawler + documentação', 'especificação para reconstruir', 'transformar produto em spec', ou precisar transformar um produto de referência em documentação técnica."
---

# cp-benchmark-to-spec — Benchmark para Especificação Técnica

Transforma um **produto de referência** (concorrente, benchmark, ou produto que se quer
replicar) em **documentação técnica completa e replicável**, pronta para o time de
desenvolvimento reconstruir o produto. O processo combina **crawler de documentação**,
**análise de design system a partir de screenshots** e **geração de especificação RUP**.

## Pipeline

```
[Insumos] ──► [Crawler] ──► [Design System] ──► [Spec RUP] ──► [Gestão de Projeto]
   │             │               │                 │                │
  URLs,        docs em        screenshots      4 fases RUP      épicos/histórias/
  pesquisa,    texto/md       → tokens de UI    (Inception →     tasks/roadmap
  screenshots  (llms.txt)     (cores, fontes,   Transition)
                              espaçamento)
```

## Agentes

| Agente | Função |
|--------|--------|
| **Analista de Documentação** | Faz crawler da documentação do produto de referência e extrai o conteúdo-fonte |
| **Analista de Design** | Analisa screenshots e extrai o design system (cores, tipografia, componentes) |
| **Especificador Técnico** | Gera a especificação RUP completa (4 fases) a partir do conteúdo-fonte |
| **Gestor de Projeto** | Gera épicos, histórias, tasks e roadmap referenciando a spec |

## Entrada

Insumos sobre o produto de referência. Pode ser:
- **URLs** da documentação (ex: `https://produto.com/help/reference`).
- **Pesquisa web** (pedido para pesquisar o produto na internet).
- **Screenshots** (pasta com imagens das telas).
- **Arquivo de contexto** (`--input contexto.txt`).

## Saída

Documentação técnica completa em `doc_dev/` (ou pasta indicada), organizada por fases RUP:

### Fase 1 — Inception (`01-inception/`)
- `00-visao-do-produto.md` — visão, problema, solução, público-alvo, diferenciais
- `01-atores.md` — atores e papéis
- `02-requisitos-gerais.md` — requisitos funcionais e não funcionais
- `03-glossario.md` — terminologia do domínio

### Fase 2 — Elaboration (`02-elaboration/`)
- `04-arquitetura-de-sistema.md` — arquitetura (backend/frontend/banco)
- `casos-de-uso/` — casos de uso detalhados por domínio

### Fase 3 — Construction (`03-construction/`)
- `schema/` — modelo de dados PostgreSQL + migrations
- `especificacao/` — detalhamento técnico por módulo
- `api/` — especificação REST + WebSocket
- `frontend/` — componentes React, páginas, tipos

### Fase 4 — Transition (`04-transition/`)
- `05-plano-de-testes.md` — testes por nível
- `06-deploy-e-infra.md` — deploy, CI/CD, infraestrutura
- `07-treinamento.md` — treinamento

### Gestão de Projeto (`05-project-management/`)
- `01-epicos.md` — épicos por domínio
- `02-historias.md` — histórias com critérios de aceite
- `03-tasks.md` — tasks com referências técnicas
- `04-roadmap.md` — fases de entrega e marcos

### Design System (raiz)
- `design-system.md` — especificação de UI/UX (cores, tipografia, componentes)

## Quality Gate

O Especificador Técnico emite veredito PASS/FAIL sobre a completude da spec. Se FAIL,
a spec precisa de correções antes de ser considerada concluída. Critérios:
- Todas as 4 fases RUP presentes.
- Casos de uso cobrindo os domínios principais.
- Design system extraído das telas.
- Gestão de projeto (épicos/histórias/tasks) referenciando a spec.

## Uso

```bash
# Insumos diretos (URLs + pedido)
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py "produto: Attio; URL: https://attio.com/help/reference; gere a spec completa"

# Contexto de arquivo
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py --input contexto.txt

# Salvar saída em pasta específica
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py "produto X" --output ./spec

# Apenas ver a estrutura da crew
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-benchmark-to-spec/scripts/run.py \
  "Quero replicar o produto Fibery. \
   URL da documentação: https://the.fibery.io/@public/User_Guide/Start-6568 \
   Screenshots em: design/ \
   Gere a especificação técnica completa para meu time reconstruir."
```

## Caminho manual (alternativa ao script)

Quando o alvo é um produto específico e o agente tem acesso a browser/ferramentas, o
caminho manual costuma render melhor que a crew — o agente executa o crawler e a geração
diretamente. Fluxo validado (usado para Attio e Fibery):

1. **Crawler da documentação** — acessar a URL de referência. Se o produto oferecer um
   arquivo `llms.txt`/`llms-full.txt` (ex: `https://produto.com/llms-full.txt`), baixá-lo
   via `curl` — é muito mais eficiente que raspar página por página. Caso contrário, usar
   `browser_navigate` + `browser_console` com `document.body.innerText` para extrair o texto.
2. **Mapear a estrutura** — listar as seções principais do conteúdo-fonte para entender o
   escopo do produto (features, módulos, integrações).
3. **Analisar screenshots** — usar `vision_analyze` em telas representativas para extrair o
   design system (cores hex, fontes, espaçamentos, componentes). **Evitar loop**: analisar
   poucas telas-chave e consolidar, não analisar imagem por imagem.
4. **Gerar a spec RUP** — criar os documentos das 4 fases em `doc_dev/`, referenciando o
   conteúdo-fonte. **Não duplicar** conteúdo — cada documento referencia os demais.
5. **Gerar o design system** — `design-system.md` com tokens de UI.
6. **Gerar a gestão de projeto** — épicos/histórias/tasks/roadmap em `05-project-management/`.
7. **Revisar com as telas** — cruzar a spec com os screenshots para identificar lacunas
   (features que ficaram de fora) e questões avançadas.

## Pitfalls

| Pitfall | Solução |
|---------|---------|
| Analisar screenshot por screenshot entra em loop | Analisar poucas telas-chave e consolidar; usar `llms.txt` para o conteúdo textual |
| `llms-full.txt` é grande (1.6MB+) | Baixar via `curl` e ler seções-chave, não o arquivo inteiro |
| Screenshots misturam landing page de marketing com o app | Focar nas telas do app real (workspace), não nas de marketing |
| Gerar docs em diretório errado | Confirmar o caminho de saída antes de escrever |
| Duplicar conteúdo entre docs | Cada documento referencia os demais, não reescreve |

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio
código Python. Não depende de diretório externo.

## Referências

- `cp-skill-craft` — padrão de criação de skills cp-* neste repositório.
- `cp-competitive-analysis` — skill complementar (análise competitiva, comparação de concorrentes).
