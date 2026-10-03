## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use their default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Mutation testing

Mutation testing has two client adapters: OMP `/mutation-test` in `.omp/skills/mutation-test/` and GitHub Copilot CLI `/omp-mutation-test` in `.github/skills/omp-mutation-test/`. Keep their five role contracts aligned; OMP agents use `task`/`hub`, while Copilot agents use `.github/agents/` and the native `agent` tool.
