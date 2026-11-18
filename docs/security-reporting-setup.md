# Confidential reporting: active routes and verification limits

Status checked **18 November 2026** for the public source preview, version **0.9.1a1**.
Use [SECURITY.md](../SECURITY.md) for disclosure scope and report requirements.

## Routes available to researchers

- **[GitHub private vulnerability reporting](https://github.com/redeex-zy/zyntrava-shield-public/security/advisories/new)**
  is enabled for this public repository. Security → Advisories exposes the
  **Report a vulnerability** option.
- **[zyntrava.security@gmail.com](mailto:zyntrava.security@gmail.com)** is the
  owner-designated email alternative. The owner verified inbound receipt and
  delivery of a private reply. Ordinary email is not end-to-end encryption.

Begin with minimal redacted text and synthetic reproduction steps. Do not publish
exploit details in issues or PRs, submit real credentials or run attacks on systems
you do not own or have permission to test. No response deadline, bounty or legal
safe harbor is promised.

## What has and has not been verified

| Property | Evidence / status |
| --- | --- |
| Repository visibility | PUBLIC, with the original research repository kept private |
| Native reporting setting | GitHub API returned `enabled: true` on 18 November 2026 |
| Public report entry point | Unauthenticated Advisories HTML contains Report a vulnerability |
| Email receipt and private reply | Verified by owner using another account; no inbox artifacts independently inspected |
| Gmail notifications and Google 2-Step Verification | Owner-confirmed; not a GitHub report-delivery test |
| GitHub App permission review | Owner-confirmed; external service settings not independently inspected |
| Native report submission / owner receipt / reply | Not end-to-end tested in this publication operation |
| GitHub security-alert subscription and delivery | Not verified: CLI lacked notification scope and browser automation stopped at its URL safeguard |
| Mailbox readers, delegates, forwarding and unauthorized access | Not reported complete; record checks or an explicit owner assurance/risk decision |

Do not turn the outstanding delivery/access checks into a claim that the reporting
feature is disabled. Equally, enablement alone does not prove a fully tested process.
The owner email alternative remains available during those checks.

## Owner notification check

1. In the public repository, select **Watch → Custom → Security alerts**, or
   **All Activity**. Ensure the repository is not ignored and save.
2. Open [GitHub notification settings](https://github.com/settings/notifications).
   Under **Subscriptions → Watching → Notify me**, enable **Email** and **On GitHub**
   where offered, using an existing verified notification address, and save.
3. Reload both settings pages and record the selected repository filter and delivery
   options privately. Do not share credentials or screenshots of private inboxes.
4. Record actual delivery when a legitimate report arrives, or through a separately
   authorized harmless end-to-end test. Gmail operation is not evidence that GitHub
   sends this repository's alerts to that inbox.

The current setup does not require changing visibility, creating another repository,
adding collaborators, broadening token scopes or sending unsolicited test reports.

## Optional authorized end-to-end test

Agree participants and synthetic, clearly labelled test content first. An owner
creating a draft advisory is not a test of an external researcher's reporting path.

1. An authorized, separately controlled reporter uses the actual private reporting
   form. Do not use a real vulnerability, credentials or executable attachments.
2. The owner confirms receipt in the intended private interface, tests a reply visible
   to the reporter, and verifies configured GitHub/email notifications. A maintainers-only
   comment cannot test reporter receipt.
3. Check advisory participants and effective access. An unrelated account/logged-out
   session must not read the private report, replies or attachments. Finite tests
   do not prove arbitrary future confidentiality.
4. Close the harmless test advisory **without publishing it**. Do not request a CVE,
   create a temporary fork or grant repository collaborator access as part of this test.
5. Keep sender identities, inbox artifacts and private report URLs outside Git.
   Record submission, receipt, reply, notifications and access controls separately.

No native report or email was sent by the publication operation. Tests requiring
additional accounts/access need the owner's authorization and must not be fabricated.

## Historical context

On 17 November 2026, native reporting checks on private staging returned HTTP 404.
Those observations remain historical; they no longer describe the public repository.
The owner subsequently authorized its controlled publication. On 18 November the
public setting and report entry point were verified. No source or CI change was
needed to enable reporting, and no production-readiness claim follows.

Primary references: [GitHub reporting and notification configuration](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository),
[reporter workflow](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
and [maintainer replies/closure](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/fix-reported-vulnerabilities/manage-vulnerability-reports).
