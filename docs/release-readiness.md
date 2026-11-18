# Public developer-preview status

**Zyntrava Shield 0.9.1a1 is publicly available as experimental source.** The owner
authorized controlled publication of
[redeex-zy/zyntrava-shield-public](https://github.com/redeex-zy/zyntrava-shield-public).
This status was checked on **18 November 2026**. Public source availability does not
authorize an application deployment, package/binary release or production service.

| Area | Current status |
| --- | --- |
| Published source baseline | `c79a3467207250aff4edb490f747492a9e743758`, tree `bbf8328459507112b10a2f24438948bc7a8162fd`; 180 selected files at publication |
| Historical source/history | Original approved ancestor `49402a1c615ebadf692c927845cb14e9d7581606`, prior archives and experimental evidence preserved; private research history not imported |
| Source licensing | Apache-2.0 approved for cleared original material; creator NOTICE and Next.js MIT attribution retained |
| Branding | Owner provisionally approves Zyntrava Shield; trademark clearance unresolved |
| Next.js/picomatch residual | Unpatched bundled copy, conditionally accepted only for trusted reviewed builds, manual CI and source-only distribution; no upstream fix claimed |
| Workflow | Manual-only, reviewed main SHA + trust acknowledgement before checkout, contents read only; local guard checks pass, hosted enforcement not validated |
| Distribution | Source only; no compiled dashboard, installer, native runtime, weights or dependency implementations |
| GitHub private reporting | Enabled; API setting and public Report a vulnerability link verified |
| Email alternative | `zyntrava.security@gmail.com`; owner confirms receipt/reply and Gmail notifications |
| Account assurances | MFA and GitHub App review owner-confirmed; no independent account inspection |
| Remaining reporting work | Native end-to-end submission/delivery and GitHub alert preferences unverified; mailbox delegates/forwarding/access checks not reported complete |
| Runtime safety | Local synthetic use only; public-management, real-data, multi-user and production deployments unsupported |

## Verification scope

The published source received Windows and native Linux/WSL checks: **190 Python
tests passed, three skipped per platform**, clean venv installation, scripted SDK
exercises, frontend typecheck/unit tests/build, packaging and source checks. These
are developer-assisted observations, not independent auditing or clean OS VM tests.

The Windows authenticated browser journey passed. A Linux follow-up on the same
published baseline also passed **one browser journey, zero failures/skips** after
missing shared libraries were extracted into a disposable QA workspace. It ran
inside restricted Bubblewrap namespaces with unchanged tests and source. Earlier
missing-browser/library failures were preserved. This is not production OS-isolation
validation. The browser's automated accessibility checks are not certification.

[Historical verification records](candidate-verification.md) and the frozen
`verification-manifest.json` describe their original dates/source candidates; their
old release decisions and audit counts are not current publication settings. The
source-selection inventory is likewise historical provenance, not a live checksum
manifest for later documentation commits.

## Limits that publication does not resolve

Registered broker tools only; unreliable task recovery, mutable local audits,
uncontrolled raw provider/logging channels and a trusted in-process host remain
limitations. Experimental recovery stays off by default. Independent adversarial
auditing, production readiness, superiority, universal prevention and trademark
clearance are not established.

Read [SECURITY.md](../SECURITY.md), [reporting verification](security-reporting-setup.md),
[dependency exposure](dependency-advisory.md), [known limitations](known-limitations.md)
and [license scope](license-scope.md). Source/documentation contributions still require
review; availability is not permission to run untrusted builds or publish raw reports.
