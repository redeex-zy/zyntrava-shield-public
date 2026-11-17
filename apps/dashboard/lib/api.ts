export type Evidence = { category: string; rule: string; detail: string };
export type AuditEvent = { id: string; created_at: string; sequence: number; status: string; execution: string; phase: string; tool?: string; simulated: boolean; detected: boolean; decision?: { evidence: Evidence[]; rule_ids: string[]; policy_digest: string }; evidence?: Evidence[]; experiment_id?: string; observed_at?: string };
export type Overview = { evaluated_actions: number; blocked_actions: number; allowed_actions: number; pending_approvals: number; security_alert_events: number; connected_agents: number; protection_state: string; workspace_mode: string; version: string; available_jobs?: string[] };
export type Rule = { id: string; tool: string; effect: string; path_prefix: string | null; destination: string | null };
export type Policy = { version: number; name: string; rules: Rule[]; sensitive_roots: string[]; release_rules?: { id: string; source: string; destination: string; projector: string; max_records: number; max_releases: number }[] };
export type PolicyResponse = { policy: Policy; digest: string; editing: string };
export type Approval = { id: string; action: { tool: string; arguments: Record<string, unknown> }; policy_digest: string; expires_in_seconds: number; session_id: string };
export type Integration = { id: string; name: string; installed: boolean; connected: boolean; status: string; last_experiment: string | null; coverage: string; permissions: string[] };
export type Metrics = { unauthorized_actions_executed: number; unauthorized_actions: number; legitimate_task_completion: number | null; attack_success_rate: number | null; median_action_ms: number; scenarios: number };
export type ExecutionMetrics = { reference_forbidden_proposal: number; rejected_before_execution: number; unauthorized_effect_observed: number; protected_value_exposure_observed: number; source_derived_exposure_observed: number; benign_workflows: number; benign_workflows_completed: number };
export type Result = { experiment_id: string; created_at: string; kind: string; corpus_version: string | null; repeats: number; seed: number | null; corpus_sha256: string | null; model_id: string | null; suite: string | null; metrics: Record<string, Metrics>; execution_metrics?: Record<string, ExecutionMetrics>; evaluation_methodologies?: string[]; limitations: string[]; live_rows: number };
export type Job = { id: string; kind: string; status: string; experiment_id: string | null; error: string | null };
export function jobSummary(job: Job): string {
  if (job.error) return job.error;
  if (job.experiment_id) return job.experiment_id;
  if (job.status === 'completed') {
    if (job.kind === 'recovery-demo') return 'Completed — verified outcome in task history';
    if (job.kind === 'demo') return 'Completed — decisions in Live Activity; approvals may still be pending';
    return 'Completed — no experiment artifact recorded';
  }
  if (job.status === 'failed') return 'Failed — no experiment result available';
  return job.status === 'queued' ? 'Queued' : 'Results pending';
}
export type Settings = { retention_days: number; poll_seconds: number; protection_mode: 'full' };
export async function api<T>(path: string, token: string, body?: unknown, method = 'GET'): Promise<T> {
  const response = await fetch(path, { method, headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(15000), cache: 'no-store' });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(`${response.status}: ${typeof detail.detail === 'string' ? detail.detail : 'Request failed'}`);
  }
  return response.json() as Promise<T>;
}
export function percentage(n: number | null | undefined): string { return typeof n === 'number' && Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : 'Not measured'; }
export function evidence(event: AuditEvent): Evidence[] { return event.decision?.evidence ?? event.evidence ?? []; }

export type TaskStatus = { id: string; state: string; read_done: number; claimed: number; actions: number; denials: number; recoveries: number; reason: string; updated: number };
