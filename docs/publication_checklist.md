# Stage 8 / M2 closure and publication review

Recorded 2026-09-21. Stage 8 implementation is complete; publication is not yet
cleared. M2 freezes the current portfolio milestone, not a claim of operational
readiness. No push, deployment, history rewrite or Stage 9 feature work occurred.

## Local results

| Check | Result |
| --- | --- |
| `python -m ruff check .` | All checks passed |
| `python -m pytest -v` | 268 passed, 1 existing cache warning, 6.33 s |
| `python -m pytest --cov=sa_engine --cov-report=term-missing` | 268 passed, 1 cache warning, 8.05 s |
| Statement coverage of `sa_engine` | 97.5%, 762 statements, 19 missed |
| Synthetic demo | JSON, text and map generated successfully |
| Clean isolated copy / fresh venv | Dependency install, Ruff, 268 tests (16.95 s, no warnings), demo passed |
| Streamlit | 1.64.0 import, UI AppTest coverage and headless server startup passed; process stopped |
| GitHub Actions | Workflow prepared/reviewed; no remote execution claimed |
| YAML | Structure reviewed manually; dedicated YAML parser unavailable |

The clean-copy check used Python 3.14.2 on Windows, with a fresh `.repro/venv`
and allowlisted source copy in `.repro/source`. It excluded Git, `.env`, existing
runs/cache and the original venv, removed inherited provider credentials and
PYTHONPATH, and disabled dotenv loading. Dependencies came only from
`requirements.txt`. The ignored reproduction environment is retained locally.
Ubuntu CI has not been exercised here. Transitive dependencies are not fully locked.

Coverage is statement coverage of the package, not browser rendering, branch
coverage or a certification measure. No artificial tests were added to increase
it. Ruff changes were limited to import cleanup; domain rules did not change.

## Secret and runtime-data review

A redacted heuristic scan of 52 public-source candidate text files found no
private-key/token/provider-credential candidates and no occurrences of local
provider credential values. Values were never printed. The scan excluded local
environments, runtime data, Git internals and `.env` itself; `.env` values were
only compared internally. This is a scoped worktree check, not proof of absence.
The only subsequent edits were documentation, including this record.

Git status, tracked-file and history commands failed the repository ownership
check, including a command-scoped safe-directory attempt. **Tracked files and
history have not been cleared for publication.** No global trust configuration
was changed. Existing `.git/info/exclude` contained no additional active rules.

`.gitignore` now excludes local secrets/configuration, runtime bundles/cache,
JSONL history, environments and tool output. `.env.example` contains empty values.
Synthetic JSON fixtures remain available. Ignoring a path does not untrack it or
remove an earlier committed copy.

## Remaining manual publication gates

- [ ] Restore legitimate Git access in Anna's trusted environment. Inspect
  `git status --short`, `git ls-files` and `git log --all --name-only --format=`
  for `.env`, credential/token files, `runs/`, raw captures and live history.
- [ ] Run a trusted secret scanner over the index and full history with redacted
  output. Review findings locally; never paste raw matches or credentials into logs.
  If a genuine secret was committed, revoke/rotate it first and plan explicit
  history cleanup. Deleting today's file is insufficient. No destructive rewrite
  is authorized by this milestone.
- [ ] Reopen current OpenAIP official terms: indexed official license evidence
  was available, but direct access returned 403. See [data sources](../DATA_SOURCES.md).
- [ ] Confirm intended live use complies with OpenSky's official terms and obtain
  required permission. Keep live datasets/reports private; authoritative comparison
  and live API smoke checks remain pending and separate from software tests.
- [ ] Capture/review the actual [synthetic screenshot](assets/README.md), retaining
  labels, limitations and basemap attribution. No browser capture was available here.
- [ ] Review the source-code MIT notice and third-party provenance; no vendored
  third-party implementation was identified in the inspected source.
- [ ] Review the final diff and public file list. Run GitHub CI after an explicitly
  authorized push; local Windows success does not establish hosted Ubuntu success.

Only after those checks should Anna decide to publish. No remote publication is
automatic. Existing aviation/data limitations remain in the root README.
