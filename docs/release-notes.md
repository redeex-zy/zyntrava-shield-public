# Source-preview notes — 0.9.1a1

The experimental source preview is public. These notes describe its capabilities;
no GitHub Release, published package or production service was created. See
[current status](release-readiness.md).

Zyntrava Shield evaluates registered AI-agent tool calls against operator-defined
permissions before execution. The preview includes a Python SDK, Pydantic AI
adapter, dummy-data first-run exercise, optional pinned Windows Qwen demo and an
authenticated localhost dashboard built from source.

The source candidate excludes private development history, operational state,
models, third-party benchmark copies, compiled UI, installers and video assets.
Package builds are SDK-only and do not silently absorb a local dashboard build.
Authorization/audit/approval/session behavior remains unchanged from the reviewed
developer baseline. Failed experimental recovery candidates are not default behavior.

The complete included reference demonstration contains one clean and one injected
Qwen task. Its activated private-file proposal was rejected before execution and
both authorized reports completed. This small developer-authored example is not
independent validation or a success rate; earlier negative results remain relevant.
Use the candidate's verification record for newly executed outcomes, including failures.

Known limits: registered tools only; trusted Python process/operator/OS; no general
OS sandbox; unprotected raw model/provider logs; unreliable recovery; mutable
local auditing; no general exactly-once side-effect guarantee; no validated public,
real-data or multi-user production deployment. No superiority or novelty claim.

Contributions: improve onboarding diagnostics, expand independent synthetic attacks
with execution-aware grading, and test dashboard accessibility/disconnected states.
See CONTRIBUTING and SECURITY before sharing data or exploit details.


## Licensing, reporting and trusted-build restrictions

The creator approves Apache-2.0 for cleared original source, retains the research
name provisionally without trademark clearance, and conditionally accepts the
bundled Next.js/picomatch residual only for reviewed trusted builds, manual CI and
source-only distribution. The upstream vulnerability remains unpatched. The
previous Vitest chain was removed with all six tests/21 assertions retained.

The new CI has no automatic trigger and validates a reviewed main commit plus
explicit acknowledgement before checkout. It retains tests/audits and read-only
contents permission, disables uv caching and contains no upload/release step.
No hosted workflow validation is claimed. GitHub private reporting is enabled;
its setting/public link are verified, email receipt/reply are owner-confirmed and
end-to-end native delivery/notifications remain unverified. The source excludes compiled
UI, dependencies/runtime binaries, installers and weights; the generated Next.js
declaration retains its MIT notice. Source licensing does not clear other bundles.
The owner authorized publication of the source preview. This does not authorize
packages, binaries, deployments or announcements. Follow [SECURITY.md](../SECURITY.md)
for confidential reports; preserve the remaining experimental and dependency warnings.
