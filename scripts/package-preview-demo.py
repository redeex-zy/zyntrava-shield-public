"""Create a NEW sanitized synthetic-evidence ZIP; never changes the original run."""

import argparse
import json
from pathlib import Path

from zyntrava.lab.public_demo import prepare_demo

cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("results", type=Path)
cli.add_argument("--output", type=Path, required=True)
args = cli.parse_args()
print(json.dumps(prepare_demo(args.results, args.output), indent=2))
