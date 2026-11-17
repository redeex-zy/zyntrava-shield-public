# Security policy — Zyntrava Shield experimental source

## Supported research version

**0.9.1a1** is the only version currently accepted for experimental security review.
The approved staging baseline is `49402a1c615ebadf692c927845cb14e9d7581606`.
This policy update is prepared separately; it does not replace that sealed source
candidate or authorize publication. There is no supported stable/production release,
response-time commitment or promised support lifetime. Independent adversarial
security auditing is incomplete. No security tool guarantees protection.

## Confidential reporting: NOT VERIFIED — publication blocker

**There is currently no verified confidential reporting destination. Do not submit
sensitive vulnerability details to GitHub issues, discussions, pull requests or
an assumed personal email address. Do not disclose vulnerability details publicly
before coordinating a private reporting channel and disclosure plan.**

On 17 November 2026, authenticated owner/admin checks of the PRIVATE staging
repository returned HTTP 404 for both the native private-vulnerability-reporting
enable request and its subsequent setting read-back. Native reporting was not
successfully enabled or verified. Both project repositories remain PRIVATE.
GitHub's native feature is documented for public repositories; this project must
not become public simply to obtain it.

The creator has confirmed that no dedicated, verified security-reporting inbox
exists yet. No address is advertised, no test email has been sent, and no external
report submission/receipt/reply or notification delivery has been verified.
A private source issue tracker is not an external confidential reporting channel:
outsiders cannot normally use it, and source collaborators may see its issues.

Until a channel is verified, retain any findings privately. Reviewers who already
have an established, trusted relationship with the creator may use that relationship
to agree a channel first; it is not an advertised general intake mechanism. The
[owner setup and verification procedure](docs/security-reporting-setup.md) explains
the remaining email setup and future native-reporting steps. It contains no live
reporting address. A verified destination must be added here before public release.

## Security boundaries in scope

- Registered tool-call validation and default-deny authorization in the broker.
- Supported file-resource scopes and numeric-loopback HTTP destination/request scopes.
- Operator approvals, expiry and single use; audit-before-effect enforcement.
- API credential/session binding and supported controlled-release boundaries.
- The returned-final-answer gate of the supported Pydantic AI adapter.

Report actual unauthorized side effects and data exposure separately from proposed
actions or suspicious text. A rejected proposal does not prove task completion.

## Known limitations and exclusions

Arbitrary unregistered/native/shell/MCP/Python tools, unrelated agents, compromised
hosts/operators/OS accounts, provider transport, raw framework messages, tracing,
external logs and persistent external agent memory are outside these boundaries.
The SDK is an in-process broker, not system-wide protection or production OS isolation.
Public management, real-data and multi-user production deployments are not validated.
Agent recovery after denial remains unreliable. Experimental recovery mechanisms
are not approved for default use. The project has no independent certification,
universal prompt-injection-prevention or trademark-clearance claim.

The known Next.js/vendored-picomatch advisory **GHSA-fc5q-39xc-vjpf** remains a
conditionally accepted build-time residual for this source-only preview. Build
only reviewed, trusted source/configuration without privileged credentials; use
manual-only CI and exclude binary, compiled-dashboard, runtime and model distributions.
The workflow requires a reviewed matching main SHA and explicit trust acknowledgement
before checkout. These restrictions do not fix the upstream vulnerability. Hosted
CI enforcement and account-wide app access are not fully validated. See the
[dependency assessment](docs/dependency-advisory.md) and
[release gates](docs/release-readiness.md).

## What to include once a private channel is verified

Use the [vulnerability report template](reviewer/VULNERABILITY-REPORT.md). Include:

- Version, exact revision/package hash and supported integration/configuration.
- Affected trust boundary, expected behavior, concrete impact and suspected severity.
- Minimal reproducible commands with synthetic data and owned local services.
- Separate evidence for attack encountered/activated, forbidden proposal, policy
  rejection, actual execution/effects and legitimate task completion or failure.
- Duplicate or uncertain effects, redacted audit identifiers, environment/model
  versions, reproducibility limits and negative results.
- A permitted private reply method and researcher attribution preference, if desired.

Do not send credentials, personal documents, production databases, private conversation
history, live targets or executable attachments. Start with minimal redacted text.

## Responsible testing and coordinated disclosure

Test only systems you own or have explicit authorization to assess. Use disposable
local environments, dummy files/credentials and owned loopback receivers. Do not
test third-party services or real financial accounts, perform real payments,
disable host protections, reset classified sessions or automatically retry uncertain
side effects. Never expand testing scope without fresh authorization.

Once private intake works, the intended process is to acknowledge privately,
reproduce and assess impact, agree remediation/disclosure with the reporter,
add regression tests, share a proposed fix privately and credit the reporter only
with consent. No response deadline, bounty, legal safe harbor or guaranteed fix
is offered. No confidential report should enter general issue templates or public
release notes before coordination. Reporting setup and public publication remain
separate owner decisions.
