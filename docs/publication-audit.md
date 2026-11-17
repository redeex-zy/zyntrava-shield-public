# Public source audit and selection

This is developer-assisted release preparation, not independent security auditing
or legal clearance. Publication remains blocked on creator decisions and a verified
confidential reporting channel. Use a **new selected repository**, never change the
private evidence repository's visibility or rewrite its history.

`SOURCE-INVENTORY.json` identifies every explicitly selected baseline/preparation
file and its content hash. The adjacent final COMPLETE-FILE-MANIFEST.json covers
all shipped files including internal inventories; it excludes its own sidecar to
avoid self-hash recursion. Private audit material and the complete excluded-path
inventory are separate owner-only deliverables, never part of the public ZIP.

## Included after inspection, subject to creator approval

Supported broker/adapter/API/CLI source; synthetic lab/grading helpers; portable
regression tests; dashboard **source**; Python/npm locks; local model manifests;
SDK examples; synthetic corpora; contributor/report templates; generic-path docs;
sanitized complete reference evidence and provenance. Existing optional operator-
only synthetic recovery research code remains explicitly experimental; the default
agent example does not enable it. Failed checkpoint/separated-feedback candidates
are not included.

## Excluded and preserved privately

All old Git history/remotes/branches; private raw results and audit copies; manual
tests; model weights/runtime ZIPs/DLLs; environments; node_modules; compiled UI;
desktop installers; reviewer archives; operational databases/tokens/configuration;
unrelated website/video assets; third-party benchmark copies; private-evidence
analysis tests. The old frozen cases/results and their original hashes are not edited.

## Review method and limits

The release record includes Gitleaks source/history scans and a reachable-blob/
nested-archive review, manual classification of scanner candidates, machine-path/
email/configuration searches, distribution member inspection and dependency/license
inventories. Deliberate synthetic markers and content hashes are classified by
context, not silently reported as real keys or blanket-suppressed. A scanner pass
does not prove that secrets or licensing problems do not exist. Any skipped bounded
history items and raw reports remain documented privately.

The prepared source has numeric-loopback startup, ephemeral operator/agent bearers,
origin/host checks, default-deny tools, mandatory auditing and separate bound
sessions. The operator/process/OS remain trusted; mutable local audit storage,
resource exhaustion, exactly-once effects, recovery reliability and public/multi-user
deployment are not solved. No broad security or independent-audit claim is allowed.

The model manifests omit unnecessary historical RAM/VRAM snapshots; their pinned
model/runtime identifiers and hashes remain. Creator name and Morocco attribution
are intentionally supplied public project identity. No personal address, private
contact, fabricated organization or operational machine path is added.

See [candidate checks](candidate-verification.md), [license decisions](licensing-decision.md),
[confidential reporting](security-reporting-setup.md), [release decision](release-readiness.md).

## Observations from this preparation

The initial private-history inventory examined 93 reachable commits, 1,242 unique
blobs, 55 archive entries and 16 blobs larger than 1 MiB. Its bounded scan reported
no skips. Gitleaks 8.30.1's unfiltered all-ref scan reported 92 scanned commits and
eight findings; the different tool counts are retained verbatim. Seven findings
were source SHA-256 values, recomputed against the referenced committed files;
one was an explicit dummy-secret test fixture. A separate materialized-object
scan reported the same eight; 4,195 nested-archive text views reported zero findings.
The initial unfiltered candidate scan reported only the same dummy fixture.
These are classified findings, not a claim that the scanner returned zero alerts.

Manual privacy review classified 18 pattern candidates: historical machine paths
in reports/logs; negative-test/path-validation expressions; synthetic URL fixtures;
prior scanner output in a private QA archive; and an unrelated font's public
copyright/contact notice. Private history and video/font files are not exported.
Git identities observed in the reviewed history were local placeholder identities;
this does not prove legal ownership. New preparation material is scanned separately
in the final clean snapshot; no old history is rewritten to remove the findings.

The baseline package hook absorbed a locally built UI into distributions. The
candidate hook is SDK-only, and a synthetic exclusion regression now covers built
UI as well as state/dependency trees. This avoids accidental compiled-asset delivery.
The npm audit initially identified a moderate Next.js issue, patched from 16.4.3
to 16.4.6 in candidate metadata/lock. See the
[publisher advisory](https://github.com/advisories/GHSA-mfr8-8qww-v76h).
The dashboard is statically exported; affected cached server rendering is not
used, but the vulnerable dependency pin was still updated. No automatic broad
dependency upgrade or weakened security policy was applied.

| Publication category | Materials and action |
| --- | --- |
| Technically suitable, subject to release gates | Explicitly allowlisted SDK/adapter/broker/API source, portable tests, dashboard source, synthetic corpora/examples, sanitized complete evidence, generic-path docs and dependency locks |
| Must be finalized first | SECURITY.md's real verified private destination; final identity/naming decision and new source checksum approval |
| Keep private/excluded | Existing history/branches, raw QA/model traces and databases, operational state, original reviewer/installer ZIPs, model/runtime binaries, third-party benchmark copies, videos and unrelated assets |
| Owner/legal questions | Any subsequently discovered ownership restriction; naming conflicts; contributor policy; future binary/model redistribution obligations |

The [license metadata inventory](dependency-licenses.json) covers 72 installed
Python distributions and 178 npm lock entries, with no missing license labels.
Labels are not legal clearance: actual notices and scope still matter, especially
MPL, CC-BY and LGPL/platform components. Source-only export does not redistribute
these dependencies' binaries, models or node_modules.

## Qualified license application update

The creator has now confirmed AI-assisted original authorship to the best of their
knowledge, no known other human copyright contributor, and the qualified Apache-2.0
grant. See [the application record](license-application.md). This update closes the
pending original-source choice without treating Git identities as title evidence.
The Next.js template's full MIT attribution is retained separately. Prior audit
counts above remain historical observations. Publication still requires a verified
confidential reporting channel and approval of the new checksum/action.

## Fresh dependency-audit limitation

The new audit reports one unpatched high-severity picomatch ReDoS advisory across
five frontend development dependency entries. The publisher advisory lists no
patched version, and the registry's latest is 4.0.7. The old zero-finding audit
above is historical, not a current result. No forced Vitest downgrade or ad-hoc
dependency patch was applied to make the check pass. See
[the upstream advisory](https://github.com/advisories/GHSA-fc5q-39xc-vjpf).


## Subsequent dependency assessment (separate candidate)

The five-entry development-chain finding above remains an unchanged observation
for the sealed predecessor. The new candidate replaces Vitest with Node's built-in
runner, retains the six unit tests, and has zero known findings in fresh full npm
audits. Manual inspection also found vulnerable picomatch code bundled inside
Next.js; that residual is **not** cleared by the npm result. No upstream patch or
general absence of vulnerable code is claimed. See [the full exposure assessment](dependency-advisory.md).
The engine, adapter, permissions, default recovery and saved evidence are unchanged.


## Subsequent private-staging preparation

The creator now approves the cleared original-source Apache grant, retains the
name provisionally and conditionally accepts the bundled Next residual under
trusted-build/manual-CI/source-only restrictions. Public publication remains
unauthorized. A separate candidate applies manual-only CI and accurate reporting
plans without changing engine code, research evidence or the sealed predecessor.
Current decisions and private reporting alternatives are in release-readiness and
security-reporting-setup. No actual reporting channel, remote or hosted validation
is claimed; historical audit figures above are not relabeled as new measurements.
