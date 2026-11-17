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
