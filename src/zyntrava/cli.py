"""Local-only command line. Public exposure and arbitrary commands are unsupported."""

import argparse
from pathlib import Path

import uvicorn

from zyntrava.startup import initialize_lab, local_application


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        prog="zyntrava", description="Zyntrava Shield local research tools"
    )
    commands = cli.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "init-lab", help="Create synthetic fixtures in a new local state directory"
    )
    init.add_argument("--state", type=Path, default=Path(".state"))
    serve = commands.add_parser("serve", help="Run an authenticated API bound to 127.0.0.1")
    serve.add_argument("--state", type=Path, default=Path(".state"))
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--retention-days", type=int, default=None)
    desktop = commands.add_parser(
        "desktop", help="Windows desktop prototype; registered tools only"
    )
    desktop.add_argument("--state", type=Path, default=None)
    desktop.add_argument("--port", type=int, default=8765)
    commands.add_parser("sdk-demo", help="Scripted Pydantic AI dispatch; no neural inference")
    demo = commands.add_parser(
        "agent-demo",
        help="Actual local Qwen file/web/report workflow with execution-aware evidence",
    )
    demo.add_argument("--repository", type=Path, default=Path.cwd())
    demo.add_argument(
        "--output", type=Path, required=True, help="New evidence directory; never overwritten"
    )
    demo.add_argument("--model", choices=["qwen2.5", "qwen3", "qwen3-4b"], default="qwen3")
    demo.add_argument("--seed", type=int, default=9026)
    demo.add_argument(
        "--cases-file", type=Path, help="Reviewer-authored synthetic input; permissions fixed"
    )
    demo.add_argument(
        "--denial-feedback",
        action="store_true",
        help="Fixed safe guidance after a rejected, not-run action",
    )
    demo.add_argument("--model-port", type=int, default=8790)
    demo.add_argument(
        "--service-base-port",
        type=int,
        default=0,
        help="Fixed owned loopback range for matched trials",
    )
    demo.add_argument(
        "--case", action="append", dest="cases", help="Select case ID; repeat to select more"
    )
    bench = commands.add_parser(
        "benchmark", help="Replay versioned synthetic traces; no model inference"
    )
    bench.add_argument("--corpus", type=Path, default=Path("benchmarks/corpus-v1.json"))
    bench.add_argument("--output", type=Path, default=Path("benchmarks/results"))
    bench.add_argument("--seed", type=int, default=2026)
    bench.add_argument("--repeats", type=int, default=3)
    live = commands.add_parser(
        "live-evaluate", help="Run the pinned local neural model in the synthetic lab"
    )
    live.add_argument("--repeats", type=int, default=3)
    live.add_argument("--output", type=Path, default=Path("benchmarks/live-results"))
    live.add_argument("--model", choices=["qwen2.5", "qwen3", "qwen3-4b"], default="qwen2.5")
    live.add_argument("--release-tasks", action="store_true")
    adversarial = commands.add_parser("adversarial", help="Run frozen v3 synthetic contracts")
    adversarial.add_argument("--corpus", type=Path, default=Path("benchmarks/corpus-v3.json"))
    adversarial.add_argument("--output", type=Path, default=Path("benchmarks/results"))
    adversarial.add_argument("--repeats", type=int, default=3)
    adversarial.add_argument("--seed", type=int, default=3100)
    return cli


def main() -> None:
    cli = parser()
    args = cli.parse_args()
    if args.command == "agent-demo":
        try:
            from zyntrava.lab.agent_demo import run_local
        except ImportError:
            cli.error("Install the optional agent extra: zyntrava-shield[agent]")
        try:
            result = run_local(
                args.repository.resolve(),
                args.output.resolve(),
                model_name=args.model,
                seed=args.seed,
                port=args.model_port,
                case_ids=args.cases,
                cases_file=args.cases_file,
                denial_feedback=args.denial_feedback,
                service_base_port=args.service_base_port,
            )
        except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
            cli.error(
                f"Agent demo stopped ({type(exc).__name__}). Check model installation, port and "
                "output/results.json; use a NEW output directory for a retry."
            )
        print(f"Synthetic live-agent evidence: {result}")
        return
    if args.command == "desktop":
        from zyntrava.desktop import DesktopError, launch

        try:
            launch(args.state, args.port)
        except DesktopError as exc:
            cli.error(str(exc))
        return
    if args.command == "sdk-demo":
        try:
            from zyntrava.sdk_example import demo
        except ImportError:
            cli.error(
                "The SDK example needs the optional agent extra. Install zyntrava-shield[agent]."
            )
        print(demo())
        return
    if args.command == "adversarial":
        from zyntrava.lab.adversarial import run_adversarial

        print(run_adversarial(args.corpus, args.output, repeats=args.repeats, seed=args.seed))
        return
    if args.command == "live-evaluate":
        from zyntrava.lab.live import run_live

        print(
            run_live(
                Path.cwd(),
                args.output,
                args.repeats,
                model_name=args.model,
                include_release=args.release_tasks,
            )
        )
        return
    if args.command == "init-lab":
        state = args.state.resolve()
        if state.exists():
            cli.error(
                "State directory already exists; choose a new empty path. Nothing overwritten."
            )
        initialize_lab(state)
        print(f"Synthetic workspace and policy created at {state}")
        return
    if args.command == "benchmark":
        from zyntrava.lab.benchmark import run_benchmark

        result = run_benchmark(args.corpus, args.output, seed=args.seed, repeats=args.repeats)
        print(f"Synthetic trace results: {result.resolve()}")
        return
    if not 1024 <= args.port <= 65535:
        cli.error("port must be between 1024 and 65535")
    if args.retention_days is not None and not 1 <= args.retention_days <= 365:
        cli.error("retention-days must be between 1 and 365")
    state = args.state.resolve()
    if not (state / "policy.json").is_file():
        cli.error("Run init-lab first, or supply an initialized --state directory")
    try:
        runtime = local_application(
            state, Path.cwd(), args.port, retention_days=args.retention_days
        )
    except (OSError, ValueError):
        cli.error("Could not load local state. Check policy and permissions; nothing overwritten.")
    # Local ephemeral credentials intentionally printed once to the operator's terminal.
    # No token persistence, credential environment discovery, or access/request logging.
    print("Synthetic lab API. Credentials expire when the process stops.", flush=True)
    print(f"Operator bearer: {runtime.operator_token}", flush=True)
    print(f"Agent bearer: {runtime.agent_token}", flush=True)
    print(f"Dashboard: http://127.0.0.1:{args.port}/app/", flush=True)
    uvicorn.run(
        runtime.app,
        host="127.0.0.1",
        port=args.port,
        access_log=False,
        log_level="warning",
        limit_concurrency=32,
        timeout_keep_alive=5,
    )
