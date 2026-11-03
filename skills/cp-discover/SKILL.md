---
name: cp-discover
description: "Run a discovery conversation with the user before building anything new: problem, users, goals, non-goals, anti-goals, constraints and open questions, confirmed by the user and recorded in .context/. Use before starting a new product, feature or epic, when the idea is still fuzzy."
---

# cp-discover — talk first, then write

Discovery is a conversation, not a form. You, the agent, interview the user and
only then write the document. The result (`cp-discover.md`, Inception) is
embedded first in the packet of every later RUP skill.

## When to use

Before building anything new: a product, a feature, an epic. Skip it for a bug
(`cp-debug`) or a change that is already specified.

## Conversation rules

- One question per message. Never a list of questions.
- Build each question on the last answer; say why you ask when it is not obvious.
- Do not guess to fill a gap: ask, or put it in Open questions.
- Play back each part in your own words and ask what is wrong or missing.
- Write and record only after the user confirms the playback.

## Steps

1. Print the packet: `python scripts/run.py "<idea>"` (phase defaults to Inception).
2. Hold the conversation, section by section (`references/discovery.md`).
3. Write one document with a `## <Section>` heading per artifact.
4. Record it (mandatory): `python scripts/run.py --record FILE|- "<idea>"`.

The recorder checks every heading, then writes
`.context/docs/01-inception/cp-discover.md` and logs it. Needs the RUP standard
authorized in `.context/` (exit 5 otherwise: see `cp-context`).
