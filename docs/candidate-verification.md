# Historical sealed-candidate verification — 17 November 2026

The measurements below belong to the preserved predecessor. They are not relabeled
as executed for this Apache candidate. Current exact-source results, raw logs and
archive hashes are supplied in the adjacent delivery VERIFICATION-MANIFEST.json.
License application is described in [its record](license-application.md).


This record concerns the selected 0.9.1a1 source candidate, not the full private
research tree. Baseline: `7e3e3ee55626525a62d13e45934368fb87c52928`.
All 51 selected Python source modules match that baseline byte-for-byte. Packaging,
documentation, test selection and the dashboard dependency patch are separate.
The adjacent source inventory and complete-file manifest identify the sealed bytes.

| Check on the exported source | Observed result |
| --- | --- |
| Windows 11 build 26200, Python 3.13.18 regressions | 190 passed, 3 skipped; one Tk finalizer warning |
| Ubuntu/WSL2 Linux 6.18.58.1, Python 3.13.18 regressions | 190 passed, 3 skipped |
| Fresh Windows and native-Linux venv: hashed dependencies, source install, scripted SDK exercise | Passed; clean environments are venvs, not clean OS VMs |
| Installed scripted SDK connection | Allowed read, denied private read, allowed continuation observed |
| Qwen3-4B Windows neural demonstration, seed 9026 | Two tasks completed; one activated goal proposed and rejected; zero observed forbidden/duplicate effects |
| Dashboard TypeScript and Vitest | Passed; six unit tests |
| Dashboard Next.js static build | Passed after dependency patch |
| Authenticated Chromium journey | Passed: actual lab jobs, approval, policies, filtering, exports, settings, unavailable/disconnected states |
| Selected axe/mobile checks | No automated violations in tested state; no full accessibility certification |
| Ruff/format, strict mypy, Bandit | Passed on selected source; Bandit reported no issues with existing explicit suppressions retained |
| npm dependency audit | Initially one moderate Next.js advisory; patched 16.4.3 to 16.4.6; final audit zero known vulnerabilities |
| Python dependency audit on Linux | Zero known vulnerabilities; unpublished project itself skipped because absent from PyPI |
| Python dependency audit on Windows | Not completed: host application control blocked a tomli compiled extension; controls retained |
| SDK wheel/source builds and member inspection | Source-only selection; no model, UI bundle, database, environment or installer included |
| Git-less sdist exclusion regression | Passed with uv on PATH, including synthetic built-UI/private-state markers |
| Included evidence hashes and execution-aware regrade | Reference and new candidate run agree with saved grades |
| Historical source-backed replay | First-pass action effects matched for all recorded arms of trace-20261028T143549Z-ceb71562; private archived source was used, not a public reproduction claim |
| Frozen evidence integrity | Existing reviewer/desktop/demo archives preserved; corpus and selected source hashes unchanged |

## Skips, failures and setup differences

Windows skips: privileged symlinks, POSIX handle-relative race regression and
legacy opt-in live inference. Linux skips: Windows Tk, Windows junction and legacy
opt-in inference. Actual Qwen inference ran separately on Windows; no Linux neural
run is claimed. The Tk finalizer warning is retained as a limitation, not hidden.

The first standard Windows venv bootstrap failed during ensurepip; a direct retry
completed without changing security controls. First pytest before dashboard build
and without uv on PATH yielded 182 passes, eight failures and three skips: seven
missing-UI desktop prerequisites and one missing build tool. The documented build/
PATH prerequisites resolved them. A standalone packaging rerun without uv failed
again; it passed with the documented prerequisite. Initial formatting issues in
new packaging/docs-check scripts were corrected. These are not baseline engine defects.

A first WSL copy under /tmp disappeared between WSL invocations; it is not counted
as a completed install. One subsequent shell failed its directory/quoting setup
and was stopped; those attempts are not passes. The successful isolated venv/source
copy used persistent native /var/tmp and fail-fast commands.

The first neural attempt exited during runtime startup and produced no task rows.
That failure remains in the private raw record. A separate startup diagnostic
reached readiness. One new attempt then ran the unchanged two tasks/seed/settings;
no seed, prompt, policy, budget or grader was tuned. The cause of the transient
startup exit is not proven. Do not discard startup failures when judging reliability.

The successful neural run identifies source checkpoint
`d8f940b8d12a7f00144236fa3a7f941a292d2895`, with its original dirty-state field.
Both complete rows and messages are retained in
[candidate evidence](../evidence/candidate-qwen-20261117/evidence.json).
The sanitized four-file package hash is
`0c59b6f3cbb9f23812c65a87d6e7f6cb708365167a88826b055eed28ec342902`.
The separate [historical reference](preview-results.md) is not overwritten.

## Performance and limits

The local Chromium journey measured 25 authenticated overview round trips: median
4.95 ms and p95 8.06 ms, unthrottled on this machine. The sum of gzipped static JS
was 184,997 bytes, below the 256,000-byte budget. These are local measurements,
not field Core Web Vitals or a cross-machine performance guarantee.

Docker Desktop's engine pipe was unavailable and WSL integration unavailable.
No new container/isolation validation, OS image CVE audit, hosted GitHub CI run,
full screen-reader assessment or independent adversarial audit is claimed.
No security control was disabled. Fresh installs use normal publisher package
downloads and the existing hash-pinned dependency set; model assets stay separate.

Use [reproduction instructions](reproducibility.md), CONTRIBUTING and the
machine-readable verification manifest. Private raw logs and historical audit
material are retained for the owner, excluded from the public source ZIP.
