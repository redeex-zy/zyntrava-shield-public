# Known limitations

- Local v0.9.2 hardening is a review candidate, not a released or audited fix.
  Uncertain tool dispatch halts the supported session/run; operator reconciliation
  is required. There is no global deduplication across deliberately new sessions
  or trusted applications that start new runs. General exactly-once is not claimed.
- Release reservations persist in the audit database, not a tamper-proof external
  service. Deleting/rolling back state, changing workspace identity or resuming old
  classified history requires operator review. Legacy state cannot safely infer
  unused budgets from missing audit rows and is not auto-migrated.
- The strict profile is opt-in and does not support legacy count-send permissions;
  it rejects that combination explicitly. Classification remains operator-owned,
  and its diagnostics do not discover every secret or establish arbitrary DLP.
  See [candidate review and migration](v0.9.2-security-hardening.md).
- Registered broker-mediated tools only. Registering an alternate executor can
  bypass coverage; arbitrary AI agents, shell/native/MCP tools and the OS are not protected.
- Recovery after denial is unreliable. The two-task example does not replace
  original 45/54 utility or negative 0/3 attacked pilot outcomes. Experimental
  separated-feedback/checkpoint candidates are excluded; default recovery is unchanged.
- No independent adversarial audit, certification, universal prevention or superiority
  is established. Developer-assisted checks are not independent validation.
- No public, real-data, multi-user, internet-facing or production service is supported.
  A localhost token authenticates a local operator, not a tenant-isolation boundary.
- Audits are redacted but locally mutable. Raw messages, custom logging and model
  transport remain outside returned-answer gating. Synthetic canary checks do not
  establish arbitrary confidentiality or resistance to timing/repeated-query channels.
- Exactly-once effects, general safe retries, durable recovery and denial-of-service
  resistance are not guaranteed. Unknown effects must not be blindly retried.
- The pinned neural launcher targets Windows/Vulkan. Linux core/SDK regressions are
  tested in WSL, not every Linux distribution; native Linux neural inference is unverified.
- This source candidate does not include Docker launchers, model weights, compiled UI,
  desktop installers, private benchmark snapshots or full historical experiment runners.
  Some retained lab helpers are research internals, not standalone supported integrations.
- The optional Windows desktop source remains experimental. Its existing frozen
  installer is not rebuilt or redistributed by this release preparation.
- Automated axe checks and a mobile/browser journey cover selected criteria, not
  full WCAG conformance or screen-reader certification. Fresh venvs are not clean OS VMs.
- The Vitest/picomatch 4.0.7 development chain was removed without dropping tests.
  Next.js 16.4.6 still vendors the assessed matcher (upstream build pins 4.0.1).
  GHSA-fc5q-39xc-vjpf was withdrawn on 18 November 2026, not fixed by a new release;
  costly patterns remain reproducible. Use only trusted build source/configuration; a clean npm
  audit is not a complete bundled-code audit. No input route from the supported
  Python/static-dashboard runtime was found. See [assessment](dependency-advisory.md).
- GitHub private vulnerability reporting is enabled and its public entry point was
  verified. End-to-end native report delivery and GitHub notification preferences
  remain unverified; email receipt/reply are owner-confirmed. See [reporting status](security-reporting-setup.md).
- Zyntrava Shield is provisionally approved as the public research name; trademark
  clearance remains unresolved. Public source availability is not deployment approval.

See [verification](candidate-verification.md), [security policy](../SECURITY.md)
and [release decision](release-readiness.md) before using or sharing this source preview.
