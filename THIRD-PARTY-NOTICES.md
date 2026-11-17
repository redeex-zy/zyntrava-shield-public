# Third-party notices — source-only distribution

The project's Apache-2.0 grant covers only original contributions that its creator
has authority to license. It does not replace the following upstream terms.

## Next.js-generated type declarations — MIT

`apps/dashboard/next-env.d.ts` matches the Next.js 16.4.6 generator template at
`dist/lib/typescript/writeAppTypeDeclarations.js`. Conservatively treat this file
as upstream MIT material. Its complete unchanged license, including
**Copyright (c) 2025 Vercel, Inc.**, is in [LICENSES/next-MIT.txt](LICENSES/next-MIT.txt).
No substantive changes to the emitted template were identified. This notice
attributes the upstream template; it does not attribute original Zyntrava code to Vercel.
[Upstream project](https://github.com/vercel/next.js).

## License documents and separately obtained software

`LICENSE` is the standard Apache-2.0 text. `LICENSES/next-MIT.txt` is the upstream
MIT text. These documents are not claimed as original Zyntrava authorship.
Python/npm lockfiles contain dependency references, not the library implementations.
No node_modules, dependency wheels, compiled dashboard, model weights, model dataset,
runtime DLLs, installers or external benchmark snapshots are included in this source ZIP.
Each separately installed component retains its own license. The dependency tree
includes MPL, LGPL, CC-BY and legacy Python terms; no compiled/runtime distribution
is cleared by this source-only grant. The prior audit has 55 npm actual-text gaps
and an unresolved isolated-build transitive version; those remain outside this clearance.
No font files are included; CSS/SVG system-font names do not bundle those fonts.

See [license scope](docs/license-scope.md), [application record](docs/license-application.md)
and [distribution obligations](docs/third-party-obligations.md).
