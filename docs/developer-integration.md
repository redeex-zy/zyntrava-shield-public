# Connect a supported Pydantic AI agent

`zyntrava.adapters.pydantic_agent.run_agent_detailed(model, broker, prompt)` creates
and binds a fresh broker session, registers broker-backed tools and gates its returned
final text. It does not discover/intercept unrelated agents.

Minimal initialization pattern, using caller-owned synthetic paths and Model:

```python
from zyntrava.adapters.pydantic_agent import run_agent_detailed
from zyntrava.audit import AuditStore
from zyntrava.broker import Broker
from zyntrava.policy import Policy, Rule
from zyntrava.tools import LabTools

policy = Policy(version=1, name="read-status", rules=(
    Rule(id="status", tool="read_file", effect="allow",
         path_prefix="public/status.txt"),
))
broker = Broker(policy, LabTools(workspace), AuditStore(audit_path), simulated=True)
session_id, result = await run_agent_detailed(
    model, broker, "Read public/status.txt using read_file.")
```

`workspace`, `audit_path` and `model` are trusted operator objects, not values from
retrieved documents. Complete runnable initialization is in
`examples/connect_local_agent.py`; the full file/report/injection example is
`examples/preview_agent.py`, using `src/zyntrava/lab/agent_demo.py:run_case`.
The no-GPU exercise injects FunctionModel explicitly; live mode owns pinned Qwen.

The adapter's read/write/POST functions submit closed ToolRequests to the existing
broker. Registering a tool does not authorize all arguments. Fetch is opt-in and
still needs an explicit numeric-loopback destination. Exact report keys require
`exact_body_fields=True`; legacy required-field rules can permit additional keys.
Count release is another operator option and is not enabled in this preview.

Approvals are operator-only, exact-action/session/policy-bound, expiring and single-use.
The model cannot approve itself. Pending, failed and unknown effects are not success;
do not retry uncertainty or reset classified session state. The SDK is not a durable
workflow engine or an exactly-once transaction system.

Covered: registered `read_file`, `write_file`, `post_message`, optional `fetch_page`,
and returned final text through the adapter's output validator. Not covered: raw
provider messages/transport, captures/logs, arbitrary Python callbacks, shell/native/
custom/MCP tools, persistent memory, unrelated apps or the OS. Adding an alternate
executor and bypassing submission invalidates the coverage claim.

`Outcome.status == "blocked"` is authorization data, not the service's business
status. Whether the original task completes is graded from receiver/filesystem state.
Experimental recovery modules are not part of the default integration.

## Local v0.9.2 candidate

`execution="failed"` now means a known failure without a protected write/network
effect or released tool data. A dispatch whose effects cannot be established uses
`unknown`, withholds output and halts further dispatch/final-answer release for
that session. The adapter raises `AgentExecutionUncertain` and stops the run;
model denial feedback is not the enforcement mechanism. Do not automatically
start a replacement run after this exception. Inspect real service/file receipts
with the trusted operator. A successful HTTP response is not business-task proof.

`broker.retire_session(session_id)` is **operator-only**: it invalidates the ID and
pending grants, even when retirement auditing fails. It does not erase model
memory or permit old classified history to be resumed in a fresh session. No
agent tool/API route exposes retirement. Completed SDK callers may use
`retire_on_exit=True` with `run_agent`/`run_agent_detailed`; this also cancels
pending approvals, so leave it false if an operator still needs to resolve them.
The legacy default is false. Retire finished sessions to stay below the 1,000
active-session cap; agent credentials still cannot mint/reset sessions.

The strict profile is optional:

```python
from zyntrava.policy import strict_status_policy

policy = strict_status_policy(owned_receiver_url)
# Allows public/status.txt and only {"status":"ready"} to that exact loopback URL.
# This does not register another tool or authorize an arbitrary network destination.
```

Run `python examples/strict_status.py` in the installed environment for a scripted
Pydantic AI example with actual broker/file/HTTP effects. The extra-field proposal
is rejected, exactly one valid report is received, and the finished session is
retired. This is not neural inference or a new attack-success benchmark.
See [migration, diagnostics and limitations](v0.9.2-security-hardening.md).
