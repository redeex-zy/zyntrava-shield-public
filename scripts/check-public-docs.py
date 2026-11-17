"""Check only selected source Markdown links/fences and unintended home paths; no network."""

import json
import re
from pathlib import Path
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
names = ["README.md", "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "LICENSE-PROPOSAL.md"]
names += [p.relative_to(root).as_posix() for p in (root / "docs").rglob("*.md")]
errors = []
links = 0
for name in names:
    path = root / name
    text = path.read_text(encoding="utf-8")
    if text.count("```") % 2:
        errors.append(name + ": unclosed fence")
    if re.search(r"[A-Za-z]:[\\/]+Users[\\/]+[^\s/\\]+|/home/[^\s/]+", text):
        errors.append(name + ": machine-specific home path")
    for value in re.findall(r"\]\(([^)]+)\)", text):
        value = unquote(value.split("#", 1)[0].strip("<>"))
        if not value or "://" in value or value.startswith("mailto:"):
            continue
        links += 1
        target = (path.parent / value).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            errors.append(name + ": missing/unsafe link " + value)
print(json.dumps({"documents": len(names), "links": links, "errors": errors}, indent=2))
raise SystemExit(bool(errors))
