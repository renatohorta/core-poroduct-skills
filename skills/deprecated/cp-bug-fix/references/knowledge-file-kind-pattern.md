# Knowledge File Kind Pattern

When saving files to the knowledge base via `archive_conversation_file()` or `write_knowledge_file`, the `derive_kind()` function in `knowledge/enums.py` determines the document type from the filename extension.

## The Pattern

Every new file type saved to the knowledge base needs:

1. **A new `DocKind` enum value** in `knowledge/enums.py`
2. **A new `if t.endswith(...)` branch** in `derive_kind()`

## Current Mappings

| Extension | Kind | Notes |
|-----------|------|-------|
| `.pdf` | PDF | |
| `.docx` | DOCX | |
| `.xlsx` | XLSX | |
| `.svg` | SVG | Added 2026-08-06 — was falling through to TXT |
| `.png` `.jpg` `.jpeg` `.webp` `.gif` `.bmp` `.ico` `.avif` | IMAGE | Added 2026-08-07 — was falling through to TXT |
| `.md` `.markdown` | MD | Added 2026-08-07 — was falling through to TXT |
| `http://` / `https://` | URL | |
| anything else | TXT | Default fallback |

## Common Pitfalls

- **SVG/IMAGE/MD files saved as TXT** — if `derive_kind()` doesn't recognize the extension, files are stored as TXT and the frontend can't render them correctly. The `kind` field is used by the frontend to decide how to display/preview the file.
- **Adding a new DocKind requires updating the enum AND derive_kind()** — the enum alone doesn't fix the mapping.
- **`kind` field `max_length` must fit the longest new value** — the model field is `CharField(max_length=4, choices=DocKind.choices)`. Adding a 5-char value like `IMAGE` breaks at runtime (DB truncation / validation) unless you bump `max_length` to 6 AND create a migration (`makemigrations knowledge`). Check the field's `max_length` whenever you add a DocKind longer than the current max.
- **Reclassify existing rows after adding kinds** — existing docs created before the fix keep the wrong `TXT` kind. Run a one-off script that re-derives `kind` from `d.file.name` (fallback `d.title`) for all non-deleted docs and saves `update_fields=["kind"]`.
- **Frontend `EXT_META` needs the new kind** — `iconCell` does `extMeta(doc.kind.toLowerCase())`. If the new kind (e.g. `image`) isn't a key in `EXT_META` in `src/routes/knowledge.tsx`, the icon falls back to the generic 📎. Add a key for the new kind.
- **archive_conversation_file() passes `filename` to derive_kind()** — the filename must have the correct extension. The `title` parameter is for display only.
