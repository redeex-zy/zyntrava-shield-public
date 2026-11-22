# Changelog

## 0.9.2a1 — local security-review candidate, unreleased

- Distinguish pre-effect failures from uncertain dispatch; halt further session
  dispatch and the supported Pydantic AI run on uncertainty. Do not retry unknown
  effects automatically; exactly-once delivery is not claimed.
- Reject approval overflow before recording successful queue acceptance; audit
  expiry/retirement while keeping invalidated grants unusable on audit failure.
- Persist count-release reservations across process restarts and audit retention.
  Legacy or incomplete state requires operator review; no implicit budget renewal.
- Add operator-only session retirement and opt-in SDK retirement on exit.
- Add an explicit strict policy profile, configuration diagnostics and synthetic
  SDK example without changing legacy default policy serialization or authority.
- Record the upstream picomatch advisory withdrawal while preserving trusted-build,
  manual-only CI and source-only restrictions.

Historical source-preview behavior, measurements and limitations are retained in
[the 0.9.1 notes](docs/release-notes.md) and [evidence summary](docs/preview-results.md).
This changelog does not announce a release or claim independent security validation.
