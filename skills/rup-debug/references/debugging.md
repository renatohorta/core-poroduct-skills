# Debugging protocol

1. **Reproduce first.** No reproduction, no diagnosis. Reduce to the smallest steps and inputs that fail every time.
2. **Pin it with a test.** The regression test fails for the reason in the Symptom, names the bug ID (`BUG-NNN`) and asserts real behavior.
3. **Root cause, not symptom.** Ask "why" until the answer is a decision or a missing check you can change (the slot set is never checked before insert), not a place where it shows (the insert crashes).
4. **Evidence over guesses.** One hypothesis at a time; confirm it with a log, a debugger or a smaller test before changing code.
5. **Record it.** `## Root cause` states what is wrong, why it happens and what proves it, in a few sentences.
6. **Fix minimally.** Change the cause; do not refactor around it. The regression test must go green and the rest of the suite stay green.
7. **Look for siblings.** If the same mistake can occur elsewhere, add tests or open another bug.
