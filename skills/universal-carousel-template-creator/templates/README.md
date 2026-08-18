# Templates de Carrossel Instagram (1080×1350)

Templates HTML/CSS gerados a partir de zips de templates Freepik em
`C:\Users\renat\Downloads\templates\`. Cada pasta contém um `slide.html`
auto-contido com múltiplos layouts (via atributo `data-layout` + `<script>`)
e os mesmos placeholders. Fontes compartilhadas em `_shared_fonts/`.

## Placeholders comuns
`{{TITLE}} {{BODY}} {{EYEBROW}} {{SLIDE_NUM}} {{TOTAL_SLIDES}} {{HANDLE}} {{BRAND}} {{NEXT_LABEL}}`
`{{ITEM_1..3}} {{ITEM_1..3_TITLE}} {{ITEM_1..3_BODY}} {{ITEM_1..3_NUM}} {{PRICE}} {{CTA_LABEL}} {{QUOTE_EMOJI}}`
Específicos: `{{THEME}}`(dark/light, t1), `{{TITLE_L1}} {{TITLE_L2}}`(t4,t8),
`{{SCRIPT}}`(t6), `{{LOCATION}} {{IMG_LABEL}} {{LIKES}} {{CAPTION}} {{COMMENTS}} {{TIME_AGO}}`(t1).

## Como usar
1. Preencha os placeholders no slide.html (ex.: substitua `{{TITLE}}` pelo texto).
2. Renderize com Chrome headless:
   `chrome.exe --headless=new --window-size=1080,1350 --force-device-scale-factor=1 --screenshot=slide_01.png file:///CAMINHO/slide.html`
3. Repita para cada slide, alterando `{{LAYOUT}}` e `{{SLIDE_NUM}}`.

## Índice
| Pasta | Zip fonte | Tema | Fontes | Layouts |
|-------|-----------|------|--------|---------|
| freepik-constellation | carousel-instagram-post-design.zip | Constelações/astrologia, lavanda #CDC4FB | Poppins | A(cover) B B2 C(steps) D(cta) |
| freepik-t1-montserrat | instagram-carousel-templates (1).zip | Mockup post Instagram (dark/light) | Montserrat | title list cta |
| freepik-t2-gilroy | instagram-carousel-templates (2).zip | Adaptiv coral #FF6148 | Montserrat(+Gilroy→M800) Lobster | cover intro list quote cta |
| freepik-t3-fashion | instagram-carousel-templates (3).zip | Fashion/loja bege | Raleway Bodoni HerrVonM. Poppins | hero arrivals price feature brand |
| freepik-t4-apartment | instagram-carousel-templates (4).zip | Decoração/apartamento sage #D2DBBE | AbrilFatface RobotoCondensed | hero card list quote cta |
| freepik-t5-lorem | instagram-carousel-templates (5).zip | Café/chocolate marrom #844C19 | AbhayaLibre Poppins | hero card list quote cta |
| freepik-t6-chairs | instagram-carousel-templates (6).zip | Móveis/cadeiras creme #FFEABB | AbhayaLibre GreatVibes JosefinSans Montserrat | hero products feature cta |
| freepik-t7-company | instagram-carousel-templates (7).zip | Empresa/empresarial rosa #FEEBEF | LibreBaskerville Montserrat | hero card list cta |
| freepik-t8-newcollection | instagram-carousel-templates-new-collection.zip | Nova coleção dark/oliva + lima #D4F828 | Poppins Montserrat | hero card list cta |
| freepik-t9-photos | instagram-carousel-templates-with-photos.zip | Advertising navy #021E57 + red | BebasNeue GreatVibes Montserrat | hero card list cta |
| freepik-t10-bebas | instagram-carousel-templates.zip | Instaphato índigo #C4CEFF | BebasNeue GreatVibes Montserrat | hero card list cta |
| freepik-t11-pet | set-instagram-carousel-templates.zip | Pet/cachorro bege #E4B97A | Gaegu Poppins | hero tips card cta |

## Templates Crewbotics (a partir de SVGs em `templates_crewbotics/`)

| Pasta | Tema | Cores | Layouts |
|-------|------|-------|---------|
| crewbotics-beige-orange | Bege + laranja, microblog/branding (Harper Russo) | #EEE3D5 / #E8893C | cover intro steps list cta |
| crewbotics-bw-productivity | Preto e branco, produtividade/time block | #090706 / #CACABE | cover intro steps list cta |
| crewbotics-bw-marketing-tips | P&B minimalista, dicas de marketing | #040405 / #8A8A8A | cover intro steps list cta |
| crewbotics-bw-red | Preto/branco/vermelho, personal branding | #140D0F / #D32F2F | cover intro steps list cta |
| crewbotics-blue-running | Azul dinâmico, dicas de corrida | #0F1897 / #6D839B | cover intro steps list cta |
| crewbotics-green-business | Verde, como começar um negócio | #27452A / #6FA96E | cover intro steps list cta |
| crewbotics-orange-social | Laranja, dicas de mídia social | #FD6F15 / #512407 | cover intro steps list cta |
| crewbotics-orange-black | Laranja/preto, branding (Harper Russo) | #F2E9EB / #B13713 | cover intro steps list cta |
| crewbotics-purple-marketing | Roxo/preto/branco, marketing moderno + IA | #1A1B1B / #B4AEDD | cover intro steps list cta |
| crewbotics-sage-advertising | Sage, o que saber antes de anunciar | #626048 / #E3DDD3 | cover intro steps list cta |
| crewbotics-yellow-black | Amarelo/preto, microblog marketing | #F6F1ED / #E3BF2A | cover intro steps list cta |
| crewbotics-yellow-green-habits | Amarelo/verde, dicas de hábitos | #2D2611 / #9C8856 | cover intro steps list cta |

Placeholders: `{{TITLE}} {{BODY}} {{EYEBROW}} {{HANDLE}} {{SLIDE_NUM}} {{TOTAL_SLIDES}} {{NEXT_LABEL}} {{PROMPT}} {{ITEM_1..3_TITLE}} {{ITEM_1..3_BODY}} {{LAYOUT}}`.
