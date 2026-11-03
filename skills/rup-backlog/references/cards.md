# Cards reference

## Types and IDs

| Type | ID | Parent | Required sections |
|------|----|--------|-------------------|
| epic | `EP-NNN` | none | Goal, Scope |
| story | `ST-NNN` | epic (required) | User story, Acceptance criteria, Definition of Done |
| task | `TK-NNN` | story (required) | Description, Target files, Covers |
| bug | `BUG-NNN` | story (optional) | Symptom, Reproduction (created by `rup-debug`) |

IDs are 3 digits, one sequence per type (`EP-1000` after `EP-999`).
Acceptance criteria get `ST-NNN/AC-n`: each `- ` bullet under
`## Acceptance criteria` becomes `- **ST-NNN/AC-n**: <text>`. A task's
`## Covers` lists those IDs; each must exist in the parent story.

## File layout

`.context/kanban/<column>/<ID>.md`, frontmatter keys in order: `id, type, title,
status, parent, priority, source, created_at, updated_at` (epics add `release`,
`iteration`). Body: `# <ID> — <title>`, the sections, then `## History`.
`status` always equals the folder; the folder wins.

## Columns

`1-backlog`, `2-todo`, `3-doing`, `4-review`, `5-testing`, `6-staging`,
`7-done`, `blocked`. New cards start in `1-backlog`.

## Priority

MoSCoW: `Must`, `Should` (default), `Could`, `Won't`.

## Title rules

Single line, non-empty, not of the form `[...]`.
