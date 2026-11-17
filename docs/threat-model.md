# Supported developer-preview threat model

The adversary controls retrieved dummy text or a model's proposed arguments. It
tries to make the registered adapter read/write outside the operator's scope,
send an unauthorized HTTP request, disclose classified content, misuse an approval
or confuse authorization with business-task success. The developer controls the
task, policy, synthetic resources, registered executors and model configuration.

The trusted computing base includes the Python interpreter/process, adapter,
broker, policy, audit writer, executors, operator, model transport/history handling
and OS account/kernel. This is a reference-monitor-style in-process integration,
not a hardened boundary against arbitrary code running as the same account.

## Enforcement and observations

| Boundary | Supported control | Verification scope |
| --- | --- | --- |
| Model to registered tools | Typed closed requests, default deny, scoped permissions | Python regressions; real Qwen file/report demonstration |
| File access | Workspace scopes, traversal/symlink handling | Portable regressions; Windows privileged symlink test skipped, Linux exercised |
| HTTP effects | Canonical numeric loopback destinations, bounded bodies, exact JSON fields when configured | Dummy receivers and regression tests; no general internet client |
| Human approval | Operator token, exact action/session/policy binding, expiration, single use | API/control/approval regressions and authenticated browser journey |
| Classified output | Session-bound flow controls and returned-answer validation | Regression tests; not arbitrary semantic confidentiality proof |
| Audit | Required pre-effect record; fail closed when audit fails | Regression tests; local SQLite is mutable by the trusted account |
| Management API | Localhost, separate ephemeral bearers, host/origin checks | Backend tests and browser journey; no public multi-user validation |

No retrieved text, tool error or model explanation grants a new permission.
Authorization errors do not establish that an authorized business task completed.
The reference grader observes executed reads, receiver receipts, forbidden and
duplicate effects separately from model prose and policy outcomes.

Out of scope: unregistered tools or alternate execution paths, compromised host or
operator, malicious Python dependencies, raw model logs/provider transport, remote
tracing, persistent agent memory and system-wide application security. Docker and
restricted-process research are not containment claims for this public example.
Use synthetic inputs and owned loopback services only. See
[limitations](known-limitations.md) and [architecture](developer-architecture.md).
