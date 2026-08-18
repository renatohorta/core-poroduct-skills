# Cards de Lançamento (lista de itens com data) — layout + fallback de arte

Padrão validado (11/08/2026) para carrosséis que listam itens com data (ex.:
lançamentos de jogos, produtos, eventos) em vez de um arco narrativo de marca.

## Quando usar
O usuário pede um carrossel de "cards", um por item, cada um com data + título
(ex.: "monte um carrossel com cada lançamento de julho"). Diferente do carrossel
de marca (cover → conteúdo → CTA), aqui cada slide é um card independente.

## Regra de ouro: foto real vs arte estilizada
Se o usuário pede "foto do jogo/produto" mas NÃO existem imagens oficiais
(lançamentos futuros, produtos não lançados), **NÃO buscar na web nem pedir
arquivos por padrão**. Oferecer/gerar **arte estilizada** como fallback:
gradiente de cor temática + emoji representativo, meio transparente. Confirmar
com o usuário via `clarify` se houver dúvida, mas a arte estilizada é o fallback
aceito. (O usuário escolheu explicitamente essa opção quando perguntado.)

## Layout do card (1080x1350, PIL)
- Fundo graphite `#1B1B1D` com gradiente sutil (→ `#26262A`).
- **Arte à esquerda** (x=90, y=300, 420x760): gradiente vertical da cor temática
  + emoji grande centralizado, meio transparente (alpha ~0.55). Criar layer RGBA
  separado, desenhar, aplicar alpha, `Image.alpha_composite`.
- **Texto à direita** (x=560): data em terracota `#A67561` (bold 44px), título em
  branco (bold 72px, caixa alta, quebrado em linhas que cabem na largura).
- **Moldura fixa**: autor/categoria no topo, handle + numeração `NN / TOTAL` no
  rodapé.
- Fontes Windows: `arialbd.ttf` (título), `arial.ttf` (corpo), `seguiemj.ttf`
  (emoji — arial não tem glifos de emoji).

## Quebra de título
Usar `font.getbbox(text)[2] <= max_w` para quebrar em linhas que cabem na largura
disponível (evita estouro do texto sobre a arte). Títulos longos deslocam o texto
para baixo — ao validar por amostragem de pixels, amostre VÁRIOS pontos na região
do texto (não um único pixel), senão dá falso negativo.

## Validação (sempre)
1. **OCR** com tesseract (`--psm 3`) para confirmar título, data e moldura legíveis.
2. **Amostragem de pixels** para confirmar que a arte transparente está presente à
   esquerda (cor ≠ fundo) e o texto branco à direita, sem sobreposição.

## Implementação no backend (crewbotics-back)
O executor determinístico vive em `chat/skills/executors/render_carousel.py`
(INI-80, TSK-301..303), plugado na skill `instagram_carousel` via `card_mode=True`.
O caminho de marca (SVG→PNG via resvg_py) é preservado para carrosséis de marca.
