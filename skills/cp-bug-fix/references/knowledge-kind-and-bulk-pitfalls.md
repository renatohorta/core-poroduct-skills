# Knowledge: file-kind classification & bulk operations pitfalls

Durable pitfalls from the Crewbotics knowledge module (Django + Postgres). Applies to
any Django model with a `TextChoices` `CharField` and to bulk soft-delete endpoints.

## 1. `derive_kind` falls back to TXT for unrecognized extensions

`knowledge/enums.py` `derive_kind(title)` maps a filename/URL to a `DocKind`. If it only
recognizes a few extensions (pdf/docx/xlsx/svg/url), every other extension — **images
(.png/.jpg/.jpeg/.webp/.gif) and markdown (.md/.markdown)** — silently falls back to `TXT`.
Symptom: a generated PNG canvas is stored as `kind=TXT`; the UI shows a text icon instead
of an image icon.

**Fix:** expand `derive_kind` with the missing extension groups:
```python
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ico", ".avif")
_MD_EXTS = (".md", ".markdown")
# ... after the existing pdf/docx/xlsx/svg checks:
if t.endswith(_IMAGE_EXTS):
    return DocKind.IMAGE
if t.endswith(_MD_EXTS):
    return DocKind.MD
return DocKind.TXT
```

## 2. New TextChoices value longer than the field's `max_length` → migration

`DocKind` is a `models.TextChoices`; the model field is `CharField(max_length=4, choices=DocKind.choices)`.
Adding `IMAGE` (5 chars) or `MD` (2 chars) — `IMAGE` exceeds 4 — **breaks at runtime** (DB
rejects the value) even though Django doesn't error at import. You MUST:
1. Bump `max_length` (e.g. 4 → 6) in the model.
2. `makemigrations` + `migrate` (the generated migration carries the new choices list).
3. Reclassify existing rows: iterate active docs, re-derive kind from `file.name` (fallback
   `title`), and `save(update_fields=["kind"])` where it changed.

**Rule:** whenever you add a `TextChoices` member, check the field's `max_length` against the
longest new value. This is the Django equivalent of "verify all seed/copy functions copy all fields".

## 3. Frontend icon map must know the new kind

The frontend `iconCell` does `extMeta(doc.kind.toLowerCase())`. If the backend now emits
`IMAGE` but the frontend `EXT_META` map only has `png/jpg/jpeg/webp/gif`, the icon falls to
the generic `📎`. Add the new kind name to `EXT_META` (e.g. `image: ["🖼️", "#FEF3C7"]`).

## 4. Bulk soft-delete with `exclude` — Postgres `__in` is case-sensitive

A bulk-delete endpoint (`POST /knowledge/docs/bulk_delete/`) accepts `documentIds`, `folderIds`,
and `exclude` (list of titles/names to KEEP while deleting everything else). **Pitfall:** if you
lowercase the `exclude` values (`str(x).strip().lower()`) and then query `title__in=exclude`,
Postgres `__in` is case-sensitive — the lowercase values never match the real mixed-case titles,
so the "keep" items get deleted anyway. Symptom: `exclude=["The Ultimate ChatGPT Prompts Book.pdf"]`
still deletes that doc.

**Fix:** keep the original case for the query:
```python
exclude = [str(x).strip() for x in (body.get("exclude") or []) if str(x).strip()]
```
Do NOT lowercase before a `__in`/`__iexact`-style exact match. (Use `__in` with original case;
if you need case-insensitive keep, match by `id` set built from `__icontains` separately.)

## 5. Bulk soft-delete ordering: handle `exclude` BEFORE the plain "delete all"

If the skill/endpoint has a `if scope == "all":` branch that deletes everything, and a separate
`if scope == "all" and exclude:` branch, the plain branch must come AFTER the exclude branch —
otherwise `scope="all"` with `exclude` hits the plain branch first and deletes the items you
meant to keep. Order: `all+exclude` → `all` → `selected` → single item.

## 6. Post-migration stale CI reference (Dockerfile.celery)

After removing a subsystem (e.g. Celery → asyncio/TaskQueue that runs inside Daphne ASGI), sweep
the CI/CD workflows for stale references. Symptom: deploy fails with
`failed to read dockerfile: open Dockerfile.celery: no such file or directory` because the
workflow still has a "Build Celery worker image" step pointing at a deleted `Dockerfile.celery`.

**Fix:** remove the stale step; the deploy should build only the Django (Daphne ASGI) image,
which already runs the background TaskQueue/Scheduler. Validate the YAML after editing
(`python -c "import yaml; yaml.safe_load(open('...'))"`).

**General rule:** when a subsystem is removed, `git grep` for its name across `.github/`,
`.dockerignore`, `.env.example`, and config — not just the app code.
