# Screen spec template for a UI generator (Lovable etc.)

Structure proven in a React project (TanStack Router + shadcn). Use as a skeleton
for the output of "document all screens to generate layout variations".

## Output contract
- Language: Brazilian Portuguese (labels/CTAs/titles).
- Preserve the shell (AppShell) on all internal screens; only auth is fullscreen.
- Require per-screen states: loading, error (with retry), empty, populated.
- Variation = layout, NEVER functionality/scope.

## Document skeleton

```
# <Product> — Technical Specification of All Screens

> Input document for the <Lovable>: generate layout variations faithful to the real product.
> Read the "Design System" section first — it defines the tokens that ALL screens use.
> Golden rule: <frontend is only visualization> (repeat the project rule).

## 1. Design System (mandatory for all screens)
- Theme (colors: background, surface, border, primary, accent).
- Fonts (headings / body / mono).
- Recurring components (buttons, chips/pills, status tags, cards, tables,
  KPIs/metrics, inputs, avatar, toast) — name the real classes/variants.

## 2. Global layout — AppShell
- Sidebar rail (collapsible) + nav items (with routes).
- Statusbar (global metadata: online, counts, plan badge).
- Mandatory preservation note.

## 3..N Screens
For each screen:
- Title + route (`/path`).
- Objective (1 line).
- Ordered structure (inside the shell, if internal).
- States (loading/error/empty/populated) and modals/CTAs.
- ⚠️ Mark fullscreen screens (auth) separately.

## Chat / conversational screen — if it exists:
- Side thread list + bubbles + composer.
- ⚠️ MANDATORY subsection: "Generative UI — Rich cards returned in the chat".
  For EACH card in the registry (they are not routes, they are screens): header, body, states,
  actions, and the CONTRACT RULE (e.g. an approval card forwards the decision to the backend;
  the frontend decides nothing).

## Route summary (map)
Table: Route | Screen | Inside the AppShell? (Yes/No-fullscreen auth)

## Guidelines for layout variations
1. Consistent shell on all internal screens.
2. Fixed dark theme (if the product is dark) — do not invent a light one.
3. PT-BR language.
4. Mandatory states per screen.
5. One primary CTA per screen; secondary actions as chips; destructive ones in red + confirmation.
6. Professional density (generous spacing, ~12px radius, soft shadows, micro-animations).
7. Fonts by function (mono for ids/timestamps/tokens).
8. Do not create new functionality.
```

## Inventory checklist (to avoid repeating the mistake of skipping dynamic cards)
- [ ] File-based routes inventoried (routes/**).
- [ ] Shared shell/layout documented once.
- [ ] Generative UI registry / dynamic cards inventoried (chat/conversational).
- [ ] Auth screens marked as fullscreen (no shell).
- [ ] Design system defined before the screens.
- [ ] Per-screen states (loading/error/empty/populated) present.
- [ ] "frontend = pure visualization / no business rule" rule preserved in the descriptions.
