# Skill design: auto-detect the mode, don't rely on the LLM remembering a flag

Durable lesson from 11/08/2026 (INI-80, release carousel test in the app).

## The problem

I added an optional parameter `card_mode: bool = False` to the
`instagram_carousel_skill.py` skill to toggle between two renderers:
- `card_mode=True` → deterministic PIL executor (release cards, 1 per game)
- `card_mode=False` (default) → brand SVG→PNG renderer (narrative carousel 5-10 slides)

In the real test in the app (port 8080), the Copilot understood the request ("19 cards, one per
game, stylized art") and called the `instagram_carousel` skill — but **without**
`card_mode=True`. Result: it fell into the brand renderer and generated 8 generic narrative
slides, ignoring the list of 19 games. The deterministic executor I built
was never triggered.

## Why it happens

The LLM that calls the skill via function calling decides the parameters on its own,
based on the skill's `description`. An optional mode flag that the LLM "should"
remember to activate is **unreliable** — the LLM has no way to know a better
renderer exists for that case unless the description explicitly says
"activate card_mode when it's a list of items with dates". Even so, it's fragile.

## The rule

**If a skill has two rendering modes, the correct mode must be DETECTED
automatically from the prompt/input — never rely on an optional flag that
the LLM needs to remember to set.**

Correct pattern:
```python
def execute(self, prompt, card_mode=None, **kwargs):
    # Auto-detects: list of items with dates (e.g.: "02/07 Rhythm Heaven Groove; ...")
    if card_mode is None:
        card_mode = _looks_like_release_list(prompt)
    ...
```

The flag can exist as an explicit override, but the default must be automatic
detection, not a blind `False`.

## Detection heuristic for "release list"

A prompt is a candidate for release cards when it contains a
`date + title` pattern in a list, e.g.:
- `\d{2}/\d{2}` (dates) repeated
- followed by item names (games, products, movies)
- separated by `;`, `–`, `-`, or a line break

E.g.: `"02/07 Rhythm Heaven Groove; 07/07 Moonlight Peaks; ..."` → detect and use
the card executor.

## Verification in the test

After implementing the detection, the acceptance test is: run the release prompt
in the app and confirm the result has **1 card per item** (e.g.: 19 cards), not a
narrative carousel of 5-10 slides. If it still comes out narrative, the detection didn't fire
or the LLM didn't call the skill with the complete prompt.
