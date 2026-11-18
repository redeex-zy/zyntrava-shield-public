# Security policy — Zyntrava Shield

## Supported experimental version

**0.9.1a1** is the version currently accepted for experimental security review.
This repository is a **public source-only developer preview**. There is no supported
stable/production release, response-time commitment or promised support lifetime.
Independent adversarial security auditing is incomplete. No security tool guarantees
protection. See [current preview status](docs/release-readiness.md).

## Report privately

Use **[Report a vulnerability on GitHub](https://github.com/redeex-zy/zyntrava-shield-public/security/advisories/new)**
or email **[zyntrava.security@gmail.com](mailto:zyntrava.security@gmail.com)**.
Do not disclose vulnerability details in public issues, discussions or pull requests
before coordinating a private reporting and disclosure plan.

**Native GitHub reporting is enabled.** On 18 November 2026, the setting returned
`enabled: true` and an unauthenticated check of Security → Advisories found the
**Report a vulnerability** option. This verifies enablement and the public entry
point, not end-to-end report submission, receipt, reply, access controls or delivery.
GitHub security-report notification preferences remain unverified.

**Email operation is owner-confirmed.** The owner verified receipt from another
account and delivery of a reply to the original sender, and confirms Gmail
notifications, Google 2-Step Verification and GitHub App permission review. These
are owner attestations, not independent inbox/account inspection. Mailbox delegates,
forwarding and unauthorized-user access tests have not been reported complete.
Ordinary email is not end-to-end encrypted: start with minimal redacted text and
agree a protected exchange before sending sensitive material.

See [reporting setup and remaining verification steps](docs/security-reporting-setup.md).
An enabled channel is not independent certification or a guarantee of confidentiality.

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
CI enforcement is not validated. GitHub App permission review is owner-confirmed,
without an independent app-access audit. See the
[dependency assessment](docs/dependency-advisory.md) and
[release gates](docs/release-readiness.md).

## What to include in a private report

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

The intended coordination process is to acknowledge privately,
reproduce and assess impact, agree remediation/disclosure with the reporter,
add regression tests, share a proposed fix privately and credit the reporter only
with consent. No response deadline, bounty, legal safe harbor or guaranteed fix
is offered. No confidential report should enter general issue templates or public
release notes before coordination. The public source preview does not authorize
deployments, account access or broader testing. Reporting settings do not establish
independent security certification.
