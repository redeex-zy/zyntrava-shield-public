# Security policy — experimental private-staging source candidate

## Versions and scope

Only the exact 0.9.1a1 candidate identified in `SOURCE-INVENTORY.json` is under
local review. There is no supported stable/production release or promised support
lifetime. Independent adversarial auditing is incomplete. No tool guarantees protection.

In scope: registered tool request validation and default-deny authorization, file
and numeric-loopback HTTP scopes, operator approvals, audit-before-effect, API
credential/session binding, controlled release boundaries and the returned-final-
answer gate of the supported Pydantic AI adapter. Reproduce using dummy data and
owned local receivers; report actual unauthorized effects separately from proposals.

Outside coverage: arbitrary native/shell/MCP/Python tools, unrelated agents,
compromised host/operator/OS, provider transport, raw framework messages, tracing,
external logs and persistent external agent memory. This SDK is not OS isolation.
There is no validated public management, real-data, multi-user or production setup.
Task recovery is unreliable; a denial does not prove the user task completes.

## Confidential reporting — RELEASE BLOCKER

**No confidential reporting destination has been established or verified for this
candidate. Do not publish a sensitive report as a public issue, and do not guess a
personal email address.** A private reviewer must first agree a verified channel
with the creator through an already established relationship.

Before publication the creator must configure and test a confidential route,
replace this paragraph with its exact verified destination, and verify notifications.
GitHub private vulnerability reporting is documented for public repositories and
may be unavailable in private staging. It has **not** been enabled or verified here.
The proposed private-staging alternative is a dedicated private reporting repository
limited to the creator and the specific consenting reviewer, with text-only synthetic
reports until receipt/reply, notifications and unauthorized-access tests pass.
Do not post vulnerability details in general staging issues accessible to all reviewers.
No actual reporting repository or address has been created, selected or verified. Follow the [owner setup procedure](docs/security-reporting-setup.md).
An ordinary public issue template is not confidential reporting.

Use [the report template](reviewer/VULNERABILITY-REPORT.md). Include revision/package
hash, supported integration/configuration, claimed boundary, minimal synthetic
steps, actual proposed and executed actions, receipts/redacted audit identifiers,
expected behavior, observed impact, reproducibility and failures. Do not include
real secrets, personal data or live targets.

## Coordination and authorized testing

Proposed process: acknowledge privately when possible, reproduce in a disposable
local workspace, agree impact and remediation, add side-effect regression tests,
share a fix privately, then coordinate publication and researcher attribution with
consent. No response-time guarantee, bounty, legal safe harbor or independent
certification is offered. Never test a third-party service or real account using
this project's examples. Do not perform real payments, disable host security,
reset a classified session or automatically retry an uncertain side effect.

The creator must approve the final policy and establish the channel before release.


## Accepted scope and build restriction

The creator conditionally accepts the known bundled Next.js/picomatch build-time
residual only for this limited source-only preview, contingent on trusted reviewed
builds, manual-only CI and exclusion of binary/model/compiled distributions. This
does not fix the upstream vulnerability or authorize public publication. Build no
unreviewed source/configuration and supply no privileged credentials to builds.
The prepared workflow requires a matching reviewed main SHA and explicit trust
acknowledgement before checkout. Hosted CI and all reporting channels remain
unverified. See the dependency assessment and current release decision.
