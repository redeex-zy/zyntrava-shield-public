# Picomatch advisory assessment — 17 November 2026

This dated assessment records the 0.9.1a1 source preview's development-tool
exposure. It does not patch picomatch upstream or eliminate all vulnerable bundled
code. The owner subsequently authorized limited source publication subject to the
trusted-build/manual-CI/source-only restrictions below. The sealed predecessor and
its ZIP are preserved; see [current preview status](release-readiness.md).

## Dependency paths and classification

The predecessor installed picomatch **4.0.7** at
`apps/dashboard/node_modules/picomatch`, all through the development root
`vitest@5.0.5`. The logical paths (shared installations are deduplicated) are:

```text
vitest -> picomatch
vitest -> tinyglobby@0.2.17 -> picomatch
vitest -> tinyglobby -> fdir@6.5.0 -> picomatch (optional peer)
vitest -> vite@8.3.5 -> picomatch
vitest -> vite -> tinyglobby -> picomatch
vitest -> vite -> tinyglobby -> fdir -> picomatch
```

Vite is a Vitest peer; `@vitest/mocker@5.0.5`, itself a Vitest dependency, also
has an optional Vite peer, yielding the same last three paths through that peer.
None introduces a separate installed picomatch version. The lock marks this
standalone package `dev: true`. Test collection/filtering and Vite transforms use
it; Zyntrava builds with Next.js, not Vite. It is not Python SDK code or a runtime
dependency of the supported Python-served static dashboard.

Manual inspection additionally found `next@16.4.6 -> dist/compiled/picomatch`.
Its package omits a version. The exact tagged Next.js package and upstream lock
pin **4.0.1** for this build; treat that as upstream provenance, not a version
field in the installed artifact. The compiled file SHA-256 is
`607dc79784c1161c33076903769dba23e63d9d9ccfe3c4695a32ebe3a5ab892d`.
It is within a package declared as a production dependency in package.json, but
is build-time code in Zyntrava's supported configuration. Next.js server/image
optimizer, middleware and development hosting are outside that configuration.

## Upstream status and controlled reproduction

[GHSA-fc5q-39xc-vjpf / CVE-2026-112366](https://github.com/advisories/GHSA-fc5q-39xc-vjpf)
affects versions through 4.0.7 and lists **no patched version** at this assessment.
The [upstream latest release](https://github.com/micromatch/picomatch/releases)
and npm registry both report 4.0.7. The advisory's link to
[PR 194](https://github.com/micromatch/picomatch/pull/194) resolves to an open
leading-question-mark extglob correctness change, not evidence of a released
fix for this ReDoS. No unreviewed PR, override or force downgrade is applied.

Bounded local child-process probes against both installed copies compiled
`+(*a)` and matched synthetic `a` strings ending in `!`. At length 25, matching
took approximately 0.6 seconds; at length 29 each child exceeded the 3-second
timeout and was terminated. This confirms vulnerable library behavior locally,
not an exploit against the dashboard. Small timings are environment-dependent.
Raw probes, source hashes and upstream responses are retained in the separate
assessment delivery; malicious requests were not sent to third-party services.

## Input flow and exposure

- Vitest obtains test globs from trusted configuration/CLI. The predecessor's
  configured include is the constant `lib/**/*.test.ts`. Instrumented collection
  observed that pattern and dependency-owned exclusion/transform patterns. It
  did not consume model output, uploaded documents or HTTP request bodies.
- Next's bundled matcher receives build/configuration globs and image patterns.
  Instrumenting the exact supported static build observed one call, pattern
  `**`. There are no configured remote image patterns, middleware or custom
  output-tracing globs. A finite trace supports the review; it is not proof of
  unreachability in every Next.js feature or future configuration.
- The supported application is `output: 'export'` with unoptimized images.
  FastAPI mounts the exported files using StaticFiles. No Node/Next/Vite server
  executes during SDK or local dashboard operation. Dashboard search uses
  URLSearchParams and parameterized SQLite substring queries (`instr`), not
  JavaScript glob compilation. Agent tool parameters/documents stay in Python.
- The source ZIP and SDK packages include no node_modules or compiled UI.
  Installing frontend dependencies brings the bundled Next matcher onto the
  build machine. Building attacker-controlled source/configuration/CLI globs is
  outside supported use and unsafe; fixed trusted globs do not allow an attacker
  to inject a repeated extglob just by choosing a filename or document text.

No untrusted-input path to this vulnerability was found in the supported runtime.
This is a scoped exposure assessment, not a universal non-exploitability claim.
The residual Next build-time copy is a genuine known risk requiring trusted builds
and upstream monitoring. Zero npm findings must not be advertised as absence of
vulnerable bundled code. An internet-facing Next server requires a new assessment.

## Targeted change and rejected alternatives

Node 24.21.0 has stable native TypeScript stripping and a built-in test runner.
The replacement uses `node:test`, `node:assert/strict`, built-in fetch mocks and
an explicit list of the same three files. All six test names and all 21 assertions
are retained; HTTP fixtures use synthetic Response objects. Type checking remains
a separate required check. TypeScript imports gain `.ts` and
`allowImportingTsExtensions` with `noEmit`; application modules are unchanged.
Node emits a harmless module-type detection warning for these files; it is not
suppressed. Add future unit test files explicitly to the test command.

Vitest and its now-unused dependencies are removed from package.json/lock. No
retained dependency version is upgraded or downgraded. npm also rehomes six
existing-version optional WASI dependency entries during lock resolution.
The unused Vitest config is excluded from the new source candidate. No test,
security scan or audit result is disabled, allowlisted or hidden.

Simply omitting development installs would break TypeScript/Tailwind/testing
reproduction. Omitting tooling from the ZIP while leaving its manifest would
still install it. A forced Vitest 3.1.4 suggestion is not a verified upstream
picomatch fix and changes major test semantics. Replacing Next.js or patching its
compiled vendor code would be disproportionate and unverified for this task.

## Verification and release decision

Use Node 24.21.0 and the checked-in npm lock:

```text
npm --prefix apps/dashboard ci --ignore-scripts
npm --prefix apps/dashboard test
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard audit --json
npm --prefix apps/dashboard audit --omit=dev --json
npm --prefix apps/dashboard run build
```

Use `npm.cmd` on Windows. Follow CONTRIBUTING for Python tests, then run
`npm --prefix apps/dashboard run test:e2e` with the documented test Python.
The adjacent assessment verification manifest records actual results, commands,
negative baseline audits, probe timeouts, platform skips and archive hashes.
Historical evidence and reported model measurements are not relabeled as new runs.

**Conditional GO for a limited source-only developer preview on advisory grounds**:
the separately audited Vitest chain is removed and tests remain reproducible;
accept and disclose the unpatched, trusted-build-only Next.js residual. There is
no demonstrated remote dashboard exploit, and no general upstream remediation.
The owner subsequently accepted that scoped residual risk, provisionally approved
the name and authorized the source preview. Native GitHub reporting is now enabled;
its delivery/notification checks remain separate. See [current status](release-readiness.md)
and [reporting details](security-reporting-setup.md). This assessment is not a new
upstream-patch check, binary-distribution clearance or production security approval.

Primary implementation references:
[Next.js tagged package](https://github.com/vercel/next.js/blob/v16.4.6/packages/next/package.json),
[Next compilation](https://github.com/vercel/next.js/blob/v16.4.6/packages/next/taskfile.js),
[Node TypeScript support](https://nodejs.org/docs/v24.21.0/api/typescript.html).
