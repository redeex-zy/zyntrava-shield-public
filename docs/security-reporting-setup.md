# Confidential reporting setup and verification

**Contact: [zyntrava.security@gmail.com](mailto:zyntrava.security@gmail.com).**
**Status: OWNER-CONFIRMED email receipt, reply, notifications and account controls;
not independently verified.**
The owner reports successful receipt of a test email from another account and
successful delivery of a reply from the security inbox to that sender. No inbox
messages or mail headers were inspected by the development assistant; this is
owner-attested verification, not an independently reproduced test.
The owner additionally confirms that **Gmail notifications work**, **Google 2-Step
Verification is enabled**, and **GitHub App permissions have been reviewed**.
No independent inbox/account/app inspection or unauthorized-access test is claimed.
Delegates, forwarding and unauthorized-user access testing have not been reported
complete. Public publication remains unauthorized and subject to the final source
review, remaining assurance decisions and explicit approval. Version **0.9.1a1**
remains experimental. This update sends no email and creates no account, repository,
collaborator or advisory.

## Preserved baseline observations and owner confirmations — 17 November 2026

- Both `redeex-zy/zyntrava-shield` and `redeex-zy/zyntrava-shield-public` are PRIVATE.
- Original approved main `49402a1c615ebadf692c927845cb14e9d7581606` is preserved in
  history. The final private candidate revision is identified in its delivery manifest.
- An authenticated owner with repository admin access attempted the documented
  `PUT repos/redeex-zy/zyntrava-shield-public/private-vulnerability-reporting`.
  GitHub returned HTTP 404. GET before and after also returned HTTP 404. Native
  reporting is unavailable through the tested private configuration and is not verified.
- The CLI token has `repo` and `workflow` scopes; it has no `notifications` scope.
  GET of the repository subscription returned 404 with an explicit missing-scope
  diagnostic. This does not prove notifications are disabled. Gmail notification
  delivery is now owner-confirmed; GitHub notification preferences remain unverified.
- The token cannot enumerate GitHub App installations (403, different token type
  required). The owner now confirms reviewing GitHub App permissions; this does
  not become an independent API audit or prove absence of forwarding/external access.
- The manual-only CI, read-only workflow token, source-only distribution limits and
  original source commit are unchanged. A documentation branch is not a new approved ZIP.

