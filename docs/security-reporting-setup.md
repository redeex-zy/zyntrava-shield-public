# Confidential reporting setup and verification

**Status: NOT CONFIGURED / NOT VERIFIED. No reporting address is published.**
This is an actionable owner procedure, not a claim that a channel works.
The creator confirms there is no dedicated verified inbox yet. No mailbox, new
repository, collaborator, email, test report or advisory has been created here.

## Observed private-staging configuration — 17 November 2026

- Both `redeex-zy/zyntrava-shield` and `redeex-zy/zyntrava-shield-public` are PRIVATE.
- Staging main remains `49402a1c615ebadf692c927845cb14e9d7581606`.
- An authenticated owner with repository admin access attempted the documented
  `PUT repos/redeex-zy/zyntrava-shield-public/private-vulnerability-reporting`.
  GitHub returned HTTP 404. GET before and after also returned HTTP 404. Native
  reporting is unavailable through the tested private configuration and is not verified.
- The CLI token has `repo` and `workflow` scopes; it has no `notifications` scope.
  GET of the repository subscription returned 404 with an explicit missing-scope
  diagnostic. This does not prove notifications are disabled; they are unverified.
- The token cannot enumerate GitHub App installations (403, different token type
  required). Do not infer absence of account-wide apps or forwarding from zero hooks.
- The manual-only CI, read-only workflow token, source-only distribution limits and
  original source commit are unchanged. A documentation branch is not a new approved ZIP.

Native private vulnerability reporting is documented for public repositories by
[GitHub](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
Do not change visibility, refresh token scopes, purchase services or create another
repository to bypass the current restrictions. A private source issue tracker
cannot accept normal external reports and is not case-confidential among its readers.

## Route now: owner-configured dedicated email

These steps require the creator's mailbox/provider access and manual action. No
password, recovery code, API token or private key should be shared with an assistant,
stored in Git, or pasted into a report. This task sends no email from any account.

1. **Select the destination.** Use an owner-controlled provider/account already
   available, or separately arrange a dedicated mailbox/alias. No domain purchase,
   subscription or account creation is performed by this task; the creator chooses
   the actual destination manually.
   Keep the actual destination private until it passes the tests below. Do not derive
   an address from the project name, GitHub profile or guessed domain.
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
6. **Run the harmless test below.** The creator uses an already-controlled second
   mailbox as the external sender, or separately obtains a consenting tester.
   Do not contact external researchers, create accounts or send mail automatically.
7. **Record evidence privately.** Keep actual addresses, mail headers, receipts,
   identities and access-control details outside Git. Record only sanitized result
   summaries in release documents. A test marker is correlation text, not a credential.
8. **Publish instructions only after verification and approval.** In a new reviewed
   documentation commit, replace SECURITY.md's inactive-channel paragraph with the
   exact verified destination, allowed report format and reply expectations. Review
   and reseal any changed release candidate. Do not modify the original sealed ZIP.

### Email configuration worksheet — values remain private and unset

| Field | Required owner decision/evidence |
| --- | --- |
| Dedicated destination | NOT CONFIGURED; no address supplied or invented |
| Owner-controlled provider and mailbox/alias | Verify directly in the provider; no account credentials in Git |
| Authorized readers/delegates | Inventory actual access and integrations; least privilege |
| Forwarding/ticketing rules | Confirm no public/unapproved recipients or automatic exports |
| Authentication/recovery | Owner verifies strong account security; do not record recovery secrets |
| Mail notifications and spam handling | Test exact inbound marker, reply and notifications |
| Retention/incident handling | Owner chooses deletion/retention and backup expectations |
| Public contact text | Remains absent until receipt/reply/access tests pass |

No SMTP endpoint, mail credentials, DNS record or fabricated destination is provided.
Notification receipt and destination ownership cannot be verified through the current
GitHub token or by a document alone.

## Harmless end-to-end verification — not performed yet

Use synthetic text only. Do not use a real vulnerability as the test. The owner
records actual UTC times and sanitized evidence in a private test record.

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
8. Mark the channel VERIFIED only after submission, receipt, reply, required
   notifications, access controls and correct SECURITY.md instructions pass.
   Any failed or unavailable step remains NOT VERIFIED and blocks public intake.

Minimum private test record (do not commit real contact details or report URLs):

```json
{
  "channel_status": "NOT VERIFIED",
  "submission": "NOT RUN",
  "owner_receipt": "NOT RUN",
  "private_reply": "NOT RUN",
  "notification_delivery": "NOT RUN",
  "unauthenticated_access_denied": "NOT RUN",
  "unrelated_account_access_denied": "NOT RUN",
  "delegates_apps_forwarding_review": "NOT RUN",
  "security_policy_matches_verified_destination": false,
  "sanitized_evidence_ids": []
}
```

## Future native GitHub reporting — only after separately authorized publication

Maintain the verified email route during any migration. This procedure does not
authorize changing repository visibility. Public publication must first pass its
separate owner approval and other release gates; a working email route resolves
the pre-publication reporting requirement without making staging public for a test.

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

## Not authorized or configured here

No new reporting repository or outside collaborator is authorized. Do not substitute
a general private issue tracker for outsider intake. No mailbox/provider account,
mail transmission, scope refresh, public advisory, release, deployment, Pages site
or visibility change has occurred. The policy and source remain experimental;
account-wide app access and independent security auditing remain unresolved.
