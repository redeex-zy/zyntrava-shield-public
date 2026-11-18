# Contributing

Start with the [quickstart](docs/developer-quickstart.md) and
[synthetic exercise](docs/contributor-exercise.md). This is a public, experimental
source preview. Open a focused issue for a non-sensitive bug or propose a small pull
request with reproduction details. Report security issues privately through
[SECURITY.md](SECURITY.md). Use only dummy data and owned loopback services.

Review and trust the exact source/configuration before building or running any
script, including local PR/fork copies. Use a disposable workspace without personal
data or privileged credentials. A branch name, hash or acknowledgement does not
make unreviewed code safe. All prepared CI is manual-only; an operator must review
the main commit and enter its full SHA plus trusted-source acknowledgement. The
guard runs before checkout; failed validation is not a passed build. Opening a
pull request does not trigger this workflow. Hosted enforcement is not validated.
Contributing does not authorize deployment, package publication or use of credentials.

For the complete selected test suite use Python 3.13, uv 0.13.6 on PATH,
Node 24.21.0 and the committed locks. Build the dashboard **before** pytest:
desktop/backend tests intentionally require real built dashboard assets.
The SDK-only first run in README does not need Node.

```sh
uv sync --locked --extra agent
npm --prefix apps/dashboard ci --ignore-scripts
npm --prefix apps/dashboard run build
uv run --no-sync pytest -q
uv run --no-sync ruff check src tests scripts examples
uv run --no-sync ruff format --check src tests scripts examples
uv run --no-sync mypy src/zyntrava
uv run --no-sync bandit -r src
uv run --no-sync pip-audit --local
```

On Windows use `npm.cmd` if PowerShell restricts npm.ps1. Never change execution
policy to run it. Browser checks use `npm --prefix apps/dashboard run test:e2e`;
set ZYNTRAVA_TEST_PYTHON to the absolute environment interpreter if not using the
default `.venv`. Playwright's browser must be installed through its official setup.

Point UV_PROJECT_ENVIRONMENT at an approved standard venv when generated redirectors
are blocked. Never disable host protection. The pip quickstart needs no uv or Node.
Frontend changes additionally need Node 24.21.0 and the dashboard's npm ci,
typecheck, test, build and audit commands. The curated public source preview has
an explicitly selected portable test suite; full research regression counts are separate.
The six frontend unit tests use Node's built-in runner and TypeScript stripping;
keep new unit test files in the explicit package.json test command. See the
[dependency exposure assessment](docs/dependency-advisory.md) before running builds.

Keep changes small. Include actual commands, OS/runtime versions, passes/skips/failures
and affected boundaries. Security regressions must verify side effects, not just
verdict text. Do not broaden permissions, suppress audit failures or enable failed
recovery candidates to improve scores. Preserve frozen corpora and original evidence.

Preregister research contracts/budgets/grading. Separate development and held-out
cases; record authorship and freeze hashes before evaluation. Nonactivation is not
blocking, repetition is not attack diversity, and final prose is not completion.
Report negative results and uncertain effects. Do not invent novelty or comparisons.

Contribute only material you have permission to share; preserve provenance/notices.
Original contributions use Apache-2.0 as described in [license scope](docs/license-scope.md).
No signed contributor agreement or assignment is inferred; disclose upstream material. Never submit real
credentials, personal data, operational databases or unauthorized targets. Follow
[the code of conduct](CODE_OF_CONDUCT.md) and use [SECURITY.md](SECURITY.md) privately
for vulnerabilities. [Three beginner issues and two research opportunities](docs/preview-contribution-issues.md)
are drafts only; none have been posted.
