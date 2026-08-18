# Landing Page Template — Creation Pattern

## When to use
Create a custom HTML landing page template for the Crewbotics platform (PageTemplate model, category="sales").

## Steps

### 1. Create the HTML file
Place in `static/page_templates/<template-name>/index.html`:
- 12 standard sections: nav, hero, logo-bar, problem, solution/features, how-it-works, use-cases, testimonials, pricing, CTA-final, footer
- Dark theme with CSS custom properties (`--bg`, `--surface`, `--border`, `--text`, `--muted`, `--accent`)
- Responsive with `clamp()` for font sizes and `auto-fit` grid
- Mobile-first: `@media (max-width: 768px)` for footer and padding
- All text in pt-BR
- Links point to `/signup`, `/chat`, `/pricing`, etc. (internal app routes)

### 2. Register in the database
```python
from pages.models import PageTemplate

with open("static/page_templates/<name>/index.html", encoding="utf-8") as f:
    html = f.read()

PageTemplate.objects.create(
    title="Crewbotics - Site de Vendas",
    description="Landing page de vendas: hero, recursos, casos de uso, precos, depoimentos e CTA.",
    category="sales",
    html_content=html,
    css_content="",
    is_public=True,
    order=30,
)
```

### 3. CSS conventions
- All CSS inline in `<style>` tag (no external files)
- CSS custom properties for theming (dark mode only)
- `clamp()` for responsive font sizes
- `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))` for responsive grids
- `border-radius: 12px` (cards) and `20px` (large cards)
- Gradient backgrounds via `linear-gradient(135deg, var(--accent), var(--accent2))`
- Feature cards: `background: var(--bg)`, hover effect with `border-color: var(--accent)` and `translateY(-2px)`

### 4. Pricing cards
- 3 tiers: Starter (free), Pro (featured), Business
- Featured card: `border-color: var(--accent)` + `::before` badge "Mais Popular"
- Price: `font-size: 40px; font-weight: 800`
- Feature list: `::before { content: '\\2713'; color: var(--accent) }`

### 5. Testimonials
- 3 quotes with author name + role
- Italic quote text, `font-style: italic`
- Author: `font-weight: 600`, role: `font-size: 12px; color: var(--muted)`

### 6. Assets directory
Create `static/page_templates/<name>/assets/` for any images/icons (can be empty if all styling is CSS-only).
