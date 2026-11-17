"""Read installed Python metadata and committed npm locks; no licensing decision."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    root = Path(__file__).resolve().parents[1]
    python = []
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"]):
        expression = dist.metadata.get("License-Expression")
        classifiers = [
            c for c in dist.metadata.get_all("Classifier", []) if c.startswith("License ::")
        ]
        legacy = dist.metadata.get("License", "")
        files = []
        for name in dist.files or []:
            if any(
                part.lower().startswith(("license", "copying", "notice")) for part in name.parts
            ):
                path = dist.locate_file(name)
                if path.is_file():
                    files.append(
                        {"path": str(name), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    )
        python.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "expression": expression,
                "classifiers": classifiers,
                "legacy_label": legacy if len(legacy) < 160 else "Long license text in METADATA",
                "license_files": files,
                "needs_manual_review": not expression and not classifiers and not legacy,
            }
        )
    node = []
    for app in ["dashboard"]:
        path = root / "apps" / app / "package-lock.json"
        if not path.is_file():
            package = json.loads((path.parent / "package.json").read_bytes())
            if package.get("dependencies") or package.get("devDependencies"):
                raise ValueError("Missing dependency lock for " + app)
            continue  # Website uses Node builtins; no third-party dependencies.
        for name, meta in json.loads(path.read_bytes()).get("packages", {}).items():
            if not name:
                continue
            node.append(
                {
                    "app": app,
                    "package": name,
                    "version": meta.get("version"),
                    "license": meta.get("license"),
                    "needs_manual_review": not meta.get("license"),
                }
            )
    result = {
        "schema": "zyntrava.preview.license-inventory.v1",
        "source": "Installed Python distribution metadata and committed npm lockfiles",
        "python": python,
        "node": node,
        "unknown_python": [p["name"] for p in python if p["needs_manual_review"]],
        "unknown_node": [p["package"] for p in node if p["needs_manual_review"]],
        "limits": (
            "Metadata inventory, not legal clearance. Review actual notices and distribution scope."
        ),
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {
                "python": len(python),
                "node": len(node),
                "unknown_python": result["unknown_python"],
                "unknown_node_count": len(result["unknown_node"]),
            }
        )
    )


if __name__ == "__main__":
    main()
