# Third-party distribution obligations

This is a source-only distribution; third-party software is not relicensed by its
Apache-2.0 grant. [License scope](license-scope.md) and
[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) identify the included exception.

| Material | Included? | Required treatment |
| --- | --- | --- |
| Original Zyntrava code, docs, synthetic cases and geometric SVGs | Yes | Qualified Apache-2.0 grant; preserve LICENSE/NOTICE; creator's AI-assisted authorship confirmation is recorded |
| Next.js 16.4.6 generated next-env.d.ts | Yes, source ZIP only | Upstream MIT; full unmodified Vercel notice in LICENSES/next-MIT.txt |
| Python packages | Names, pins/hashes only | Installed separately; preserve their actual notices if later redistributed; MPL/PSF/CNRI/nested terms are not replaced by Apache |
| npm packages | Source manifests/lock only | No node_modules or compiled UI shipped; review emitted content and MPL, CC-BY, LGPL/native source/relinking requirements before any bundle |
| Qwen models and llama.cpp | Download manifests only | No weights/runtime shipped; review exact artifacts/model cards and all runtime components before any redistribution |
| External benchmark copies, previous videos, fonts and installers | No | Their separate rights are not cleared or incorporated |
| Synthetic model traces and grades | Selected sanitized records only | No exclusive ownership claim over generated wording/facts; preserve provenance and negative findings |

The detailed prior audit reviewed 73 third-party Python entries and 178 npm lock
entries. Actual license text remains unverified for 55 npm entries; the exact
isolated-build trove-classifiers version was not recorded. These are explicit
limits on environment/binary clearance, not an approval inferred from metadata.
No model/runtime/library binaries are included to conceal those gaps.

Primary terms: [Apache](https://www.apache.org/licenses/LICENSE-2.0),
[MPL](https://www.mozilla.org/en-US/MPL/2.0/),
[LGPL](https://www.gnu.org/licenses/lgpl-3.0.txt),
[CC-BY](https://creativecommons.org/licenses/by/4.0/legalcode.en).
