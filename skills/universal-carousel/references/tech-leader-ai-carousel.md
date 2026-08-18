# Carrosséis para líderes de tech na virada para IA (padrão de copy + ganchos)

Padrão de conteúdo recorrente: carrossel pessoal para o perfil @renato.academy (Instagram) e
@renatohorta (LinkedIn), destinado a líderes de tecnologia que estão levando suas empresas para IA.
Reutilize este framework; não recomece do zero.

## Público e proposta
- Público: CPOs, VPs, tech leads, diretores de produto/engenharia.
- Proposta: ajudar líderes de tech a atravessar a virada para IA em DOIS eixos — gestão de produto
  e construção de sistemas. A IA é tratada como mudança de produto E engenharia, não "um feature".

## Estrutura de 7 slides que funciona
1. **Capa/Hook** — pergunta magnética sobre a virada para IA (ex.: "Sua empresa vai virar para IA.
   A questão é: com ou sem você?") + foto de perfil + credenciais (CPTO · MBA FDC · GenAI MIT · ex-Hotmart).
2. **A real ameaça** — IA ≠ stack nova; é visão (produto + engenharia juntos).
3. **Credibilidade / números** — 15+ anos, 160 devs liderados, 10a 8m da engenharia ao CPO.
4. **Framework** — virada em 3 frentes: Produto, Engenharia, Organização.
5. **Gestão de produto** — valor real (não hype), dados como produto, roadmap por impacto.
6. **Construção de sistemas** — fundamentação, confiança/custo, escala com KPIs.
7. **CTA** — "A virada para IA não espera. Seu time está pronto?" + botão "Seguir @renato.academy".

## Ganchos de comentário (elemento "💬" destacado em cada slide interno)
Colocar UMA pergunta de engajamento por slide, em pill destacada. Ganchos que performam:
- "Qual é o maior desafio da sua empresa hoje?"
- "Quantas pessoas de tech você lidera hoje?"
- "Qual dessas 3 frentes é a mais difícil na sua empresa?"
- "Você já colocou IA no seu roadmap?"
- "Qual o maior gargalo técnico da sua virada para IA?"

## Estilo de design
- Versão escura executiva: graphite `#1B1B1D` + acento terracota `#A67561` (derivado da foto de perfil).
- **Template pronto (copy-and-modify):** `templates/tech-leader-dark-executive.html` na skill — CSS completo
  da versão escura (capa, slide interno, stats, layers, CTA enxuto, pill de gancho 💬, rodapé com handle).
  Copie, troque os caminhos `file:///CAMINHO/assets/...` pelos do projeto e injete a copy. Para a versão
  "alegre", troque as variáveis de cor (creme #FFF6E9 + laranja #FF7A45, cards brancos) — mesma estrutura.
- O usuário pediu também uma **versão "mais alegre"**: fundo creme quente `#FFF6E9`, cards brancos
  arredondados, acentos laranja `#FF7A45`/âmbar `#FFB45C`/teal `#4ECDC4`, blobs decorativos, emojis
  nos itens (💡📊🗺️🧱🛡️📈). Manter a MESMA copy; só mudar a identidade visual.
- Entregar as duas versões em pastas separadas (`carrossel_output/` e `carrossel_output_alegre/`).

## Preferências do usuário (regra dura)
- Handle é **@renato.academy** (NÃO @renatohorta para o Instagram). Verificar antes de gravar.
- **Não** colocar "Salve este post e compartilhe com um líder de tech" nem "↓ Comenta 'AI' para eu
  te marcar" no slide final, e **não** colocar "Salvar o post →" no rodapé do CTA. O slide final fica
  enxuto: título + subtítulo + botão "Seguir @renato.academy" + handle.
- Quando o usuário pedir ajuste pontual de UM slide, editar o HTML injetado daquele slide em
  `slides_html/` e re-renderizar SÓ ele — não regerar tudo.
