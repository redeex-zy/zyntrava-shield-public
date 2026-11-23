# Changelog

## 0.9.2a1 — proposed experimental security-hardening update

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
- Validate the unchanged security implementation at
  `28eb223462bf266f51d87ed849d4fd343b55dd64`: Windows and Linux/WSL each passed
  236 tests with three documented skips. The 46 focused security regressions are
  included in those totals. Initial missing-uv environment failures were preserved;
  the same assertions passed after restoring the existing pinned tool on PATH.
- Run a matched actual-Qwen3-4B comparison at seeds 9026/9027: both v0.9.1a1 and
  v0.9.2a1 completed 4/4 clean and 4/8 injected tasks; six activated forbidden
  proposals per version were rejected, with zero observed forbidden or duplicate
  effects. **Recovery did not improve.** Unactivated attacks are not blocked attacks.
- Separately exercise real-model post-effect uncertainty, strict schemas,
  pre-dispatch audit failure and durable release accounting across two fresh
  broker processes. A committed uncertain POST halted the new adapter; neither
  version duplicated the POST in the single matched fault trial. No general
  duplicate-rate advantage or exactly-once guarantee is claimed.
- Add a [dated validation report](docs/v0.9.2-validation.md) and sanitized result
  summary. No raw operational state, model weights, binaries or private research
  traces are added. No engine, dependency or CI changes follow the validated commit.

Compatibility and limitations: legacy policy defaults remain unchanged; strict
mode is opt-in and rejects legacy count grants. Existing release databases need
explicit operator review and fail closed rather than silently renewing budgets.
General POST deduplication, hostile-host protection and reliable task recovery
are not provided. Independent adversarial review is pending; this is not
production-ready. This proposal creates no GitHub Release or package publication.

Historical source-preview behavior, measurements and limitations are retained in
[the 0.9.1 notes](docs/release-notes.md) and [evidence summary](docs/preview-results.md).
This changelog does not announce a release or claim independent security validation.
