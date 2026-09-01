# Roadmap and inbox maintenance (crewbotics-back)

## Golden rule: ALWAYS verify the real state against the code before reporting "what's missing"

The `.hermes/roadmap/tasks.md` and the `.hermes/inbox/` files **often get
out of date relative to the code**. Before answering "what's left to do?" or
"update the roadmap", cross-check the checkboxes/status against reality:

1. **Does the model exist?** `django.apps.apps.get_model("<app>", "<Model>")`.
2. **Does the endpoint exist?** `grep` for `PasswordResetRequestView`, `dashboard/kpis`, etc.
3. **Does the test exist?** `os.path.exists("tests/<app>/test_x.py")`.
4. **Where does it live?** The roadmap may predict a wrong app/location. E.g.: ActivityLog was
   predicted in `utils/models.py`, but was implemented in `activity/models.py` (dedicated
   app). Mark the task as done with a note "implemented in <real location>".
5. **The frontend lives in ANOTHER repo** (`C:\Users\renat\WebstormProjects\crewbotics-front`).
   Frontend tasks (pages /auth/forgot-password, reset-password, link on login)
   are NOT implementable in this backend repo — keep them pending and flag the repo.

## Inbox → processed convention

- Features in `.hermes/inbox/features/` and bugs in `.hermes/inbox/bugs/`.
- When an item has status `[Concluído]` (feature) or `[Corrigido]` (bug), it must be
  MOVED to `.hermes/inbox/processed/` (same filename, flat folder).
- Use **`git mv`** (preserves rename history) for the move.
- Items WITHOUT an explicit status (or with Open/Reclassified status) stay in the active folder.
- When moving, the commit shows only "rename (100%)" — if the file gained the `[Concluído]` status
  **in the same move**, `git mv` doesn't commit the content edit; run `git add`
  on the file afterwards to include the status marker in the same commit (or a separate commit).
- **Staging pitfall:** `git mv` already leaves the rename STAGED (status `R`). Do NOT run `git add`
  on the OLD path (`bugs/...`) — it fails with `fatal: pathspec ... did not match any files`.
  If you need to include a content edit in the same commit, `git add` only the NEW path
  (`processed/...`) and commit; the rename is already staged.

## Pitfall: writing tools masking content

When writing examples with fields that look like secrets (e.g.: `{ "token": "...", "password": "..." }`),
the writing/file tool may mask the values to `***` in the written file.
For placeholders in documentation, use tokens that don't look like real credentials
(e.g.: `"token": "TOKEN_DO_EMAIL"`, `"password": "NOVA_SENHA"`) and verify the file
by reading raw bytes (`open(p,"rb").read()`) if you suspect masking.

## Mark a feature as Completed in the inbox

If a feature was implemented and merged but the inbox `.md` has no `**Status:**`,
add the line `**Status:** [Concluído]` right after the header block (Date/Source),
then `git mv` to processed and commit.

## Pitfall: roadmap file lost content — rebuild from git history

Symptom: `.hermes/roadmap/iniciativas.md` (or tasks.md) has "holes" — sections that
became just a summary header (`## INI-01 a INI-13: Fundação do Sistema` without bullets),
or INI numbers that skip (INI-44 → INI-61). This happens when a feature commit
**replaces** the whole file with a summarized version instead of appending.

Recovery procedure (don't rewrite from scratch — the content exists in git):

1. **Diagnose the commit that broke it:** `git log --oneline --follow -- <file>` and
   compare the size (`git show <commit>:<file> | wc -c`) between commits. The commit
   where the size drops is the culprit.
2. **Map where each INI range lives:** the detailed content may be spread across
   SEVERAL historical commits, not just the one before the break. E.g.: INI-01..14 in one
   commit, INI-15..60 (table) in another, INI-61 in `tasks.md`, INI-62..70 in another, INI-71..79
   in the current file. Use `git show <commit>:<file>` to extract each block.
3. **Rebuild in sequential order:** assemble the new file by concatenating the blocks in
   INI numeric order (not in the order they appear in commits — `9e2e8b3` had
   INI-66/65 before INI-64, which would break the sequence if copied raw).
4. **Verify coverage:** `re.findall(r"INI-(\d+)", txt)` and confirm the list of
   numbers is contiguous (INI-01..79). Some numbers may never have had their own section
   (e.g.: INI-36/38/39 only referenced in tasks.md) — that's normal, not a hole.
5. **Commit on its own branch** (`docs/restore-<file>-roadmap`), merge with authorization.

Note: `git log --follow` is essential — without `--follow` git doesn't track the file through
renames and the history seems to start too late.
