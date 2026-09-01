# DOC-01 — claude_proxy port diverges between README and code [Done]

**Type**: Documentation bug · **Severity**: Low · **Opened on**: 2026-08-18

## Symptom

- `README.md` instructs `python scripts/claude_proxy.py --port 8090` and justifies:
  "avoids conflict with frontends on 8080".
- `scripts/claude_proxy.py` defines `DEFAULT_PORT = 8080`, and the module docstring
  also exemplifies 8080 and `LLM_API_BASE=http://localhost:8080/v1`.

Anyone running without `--port` starts on 8080 and configuring the `.env` per the
README (8090) results in a refused connection.

## Proposed fix

Align on **8090**: change `DEFAULT_PORT = 8090` and update the module docstring
(example `--port` and `LLM_API_BASE` lines).

## Acceptance criterion

- `python scripts/claude_proxy.py` starts on 8090.
- README, docstring and code cite the same port.


---

## Resolution

**Done on 2026-08-18.** Verified with the suite (`pytest`, 158 tests, no
LLM credential). See `.context/docs/04-quality-qa.md`.
