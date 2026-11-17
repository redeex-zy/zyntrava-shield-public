"""Pydantic AI tool-calling runtime with exclusively broker-backed function tools.

The model is injected by the operator. The bundled smoke run uses FunctionModel,
an explicit test double. No live inference or prompt-injection robustness is implied.
"""

import asyncio

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.run import AgentRunResult
from pydantic_ai.usage import UsageLimits

from zyntrava.adapters.feedback import tool_result
from zyntrava.broker import Broker
from zyntrava.models import ToolRequest


def _build_agent(
    model: Model,
    broker: Broker,
    session_id: str,
    *,
    enable_fetch: bool = False,
    enable_release: bool = False,
    denial_feedback: bool = False,
) -> Agent[None, str]:
    agent: Agent[None, str] = Agent(
        model, instructions="Use the provided tools. Report their enforcement outcome accurately."
    )

    @agent.output_validator
    def release_answer(ctx: RunContext[None], output: str) -> str:
        outcome = broker.final_answer(session_id, output)
        return outcome.output if outcome.output is not None else "Final answer withheld by policy."

    @agent.tool(sequential=True)
    def read_file(ctx: RunContext[None], path: str) -> str:
        """Read an authorized UTF-8 file in the controlled workspace."""
        return tool_result(
            broker.submit(session_id, ToolRequest(tool="read_file", arguments={"path": path})),
            denial_feedback,
        )

    @agent.tool(sequential=True)
    def write_file(ctx: RunContext[None], path: str, content: str) -> str:
        """Propose creation of a report file, subject to operator approval."""
        return tool_result(
            broker.submit(
                session_id,
                ToolRequest(tool="write_file", arguments={"path": path, "content": content}),
            ),
            denial_feedback,
        )

    @agent.tool(sequential=True)
    def post_message(ctx: RunContext[None], url: str, body: str) -> str:
        """Send a permitted message to an explicitly allowed local lab receiver."""
        return tool_result(
            broker.submit(
                session_id, ToolRequest(tool="post_message", arguments={"url": url, "body": body})
            ),
            denial_feedback,
        )

    if enable_fetch:

        @agent.tool(sequential=True)
        def fetch_page(ctx: RunContext[None], url: str) -> str:
            """Fetch a page from an explicitly authorized numeric-loopback lab endpoint."""
            return tool_result(
                broker.submit(session_id, ToolRequest(tool="fetch_page", arguments={"url": url})),
                denial_feedback,
            )

    if enable_release:

        @agent.tool(sequential=True)
        def export_count(ctx: RunContext[None], path: str, url: str) -> str:
            """Release only a record count through an explicitly granted trusted projector."""
            return tool_result(
                broker.submit(
                    session_id,
                    ToolRequest(tool="export_count", arguments={"path": path, "url": url}),
                ),
                denial_feedback,
            )

    return agent


def run_agent(model: Model, broker: Broker, prompt: str) -> str:
    return asyncio.run(run_agent_detailed(model, broker, prompt))[1].output


async def run_agent_detailed(
    model: Model,
    broker: Broker,
    prompt: str,
    *,
    seed: int = 2026,
    enable_fetch: bool = False,
    enable_release: bool = False,
    denial_feedback: bool = False,
) -> tuple[str, AgentRunResult[str]]:
    if len(prompt) > 32768:
        raise ValueError("prompt exceeds the 32 Ki-character source limit")
    session_id = broker.create_session()
    broker.observe(session_id, prompt, "user")
    result = await _build_agent(
        model,
        broker,
        session_id,
        enable_fetch=enable_fetch,
        enable_release=enable_release,
        denial_feedback=denial_feedback,
    ).run(
        prompt,
        usage_limits=UsageLimits(request_limit=8, tool_calls_limit=8),
        model_settings={
            "temperature": 0.2,
            "max_tokens": 512,
            "seed": seed,
            "parallel_tool_calls": False,
        },
        timeout=90,
    )
    return session_id, result
