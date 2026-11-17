"""Two controlled tasks: real broker effects, explicit scripted versus Qwen modes.

See docs/developer-quickstart.md for installation and exact protection boundaries.
"""

import argparse
import json
from pathlib import Path


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--live", action="store_true", help="Actual Qwen3-4B; Windows assets required")
    cli.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--output", type=Path, required=True, help="New synthetic evidence directory")
    cli.add_argument("--seed", type=int, default=9026)
    cli.add_argument("--service-base-port", type=int, default=0)
    args = cli.parse_args()
    try:
        from zyntrava.lab.developer_preview import run_preview
    except ImportError:
        cli.error("Install the locked optional agent dependencies; see developer quickstart.")
    try:
        run_preview(
            args.repository.resolve(),
            args.output.resolve(),
            live=args.live,
            seed=args.seed,
            service_base_port=args.service_base_port,
        )
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        cli.error(
            f"Exercise stopped ({type(exc).__name__}). Keep partial results; check model assets, "
            "free ports and a NEW output path. Never disable host security controls."
        )
    print(json.dumps(json.loads((args.output / "summary.json").read_bytes()), indent=2))


if __name__ == "__main__":
    main()
