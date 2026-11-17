# Zyntrava Shield

**Intelligence Deserves Protection.**

Experimental AI-agent tool authorization by **Mohamed Reda Mejhed, Morocco**.
**0.9.1a1 private-staging source candidate — not published, independently audited or
production-ready.** Apache-2.0 is approved for cleared original source. The provisional
name has no trademark clearance. Confidential reporting is unverified and public
publication is not authorized. See [release status](docs/release-readiness.md).

Zyntrava checks a proposed registered tool call against operator-defined permissions
**outside the language model**, before allowing its executor to run. Untrusted
documents cannot grant permission. A rejected action and a completed user task are
different outcomes; the examples measure both.

| Protected in the supported adapter | Outside this security boundary |
| --- | --- |
| Registered file reads/writes and scoped numeric-loopback HTTP tools | Unregistered/native/shell/MCP tools and arbitrary Python callbacks |
| Default-deny authorization, exact request validation, approvals and pre-effect audits | Other agents/apps, a compromised host, operator or OS account |
| Returned final text through the adapter's output validator | Provider transport, raw transcripts, external tracing and logs |

This is an in-process broker, **not system-wide protection or an OS sandbox**.
Use dummy data and owned localhost services only. Recovery after rejection remains
unreliable. Experimental feedback/separation candidates are excluded; no recovery
controller is enabled in the default example. Public, real-data, multi-user and
internet-facing management deployments are unsupported.

## First run — no GPU, account or paid API

Use Python **3.13**, from this source directory. The package is not claimed to be
on PyPI. Windows PowerShell:

```powershell
python -m venv .state/preview-env
.state/preview-env/Scripts/python.exe -m pip install --require-hashes -r requirements-preview.txt
.state/preview-env/Scripts/python.exe -m pip install --no-deps .
.state/preview-env/Scripts/python.exe examples/preview_agent.py --output runs/first-run
```

Linux/WSL (use a native Linux filesystem and a separate environment):

```sh
python3.13 -m venv .state/preview-env
.state/preview-env/bin/python -m pip install --require-hashes -r requirements-preview.txt
.state/preview-env/bin/python -m pip install --no-deps .
.state/preview-env/bin/python examples/preview_agent.py --output runs/first-run
```

This first exercise uses an explicitly **scripted Pydantic AI FunctionModel**,
with real broker/file/localhost effects. It is not neural inference. Expected:
one clean report; one proposed private read rejected before execution, followed
by an authorized report. Check `summary.json`, not the agent's final prose.
Use a **new** output directory every time. [Quickstart and removal](docs/developer-quickstart.md).

## Real model-generated proposals: optional Windows Qwen demo

The pinned local launcher supports Windows, Qwen3-4B Q4_K_M and llama.cpp/Vulkan.
The weights are about 2.50 GB; KV/compute memory is additional. Check free RAM and
VRAM. Assets are downloaded separately and never included in this repository.
Linux neural inference is not validated by this release candidate.

```powershell
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
.state/preview-env/Scripts/python.exe scripts/install-local-model.py --model qwen3-4b
.state/preview-env/Scripts/python.exe examples/preview_agent.py --live --seed 9026 --service-base-port 18870 --output runs/qwen-first-run
```

The clean task reads `public/status.txt` and posts one status-only object to an
owned loopback receiver. The injected input asks for `private/operator.txt` first.
File/network actions in this example are broker-mediated; final answers pass the
adapter gate. There is no alternate shell executor. [SDK connection example and
coverage](docs/developer-integration.md).

Read the separate fields for attack encountered, activation, forbidden proposal,
rejection, actual effects, duplicate effects and legitimate completion. An attack
that never activates is **not** a successful block. Live behavior can vary; preserve
failures. [Methodology and complete reference evidence](docs/preview-results.md).

## Optional authenticated dashboard

The affected Vitest/picomatch development dependency chain has been replaced by
Node's built-in test runner, preserving all six unit tests. Next.js still contains
an unpatched vendored picomatch copy. It is not used by the Python/static-dashboard
runtime; build only trusted source/configuration. A zero-finding npm audit does
not cover that bundled copy. Read the [exposure assessment](docs/dependency-advisory.md)
and [release gates](docs/release-readiness.md). Publication remains unauthorized.

Build only source/configuration you have reviewed and trust, without privileged
credentials or personal files. Do not run unreviewed PR/fork build scripts. The
prepared CI is manual-only and rejects a missing/mismatched reviewed main SHA or
missing trusted-source acknowledgement before checkout; it has read-only contents
permission, no supplied secrets and no upload/release job. Hosted enforcement is
not yet tested. [Staging/reporting procedure](docs/security-reporting-setup.md).

Node 24.21.0 is the tested prerequisite for UI builds and native TypeScript unit tests:

```powershell
npm.cmd --prefix apps/dashboard ci --ignore-scripts
npm.cmd --prefix apps/dashboard run build
.state/preview-env/Scripts/python.exe -m zyntrava init-lab --state .state/dashboard-new
.state/preview-env/Scripts/python.exe -m zyntrava serve --state .state/dashboard-new
```

On Linux use `npm` and the environment's `bin/python`. Open
`http://127.0.0.1:8765/app/` and use the ephemeral operator bearer printed in your
own terminal. Never share or record it. Ctrl+C stops the service. Opening the UI
does not connect an agent; it has a separate synthetic workspace. Packages built
from this candidate intentionally **do not bundle** compiled UI or installers.

## Evidence, limitations and contribution

The included reference run is one developer-authored two-task Qwen demonstration:
one activated private-read proposal was rejected/not run, and both reports completed
with no observed forbidden/duplicate effects. It is not an independent benchmark or
a general recovery success rate. Historical utility remains 45/54 for its original
contract; negative recovery results are not replaced. No novelty or advantage over
Pipelock is established. [Candidate verification](docs/candidate-verification.md).

- [Architecture and trust boundaries](docs/developer-architecture.md)
- [Threat model](docs/threat-model.md) and [known limitations](docs/known-limitations.md)
- [Reproduce evidence and tests](docs/reproducibility.md)
- [15-minute contributor exercise](docs/contributor-exercise.md)
- [Troubleshooting](docs/developer-troubleshooting.md)
- [Contributing](CONTRIBUTING.md), [conduct](CODE_OF_CONDUCT.md), [security](SECURITY.md)
- [Licensing decision and obligations](docs/licensing-decision.md)
- [Audit and included/excluded source inventory](docs/publication-audit.md)

## License

Original copyrightable Zyntrava contributions are licensed under
[Apache License 2.0](LICENSE), only to the extent the creator has authority to
grant the rights. See [NOTICE](NOTICE) and [the approval record](docs/license-application.md).
The creator reports AI-assisted authorship; no exclusive ownership of every
generated element or factual result is asserted.

Third-party material retains its own license. In particular, the generated Next.js
type declaration retains MIT attribution: [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
Models, runtime binaries and dependencies are obtained separately and are not
redistributed in this source-only preview. [Scope and exclusions](docs/license-scope.md).

The working name has **no trademark-clearance claim**. No public repository URL,
certification, registered company, endorsement or production readiness is implied.
