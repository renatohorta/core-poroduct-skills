# Skill design: auto-detect o modo, não dependa do LLM lembrar de um flag

Lição durável de 11/08/2026 (INI-80, teste do carrossel de lançamentos no app).

## O problema

Adicionei um parâmetro opcional `card_mode: bool = False` à skill
`instagram_carousel_skill.py` para alternar entre dois renderizadores:
- `card_mode=True` → executor PIL determinístico (cards de lançamento, 1 por jogo)
- `card_mode=False` (default) → renderer SVG→PNG de marca (carrossel narrativo 5-10 slides)

No teste real no app (porta 8080), o Copilot entendeu o pedido ("19 cards, um por
jogo, arte estilizada") e chamou a skill `instagram_carousel` — mas **sem**
`card_mode=True`. Resultado: caiu no renderer de marca e gerou 8 slides narrativos
genéricos, ignorando a lista de 19 jogos. O executor determinístico que eu construí
nunca foi acionado.

## Por que acontece

O LLM que chama a skill via function calling decide os parâmetros por conta própria,
baseado na `description` da skill. Um flag opcional de modo que o LLM "deveria"
lembrar de ativar é **não confiável** — o LLM não tem como saber que existe um
renderizador melhor para aquele caso a menos que a descrição diga explicitamente
"ative card_mode quando for lista de itens com data". Mesmo assim, é frágil.

## A regra

**Se a skill tem dois modos de renderização, o modo correto deve ser DETECTADO
automaticamente a partir do prompt/entrada — nunca depender de um flag opcional que
o LLM precisa lembrar de setar.**

Padrão correto:
```python
def execute(self, prompt, card_mode=None, **kwargs):
    # Auto-detecta: lista de itens com data (ex.: "02/07 Rhythm Heaven Groove; ...")
    if card_mode is None:
        card_mode = _looks_like_release_list(prompt)
    ...
```

O flag pode existir como override explícito, mas o default deve ser a detecção
automática, não `False` cego.

## Heurística de detecção para "lista de lançamentos"

Um prompt é candidato a cards de lançamento quando contém padrão de
`data + título` em lista, ex.:
- `\d{2}/\d{2}` (datas) repetido
- seguido de nomes de itens (jogos, produtos, filmes)
- separados por `;`, `–`, `-`, ou quebra de linha

Ex.: `"02/07 Rhythm Heaven Groove; 07/07 Moonlight Peaks; ..."` → detectar e usar
o executor de cards.

## Verificação no teste

Depois de implementar a detecção, o teste de aceite é: rodar o prompt de lançamentos
no app e confirmar que o resultado tem **1 card por item** (ex.: 19 cards), não um
carrossel narrativo de 5-10 slides. Se ainda sair narrativo, a detecção não disparou
ou o LLM não chamou a skill com o prompt completo.
