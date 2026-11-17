# Developer-preview demonstration plan

Freeze before live inference. This is an onboarding demonstration, not an attack
benchmark, an independent evaluation or a recovery-method experiment.

Use the unchanged Pydantic AI adapter/broker/policy and bundled clean-file and
private-prerequisite cases. Preserve corpus SHA-256
`2cd93f5982928b4f0f180fcbf63c81f0a8d86503eec97042c6d812ef139c30f4`.
Qwen3-4B Q4_K_M, pinned model/runtime, seed 9026, original temperature 0.2,
512 output tokens, eight requests/tool calls, 90-second task timeout. Fixed owned
receiver ports 18870/18871, model port 8790. No fixed denial feedback, completion
checkpoint, forced tool choice or new authority. Real files and loopback HTTP only.

Run once and retain both tasks, including failures/nonactivation. Do not rerun seeds
until a favorable clip appears. Independently regrade actual proposals/effects with
the existing `agent09-execution-v2` grader. A final promise is not completion. Record
encounter, activation, rejected/not-run proposals, actual forbidden/duplicate effects
and legitimate completion separately. No guaranteed recovery score.

The no-GPU onboarding check uses an explicitly scripted FunctionModel with the same
real broker/files/receiver. It is not neural inference or evidence that a model
followed an attack. Keep that label visible in outputs, README and video materials.

Create a new publication-candidate demo ZIP from the full two-task run: preserved
source hash/provenance, model settings, all proposals, outcomes, native framework
messages, receipts, observed effects and original/recomputed grades. Exclude
workspaces, audit databases, credentials, machine paths and Git identity. Sanitize
only a copy; never edit raw evidence. Reject unexpected data rather than silently
claiming it safe. Include a file checksum inventory and explicit sanitization notes.

If the live attack does not activate or the task fails, the storyboard must report
that observed outcome. Any historical illustrative successful trace must be clearly
identified, accompanied by its full run and negative-results context, and must not
be called the fresh run or a success rate. Do not render or publish a video.
