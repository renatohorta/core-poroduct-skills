# The RUP standard `.context/` tree

`--init` creates only what is missing (skeleton = title + "To be filled.").

```
.context/
  .rup-standard                 marker: version, authorized_by, authorized_at
  README.md
  docs/
    01-inception/    vision-and-scope.md, requirements.md
    02-elaboration/  architecture.md, domain-model.md
    03-construction/ api-contracts.md, ui-spec.md, data-dictionary.md
    04-transition/   test-strategy.md, devops-infra.md
  inbox/             initiatives/, tasks/, bugs/, tech-debt/, processed/
  kanban/            README.md, 1-backlog/ 2-todo/ 3-doing/ 4-review/
                     5-testing/ 6-staging/ 7-done/ blocked/
  roadmap/
  tracking/          progress.md, decisions.md  (+ rup-log.md, written on use)
```

Also added to the project root (text kept, block added once): `CLAUDE.md` and
`AGENT.md` get a "RUP skills — which one to use" block between
`<!-- rup-skills:start -->` and `<!-- rup-skills:end -->`.

Other documentation directories detected next to `.context/`: `.specs`, `.spec`,
`.doc`, `.docs`, `docs`, `doc`, `documentation`, `specs`.
