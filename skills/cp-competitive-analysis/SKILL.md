---
name: cp-competitive-analysis
description: "Análise Competitiva — cria uma crew CrewAI com Analista de Mercado, Analista de Competidores, Analista de Pricing/Posicionamento e Estrategista para comparar produtos, features, preços, posicionamento e estratégias de mercado, gerando relatórios completos de inteligência competitiva. Use quando o usuário disser 'analisar concorrentes', 'análise competitiva', 'comparar concorrentes', 'benchmarking de mercado', 'competitive analysis', 'battle card', 'SWOT de concorrentes', ou precisar de inteligência competitiva para decisões estratégicas."
---

# cp-competitive-analysis — Análise Competitiva

Cria uma crew CrewAI com agentes especializados para executar o ciclo completo de análise competitiva:

1. **Analista de Mercado** — Define o escopo, mapeia o mercado, tamanho, crescimento e dinâmica competitiva
2. **Analista de Competidores** — Perfila cada concorrente: overview, produto, forças, fraquezas, estratégia
3. **Analista de Pricing/Posicionamento** — Compara preços, tiers, posicionamento e mapa de posicionamento
4. **Estrategista** — SWOT, vantagens competitivas, recomendações estratégicas e battle cards

## Agentes

| Agente | Função |
|--------|--------|
| Analista de Mercado | Define mercado, tamanho, crescimento, tendências e dinâmica competitiva |
| Analista de Competidores | Perfila concorrentes: overview, produto, forças, fraquezas, estratégia |
| Analista de Pricing/Posicionamento | Compara preços, tiers, posicionamento e mapa de posicionamento |
| Estrategista | SWOT, vantagens competitivas, recomendações e battle cards |

## Entrada

Contexto da análise — sua empresa/produto, concorrentes a analisar (ou critérios para identificá-los), indústria/segmento, escopo geográfico e aspectos de foco. Pode ser:
- Texto direto no argumento: `"nossa empresa é um SaaS de gestão de clínicas; analise concorrentes como Doctoralia e Zenklub"`
- Arquivo: `--input contexto.txt`

## Saída

Relatório de inteligência competitiva completo contendo:
- Executive summary com key takeaways
- Market overview (definição, tamanho, crescimento, landscape)
- Perfis de cada concorrente (overview, produto, forças, fraquezas, estratégia)
- Matriz de comparação de features
- Comparação de pricing (tiers/planos)
- Mapa de posicionamento
- Resumo SWOT
- Vantagens competitivas (suas vs. dos concorrentes)
- Recomendações estratégicas (imediatas, médio prazo, respostas a vigiar)
- Battle cards por concorrente (pitch, resposta, diferenciais, objeções)

## Quality Gate

O Estrategista emite veredito PASS/FAIL sobre a completude do relatório. Se FAIL, o relatório precisa de correções antes de ser considerado concluído.

## Uso

```bash
# Contexto direto
python .hermes/skills/cp-competitive-analysis/scripts/run.py "SaaS de gestão de clínicas; concorrentes: Doctoralia, Zenklub"

# Contexto de arquivo
python .hermes/skills/cp-competitive-analysis/scripts/run.py --input contexto.txt

# Salvar saída em arquivo específico
python .hermes/skills/cp-competitive-analysis/scripts/run.py "nosso produto X" --output docs/analise-competitiva.md

# Apenas ver a estrutura da crew
python .hermes/skills/cp-competitive-analysis/scripts/run.py "teste" --dry-run
```

## Exemplo

```bash
python .hermes/skills/cp-competitive-analysis/scripts/run.py \
  "Somos um SaaS de gestão de clínicas de estética no Brasil. \
   Queremos analisar concorrentes como Doctoralia, Zenklub e Clínica Ágil, \
   focando em features, pricing e posicionamento. Objetivo: estratégia de go-to-market."
```

## Script

O script `scripts/run.py` é self-contained — todos os agentes estão embutidos no próprio código Python. Não depende de diretório externo.

## Caminho manual (alternativa ao script)

Quando o alvo é um concorrente específico e o time tem documentação interna do próprio produto, o caminho manual costuma render melhor que a crew — o agente já tem contexto do produto e pode comparar com precisão. Fluxo validado:

1. **Navegar no site oficial do concorrente** (browser_navigate) — home, `/pricing`, `/about`, páginas de produto. Extrair texto real via `browser_console` com `document.body.innerText` (o snapshot acessível às vezes omite conteúdo renderizado por JS).
2. **Delegar a pesquisa ampla a um subagente** (`delegate_task` com toolsets `["web","browser"]`) para coletar capacidades, planos, posicionamento e concorrentes em paralelo — evita poluir o contexto do agente principal com dezenas de navegações.
3. **Ler a documentação interna** do produto próprio (`.hermes/docs/`) para a comparação feature-a-feature, pricing, SWOT e battle card.
4. **Salvar a especificação** em `doc/competitive-analysis/<concorrente>-vs-<produto>.md` (convenção do projeto Crewbotics — pasta `doc/` na raiz, não `.hermes/docs/`).

## Pitfall: contadores de preço animados

Páginas de pricing modernas (ex.: manus.im) renderizam os valores em US$ como **contadores animados** — cada dígito é um elemento separado que muda com animação. Isso faz `document.body.innerText` e seletores de texto devolverem dígitos soltos (`"0","1","2",...`) ou nada, e o preço real não é extraível por scraping. O que funciona:
- **Créditos/quantidades** (ex.: "4.000 créditos/mês") costumam ser texto estático e são extraíveis.
- **Preços em moeda** podem não ser extraíveis — **marque como "não confirmado"** no relatório e peça o valor ao usuário (que pode ter a página aberta no navegador dele) em vez de inventar.

## Referências

- `references/manus-im.md` — dados de pesquisa do Manus (manus.im) coletados em 15/08/2026: capacidades, planos, posicionamento, concorrentes e notas de confiabilidade.
