# Confidential reporting setup and verification plan

Status: **NOT CONFIGURED / NOT VERIFIED**. No actual destination, repository,
notification, test report or invitation exists as a result of this task. Do not
send sensitive details to a public issue or infer a personal email address.
External setup/tests need separate explicit authority and consenting participants.

## Choose the supported route without changing visibility

GitHub documents private vulnerability reporting for public repositories. Do not
make private staging public to obtain it. Check the actual repository's feature
availability and current [official configuration instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
when the owner later authorizes access. If unavailable, record that result and use
the private alternative below; do not call a normal issue a private advisory.

### Route A — private vulnerability reporting, only where supported

An authorized admin checks Settings → Security and quality → Advanced Security →
Private vulnerability reporting. If supported and separately approved, enable it.
For the consenting non-admin tester, confirm Report a vulnerability appears in
Security/Advisories. Review the displayed SECURITY.md before submitting. Subscribe
the responsible owner to Security alerts or All Activity and check their notification
preferences. Do not advertise an active destination until the end-to-end test passes.

The [reporter workflow](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
is distinct from an admin creating a draft advisory. Record the actual reporting
interface URL only after observing it; this document supplies no invented URL.
An optional future read-only setting check with an already authorized CLI session is:

```sh
gh api --method GET repos/OWNER/REPOSITORY/private-vulnerability-reporting --jq .enabled
```

OWNER/REPOSITORY are placeholders. This command was not run. A true flag proves
only a setting, not delivery or confidentiality. Error/false/unsupported results
require the alternative; do not bypass permissions, buy services or change visibility.

### Route B — dedicated private reporting repository for each reviewer/case

This is the proposed private-staging alternative, not a configured channel.

1. After separate approval, the owner selects or creates a dedicated **private**
   repository for the specific case/reviewer. Do not reuse general source-staging
   issues: every source collaborator may be able to read them. Store no release
   source, credentials or real exploit payload in this reporting repository.
2. Review the actual access list. Limit it to the owner, the consenting reporter
   and explicitly authorized triage participants; inventory organization owners,
   administrators and inherited team access rather than promising two-person-only
   secrecy. Require normal account security/MFA where available. Do not create accounts here.
3. Enable Issues; disable Actions and unnecessary discussions, wiki, Pages or
   integrations. Review repository/organization apps, hooks and notification
   forwarding so bodies are not copied to unintended recipients. Do not add bots
   or tokens to transport vulnerability details.
4. Record the real repository identity and verify its private visibility. With an
   already authorized CLI, a future read-only check is:

```sh
gh api --method GET repos/OWNER/PRIVATE-CASE-REPOSITORY --jq '{private: .private, visibility: .visibility, issues: .has_issues}'
```

5. Invite only the separately approved consenting tester, verify their effective
   access, then send the actual private issue URL through the already verified
   relationship. This task sends no invitation or link. GitHub's
   [issue access instructions](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue)
   explain the basic read-access requirement; repository visibility/access must
   still be tested, not presumed.
6. Start **text-only**. Do not assume attachment URLs inherit issue confidentiality.
   Exclude attachments until anonymous/unrelated-user access checks on the actual
   storage path pass. Keep all real credentials, personal data and production targets out.

## Harmless end-to-end test — required for either route

Use `REPORTING-TEST-RECORD.json` in the private decision workspace, never public source.

1. Owner and consenting non-admin reporter agree the test and participants. Record
   the exact private destination and UTC timestamp privately. Submit a new message
   titled **Harmless confidential-channel verification — not a vulnerability**,
   containing a unique random marker and “Synthetic text only; no security issue.”
   Use the marker only for correlation; it is not an authentication credential.
2. Confirm the owner sees exactly that marker in the intended private interface.
   Confirm the intended notification arrives; test required in-app/email preferences
   without publishing an address or copying notification headers into public source.
3. Owner replies privately with the marker. Reporter confirms receipt and access
   to the reply. A UI screenshot alone or an enabled setting does not complete this test.
4. An unauthenticated session and a consenting unrelated account both attempt to
   open the exact report URL. Neither may read title/body/comments or attachments.
   Check search/issue lists as well. Record only sanitized success/denial evidence;
   do not store credentials, browser cookies or private inbox state in the source.
5. Review actual authorized participants and audit unexpected viewers/notifications.
   Verify no public issue, published advisory, release or CVE request was created.
   A platform's authorized administrators remain part of the trusted service boundary.
6. Close the harmless private issue, or use **Close security advisory** for the
   harmless private-report test where supported. Never publish a fake advisory.
   Record agreed retention/access removal. Closing does not erase server backups,
   notifications or previously downloaded copies; do not promise secure deletion.
7. Only after receipt, reply, notification and access tests pass may the owner mark
   the actual route verified and update SECURITY.md in a newly sealed candidate.
   Keep the earlier verified route available during any later reporting migration.

Private-advisory handling is described by [GitHub's management procedure](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/fix-reported-vulnerabilities/manage-vulnerability-reports).
If any test fails, stop accepting sensitive reports and keep channel status unverified.
Do not solve a missing feature by making a private repository public.

## Remaining scope and approvals

No reporting channel has been tested here. Source-only private staging may be
technically ready for owner review while confidential intake remains NO-GO.
Public publication is not authorized. Any actual repository creation, invitation,
report submission, configuration change or source push is a future external action
requiring explicit approval. No email, organization identity or destination is invented.
