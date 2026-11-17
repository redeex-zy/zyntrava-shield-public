# Reproduce this candidate

Use a new source extraction, Python 3.13 and README's hash-locked installation.
No real credentials, paid services, model weights or private repository history
are required for the scripted exercise. New output paths are mandatory.

```sh
python examples/preview_agent.py --output runs/independent-first-run
python reviewer/verify-evidence.py
python scripts/check-public-docs.py
```

Here `python` means the installed environment's interpreter, not system Python.
The evidence verifier reads both complete selected runs, checks their member
hashes and recomputes the existing effect grades. It does not replay inference
or establish publisher authenticity. External COMPLETE-FILE-MANIFEST.json and
the adjacent ZIP checksum cover the source bytes; review those against an
owner-approved checksum before executing source.

For development regressions follow CONTRIBUTING: install uv 0.13.6 on PATH,
`uv sync --locked --extra agent`, build the dashboard, then run pytest/static
checks. The selected suite differs from the much larger private research tree.
Linux tests use a separate native-filesystem source/venv; do not reuse a Windows
venv. Python/npm lock hashes preserve versions, not future vulnerability status.

For actual Qwen use README's Windows-only pinned asset installer and the frozen
[protocol](preview-demo-protocol.md): two tasks, seed 9026, ports 18870/18871,
model port 8790, unchanged permissions/budgets/grader and no experimental recovery.
Preserve startup errors, incomplete tasks, nonactivation and duplicate effects.
Do not rerun seeds until a favorable result appears. Installing approved model
assets may require several GB of disk/memory and internet access to their publishers.

To package a new **complete** two-task synthetic run without modifying it:

```sh
python scripts/package-preview-demo.py runs/independent-first-run/results.json --output runs/independent-demo.zip
```

The strict sanitizer rejects unexpected content or personal paths. Raw workspaces,
SQLite state and model transcripts remain private until individually reviewed.
The included reference evidence preserves its original hashes and dirty-tree
provenance; the current candidate demonstration is a separate measurement.
Historical source-backed archive replay is recorded in verification, but its private
archives are deliberately not redistributed. It is not claimed reproducible from
these selected public files. Independently authored synthetic tests are encouraged
within [the contributor exercise](contributor-exercise.md) and the supported threat model.
