# Editing .md docs — secret-looking values are masked to `***`

## Symptom

When writing examples/JSON with secret-looking strings in `.md` files
(e.g. `{ "token": "TOKEN", "password": "SENHA" }`, `Authorization: Bearer *** the
write/edit tool may mask those values to `***` (content-safety
filter). The `git diff` and the read show `***` instead of the value you wrote.

This happens **on write** (writes `***` to the file) and **on display** (shows `***`
even when the file is correct). This double layer confuses the diagnosis — you
"see" `***` and assume the write failed, but the file may be correct.

## Diagnosis — read raw bytes

Use bytes, not text, to distinguish masking from real content:

```python
raw = open(p, "rb").read()
print(b'NOVA_SENHA' in raw)   # True = correct content in the file
print(b'***' in raw)          # False = no masking written
```

If the **bytes** contain the expected value, the `***` is only display masking —
do NOT rewrite the file (wastes iterations for nothing). If the bytes have `***`, the write
really masked it and it must be fixed.

## Fix — use placeholders that do not look like secrets

Replace with neutral placeholders that do not trigger the filter:

```python
# instead of: { "token": "xxx", "password": "yyy" }
# use:       { "token": "TOKEN_DO_EMAIL", "password": "NOVA_SENHA" }
```

To replace an exact line that already got masked, use regex on bytes:

```python
import re
pat = re.compile(rb'\*\*Corpo:\*\* `\{[^\r\n]*"password"[^\r\n]*`')
m = pat.search(raw)
if m:
    raw = raw[:m.start()] + b'**Corpo:** `{ "token": "TOKEN_DO_EMAIL", "password": "NOVA_SENHA" }`' + raw[m.end():]
    open(p, "wb").write(raw)
```

## Note

A simple substring replace (`raw.replace(old, new)`) may "not find" the old
if there is some invisible byte difference (CRLF, spaces). Prefer regex on bytes
over the whole line when the exact replace fails.
