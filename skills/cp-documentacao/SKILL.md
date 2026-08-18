---
name: cp-documentacao
description: "Documentação de Software — cria uma crew CrewAI com Redator Técnico, Redator de Usuário, Diagramador e Revisor para gerar documentação técnica, de API, de usuário e diagramas. Use quando o usuário disser 'documentar', 'criar documentação', 'escrever README', 'gerar docs da API', 'criar manual do usuário'."
---

# cp-documentacao — Documentação de Software

Cria uma crew CrewAI com agentes especializados para gerar documentação completa de software:

1. **Redator Técnico** — Escreve documentação técnica e de API. Transforma código complexo em documentação clara e útil.
2. **Redator de Usuário** — Escreve manuais, guias, FAQs, tutoriais. Foco no usuário final com linguagem simples e exemplos práticos.
3. **Diagramador** — Cria diagramas, fluxogramas, capturas de tela (Mermaid, PlantUML). Vale mais que 1000 palavras.
4. **Revisor de Documentação** — Verifica clareza, completude, consistência, ortografia. Não deixa passar erro de português ou informação faltando.

## Pipeline (tasks sequenciais)

```
[Análise] ──► [Doc Técnica + API] ──► [Doc de Usuário] ──► [Diagramas] ──► [Revisão]
    │                │                       │                  │               │
    │  Redator       │  Redator Técnico      │  Redator         │  Diagramador │  Revisor
    │  Técnico       │                       │  de Usuário      │              │
    │                │                       │                  │              │
    └────────────────┴───────────────────────┴──────────────────┴──────────────┴── PASS/FAIL
```

## Agentes

| Agente | Função |
|--------|--------|
| Redator Técnico | Análise do que documentar + documentação técnica e de API |
| Redator de Usuário | Manuais, guias, FAQs, tutoriais para o usuário final |
| Diagramador | Diagramas Mermaid/PlantUML, fluxogramas, visuais |
| Revisor de Documentação | Revisão final: clareza, completude, consistência, ortografia |

## Entrada

Descrição do que documentar — pode ser:
- Código fonte (caminho do projeto)
- APIs (endpoints, schemas)
- Requisitos funcionais
- Texto direto no argumento: `"API de agendamento para clínicas"`
- Arquivo: `--input descricao.txt`

## Saída

Documentação completa contendo:
- README principal do projeto
- Documentação técnica (arquitetura, componentes, decisões)
- Documentação de API (endpoints, schemas, exemplos)
- Guia do usuário (instalação, configuração, uso)
- Diagramas (arquitetura, fluxo, entidade-relacionamento)
- Documentação revisada e aprovada

## Documentando TELAS de um app (spec para Lovable/gerador de UI)

Quando o pedido é "especificar todas as telas do sistema para gerar variações de layout"
(no Lovable ou similar), o inventário NÃO pode ser dirigido só por rotas. Pitfall real
que já pegou: listar apenas `src/routes/*.tsx` deixa de fora os componentes **dinâmicos**
renderizados em superfícies conversacionais (chat), que são telas/cards de primeira classe
para o gerador.

Receita de inventário completo:
1. **Rotas (file-based)**: `src/routes/**/*.tsx` → uma entrada por rota (método de listar:
   `os.walk` em Python; neste host o `search_files` falha se não houver ripgrep).
2. **Layout/shell compartilhado**: o `AppShell`/layout (rail lateral + statusbar) é o
   esqueleto que TODAS as telas internas compartilham — documente-o uma vez e marque quais
   telas usam (internas) e quais são fullscreen sem rail (auth).
3. **Componentes dinâmicos / Generative UI**: qualquer `registry` de cards que o backend
   renderiza dentro do chat (`render_*_tool`, `uiPayload.component`) SÃO telas para o
   gerador. Inventarie cada card (header, corpo, estados, ações) e a regra de contrato
   (ex.: card de aprovação apenas encaminha a decisão de volta ao backend).
4. **Design system obrigatório**: defina tokens (cores, fontes, componentes recorrentes)
   antes das telas — é o que mantém as variações coerentes.
5. **Estados por tela**: loading / erro (com retry) / vazio / populated — exija todos.
6. **Não mudar escopo**: variação é de layout, não de funcionalidade.

Reutilize o esqueleto pronto em `templates/spec-telas-lovable.md` (estrutura + checklist
de inventário) como ponto de partida.

## Quality Gate

O Revisor de Documentação emite veredito PASS/FAIL. Se FAIL, a documentação precisa de correções.

## Uso

```bash
# Modo full (padrão): documentação completa
python .hermes/skills/cp-documentacao/scripts/run.py "API de agendamento para clínicas"

# Modo específico: apenas documentação técnica
python .hermes/skills/cp-documentacao/scripts/run.py "API REST de pedidos" --mode tech

# Modo específico: apenas documentação de usuário
python .hermes/skills/cp-documentacao/scripts/run.py "app mobile de delivery" --mode user

# Modo específico: apenas diagramas
python .hermes/skills/cp-documentacao/scripts/run.py "sistema de e-commerce" --mode diagrams

# Modo específico: apenas documentação de API
python .hermes/skills/cp-documentacao/scripts/run.py "endpoints de autenticação" --mode api

# Com arquivo de entrada
python .hermes/skills/cp-documentacao/scripts/run.py --input descricao.txt

# Salvar saída em arquivo específico
python .hermes/skills/cp-documentacao/scripts/run.py "API de pagamentos" --output docs/completa.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-documentacao/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-documentacao/scripts/run.py \
  "API REST para sistema de agendamento de consultas médicas. \
   Endpoints: GET /medicos, POST /agendamentos, DELETE /agendamentos/:id. \
   Autenticação JWT. Notificações por email. \
   Tecnologias: Django REST Framework, PostgreSQL, Redis para fila de emails."
```

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.