Native private vulnerability reporting is documented for public repositories by
[GitHub](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
Do not change visibility, refresh token scopes, purchase services or create another
repository to bypass the current restrictions. A private source issue tracker
cannot accept normal external reports and is not case-confidential among its readers.

## Route now: owner-designated dedicated email

These steps require the creator's mailbox/provider access and manual action. No
password, recovery code, API token or private key should be shared with an assistant,
stored in Git, or pasted into a report. This task sends no email from any account.

1. **Use the designated contact.** The creator supplies and authorizes
   `zyntrava.security@gmail.com` for private vulnerability reports. Receipt and reply
   were verified by the owner as described above. No address was inferred from a
   profile/domain, and no personal sender address or mail header is published.
2. **Confirm control and access.** Sign in directly to the provider, verify the
   destination exists and can receive external mail, and verify ownership/control
   of its alias and backing mailbox. Review delegates, recovery methods, forwarding
   rules, mailing lists, shared folders, integrations and retention. Limit content
   access to the owner and explicitly authorized triage participants. Do not grant
   access to an outside researcher or app as part of setup.
3. **Protect the account.** Enable the provider's available strong authentication
   and safe recovery. Keep recovery material outside this project. Review the
   provider's transport-security support; if using an already-owned domain, review
   existing SPF/DKIM/DMARC results without publishing or changing DNS here.
   Avoid auto-forwarding full reports or automatic public ticket creation.
4. **Configure handling.** Use a private folder/label and notifications the owner
   can actually monitor; inspect spam/quarantine during testing. Permit plain-text
   external reports. Keep attachments disabled by process until reviewed; do not
   run received scripts or commands. Use a minimal acknowledgement only after
   testing that it replies privately to the intended sender, without echoing secrets.
5. **Choose confidentiality expectations.** Ordinary email is not end-to-end
   encryption, even with transport TLS. The mail provider and approved mailbox
   administrators are trusted parties. Start with redacted text; agree a separately
   verified protected exchange before highly sensitive material. Do not advertise
   encryption or an OpenPGP key that has not been configured and verified.
6. **Complete the remaining harmless checks below.** Preserve the owner's successful
   receipt/reply and Gmail notification results; do not relabel them as assistant-executed
   or independently audited. Google 2-Step Verification and GitHub App review are
   owner-confirmed. Effective mailbox access and forwarding/delegates still need
   review/testing. Do not contact external researchers, create accounts
   or send mail automatically.
7. **Record evidence privately.** Apart from the approved security contact, keep
   sender addresses, mail headers, receipts, identities and access-control details
   outside Git. Record only sanitized result
   summaries in release documents. A test marker is correlation text, not a credential.
8. **Keep status precise.** SECURITY.md lists the owner-designated contact and
   distinguishes owner-confirmed controls from incomplete independent/access
   testing. Update that status only after additional evidence exists. Public
   publication requires separate approval and a reviewed/resealed changed source
   candidate. The owner separately authorizes the normal private documentation merge;
   preserve the original commit/ZIP. This does not authorize public publication.

### Email configuration and verification worksheet

| Field | Required owner decision/evidence |
| --- | --- |
| Dedicated destination | `zyntrava.security@gmail.com`, explicitly supplied and authorized by the owner |
| Inbound email receipt | VERIFIED BY OWNER: test from another account was received |
| Reply delivery | VERIFIED BY OWNER: reply reached the original sender |
| Gmail notification delivery | VERIFIED BY OWNER; not independently reproduced |
| Google 2-Step Verification | ENABLED, as confirmed by owner; no account settings inspected |
| GitHub App permissions | REVIEWED BY OWNER; no independent app-access audit |
| Access controls/readers/delegates | NOT VERIFIED; review actual readers and integrations |
| Forwarding/ticketing rules | NOT VERIFIED; confirm no public/unapproved exports |
| Authentication/recovery | Owner confirms 2-Step Verification; recovery/delegation details not independently reviewed |
| Spam handling/retention | Owner review still required; no test result claimed |
| Documentation approval | Owner authorizes private main merge and source candidate; no public-release authorization |

No SMTP credentials, private mail headers or fabricated destination are provided.
The current GitHub token cannot inspect the Gmail inbox. The owner's receipt/reply
and subsequent confirmations are the evidence recorded here. They are not independent
verification of notifications, account controls, delegates, forwarding or retention.

## Harmless verification — owner-confirmed checks and remaining assurance limits

Use synthetic text only. Do not use a real vulnerability as the test. Preserve the
owner-reported successful receipt, reply and Gmail notifications; no exact test time, sender identity,
marker or private receipt artifact was supplied to the assistant. Do not invent
those details. Record additional evidence privately as the remaining tests run.

1. Agree the destination, intended participants and a unique marker. Suggested
   subject: **Harmless confidential-channel verification — not a vulnerability**.
   Body: “Synthetic text only; no security issue. Please reply with the same marker.”
   Add the marker chosen locally by the owner; this document contains no live marker.
2. From a separately controlled sender account, submit the text through the actual
   external reporting path. Confirm sent-mail state alone is not accepted as receipt.
3. The owner verifies the exact marker in the intended inbox/interface, observes
   spam/quarantine behavior and confirms the configured in-app/email notification.
4. The owner replies privately to the intended sender with the marker. The sender
   confirms the reply and any expected notification. Do not CC unrelated people.
5. Verify effective access: a logged-out session and a separate unauthorized account
   cannot read the private inbox, thread, report URL, search results or shared view.
   Review delegates, apps and forwarding as well; a login prompt alone does not
   prove the absence of another authorized reader. Avoid screenshots of inbox content.
6. Do not use attachments until their actual storage/link permissions have been
   independently tested. Record provider/admin trust boundaries and limitations;
   finite access tests do not prove arbitrary future confidentiality.
7. Close/archive the harmless test privately according to the owner's retention
   decision. Closing or deletion does not erase provider backups or delivered copies.
8. Mark the full process VERIFIED only after submission, receipt, reply, required
   notifications, access controls and correct SECURITY.md instructions pass.
   Owner-confirmed receipt/reply, Gmail notifications, 2-Step Verification and GitHub
   App review remain owner attestations. Unreported mailbox-access tests remain
   unverified; record their completion or an explicit owner assurance/risk decision
   before full reporting-process sign-off. Public release always needs separate approval.

Private test record (do not commit sender addresses, inbox artifacts or report URLs;
the designated security contact above is explicitly owner-approved):

```json
{
  "channel_status": "OWNER-CONFIRMED OPERATION; INDEPENDENT/ACCESS TESTS INCOMPLETE",
  "submission": "OWNER-REPORTED TEST FROM ANOTHER ACCOUNT",
  "owner_receipt": "VERIFIED BY OWNER",
  "private_reply": "VERIFIED BY OWNER: REACHED ORIGINAL SENDER",
  "evidence_basis": "Owner statements; no inbox/account artifacts inspected by assistant",
  "gmail_notification_delivery": "VERIFIED BY OWNER",
  "google_two_step_verification": "ENABLED AS CONFIRMED BY OWNER",
  "github_app_permission_review": "CONFIRMED BY OWNER",
  "github_notification_preferences": "NOT VERIFIED",
  "unauthenticated_access_denied": "NOT TESTED",
  "unrelated_account_access_denied": "NOT TESTED",
  "delegates_apps_forwarding_review": "NOT VERIFIED",
  "security_policy_matches_owner_designated_contact": true,
  "sanitized_evidence_ids": []
}
```

## Future native GitHub reporting — only after separately authorized publication

Maintain the verified email route during any migration. This procedure does not
authorize changing repository visibility. Public publication must first pass its
separate owner approval and other release gates. Completing the remaining email
verification can satisfy the reporting gate without making staging public for a test;
owner-confirmed operational checks do not independently verify mailbox access control.

1. After separately approved publication, confirm the intended repository's actual
   owner/name and PUBLIC visibility. The original research repository stays PRIVATE.
2. As an authorized admin, open Settings → Security and quality → Advanced Security
   → Private vulnerability reporting. Enable the native feature where supported.
   Alternatively use the documented PUT endpoint with a suitable admin credential.
3. Read back the setting and require `enabled: true`; API failure is not success.
   This is a future command, **not** a command to run against private staging now:

   ```sh
   gh api --method PUT repos/redeex-zy/zyntrava-shield-public/private-vulnerability-reporting
   gh api --method GET repos/redeex-zy/zyntrava-shield-public/private-vulnerability-reporting --jq .enabled
   ```

4. The owner checks repository Watch → Custom → Security alerts (or All Activity),
   repository notifications enabled, and personal Settings → Notifications →
   Subscriptions → Watching delivery preferences. Settings alone do not prove
   delivery. Current CLI notification access is insufficient; do not request tokens.
5. With separate consent/authority for the test, a non-admin controlled account
   opens the real Security/Advisories reporting interface and confirms that the
   current SECURITY.md and Report a vulnerability action are visible. An owner
   creating a draft advisory does not test outsider submission.
6. Submit a harmless report and perform the receipt/reply/notification/access tests
   above. GitHub adds the reporter as an **advisory** participant; this is distinct
   from repository collaborator access. Review actual advisory permissions, and
   obtain any necessary authorization before a future test. No account is added here.
7. Use a normal private advisory reply for the reporter; a maintainers-only
   confidential comment is intentionally hidden from the reporter and cannot test
   their receipt. Do not create a temporary fork, CVE request or public advisory.
8. Close the harmless advisory using Close security advisory without publishing it.
   Check that public/advisory views expose none of its title/body/replies. Record
   permitted participants, notifications and retention limits privately.
9. Only after the full test succeeds, update SECURITY.md with the actual verified
   reporting destination and keep the previous verified route until migration is safe.

Official references:
[configuration and notifications](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository),
[reporter workflow](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately),
[maintainer replies and closure](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/fix-reported-vulnerabilities/manage-vulnerability-reports),
[enable API](https://docs.github.com/en/rest/repos/repos#enable-private-vulnerability-reporting-for-a-repository).

## Actions outside this documentation update

No new reporting repository or outside collaborator is authorized. Do not substitute
a general private issue tracker for outsider intake. No mailbox/provider account,
mail transmission, scope refresh, public advisory, release, deployment, Pages site
or visibility change was performed by the assistant. The owner separately reports
the successful email receipt/reply test above. The policy and source remain experimental;
account-wide app access and independent security auditing remain unresolved.
