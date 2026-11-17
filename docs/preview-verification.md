# Executed developer-preview verification

All results are developer-assisted local checks, not independent certification.
Python 3.13.18; application dependencies from the committed uv lock and hashed pip
export. No paid model API or production credentials. The exact private engineering
manifest preserves raw logs, hashes, revisions and failures.

| Check | Observed result |
| --- | --- |
| Starting full Windows suite | 239 passed, 3 skips |
| Full Windows / WSL Linux regression after additions | 247 passed, 3 skips each |
| Selected source export tests, fresh Windows / native-filesystem WSL venv | 77 passed, 1 platform-specific skip each |
| README pip dependency/source setup and scripted exercise | Passed on Windows and native-filesystem WSL |
| First shared-Windows-mount WSL install | Timed out at 300 seconds; incomplete, not counted passed |
| Subsequent tests on that incomplete shared-mount environment | Failed: project was not installed; retained separately |
| Installed Windows dashboard/browser journey | Passed, including approval/completed job, selected axe/keyboard/mobile checks, cleanup and no credential persistence |
| Actual Qwen3-4B demo | Two tasks complete; injected goal activated/rejected; zero observed forbidden/duplicate effects |
| Ruff/format/strict mypy/Bandit, Python dependency audits | Passed; unpublished project itself is not in the vulnerability database |
| Dashboard/website tests/builds, dashboard types/npm audit | Passed |
| Source-backed archived benchmark replay | First-pass action effects matched |
| Source ZIP verification | Bounded regular paths, complete SHA-256 inventory and CRC reads passed |
| Git-less source-distribution build | Initial build included venv/node_modules; fixed with explicit source selection and a synthetic-state exclusion regression |

Full Windows skips: privileged symlinks, POSIX race and legacy opt-in inference.
Full Linux skips: Windows Tk/junction and legacy opt-in inference. Actual Qwen3-4B
was run separately on Windows. Selected source skips are the corresponding
platform-specific symlink/junction case. Fresh venvs are not clean OS VMs.

The recorded live demo ran at source checkpoint e02067b981fed7ba439a74d4f33129a7bf7a0c75.
Its exercise module was subsequently moved to a non-conflicting filename without
changing its bytes; the original historical helper/tests were restored byte-for-byte.
The saved run reports dirty=true; it is not relabeled as a pristine source run.
The manifest checks recorded-module/core/grader bytes against committed checkpoints.
The adapter, broker, policies, grader and default recovery behavior are unchanged.
No repeat-until-success inference was used. Earlier negative recovery evidence
remains authoritative for its own contracts.

No new Docker validation, native Linux neural inference, full screen-reader review,
container OS CVE audit or public GitHub CI run was performed for this documentation/
SDK milestone. Prior Docker research does not establish production isolation.
New source/wheel installation is verified; the frozen desktop installer is preserved,
not rebuilt. Binary/compiled-asset licensing review and a verified private disclosure
route remain prerequisites for publication.

An archive-generation attempt created a valid ZIP/checksum but then failed because
an identical adjacent verifier already existed. That attempt is retained, not counted
as a successful command. The generator now preflights conflicts and reuses only an
identical verifier; a regression covers refusal before writing a conflicting package.
Use only the final candidate paths/checksums in the engineering handoff.

The failed 172 MB distribution remains private for diagnosis. A build's exit code
alone was insufficient: member inspection identified the problem. Corrected builds
are inspected separately; the curated source ZIP never included those directories.
