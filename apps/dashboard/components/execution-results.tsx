import type { ExecutionMetrics } from '../lib/api';

export function ExecutionResults({ metrics }: { metrics?: Record<string, ExecutionMetrics> }) {
  if (!metrics || !Object.keys(metrics).length) return null;
  return <div className="table-wrap"><table>
    <caption>Execution-aware evidence · v4.0 · finite synthetic canary oracle</caption>
    <thead><tr><th>Configuration</th><th>Forbidden proposals</th><th>Rejected before execution</th><th>Forbidden effects observed</th><th>Protected-value exposures</th><th>Source-derived exposures</th><th>Benign completed</th></tr></thead>
    <tbody>{Object.entries(metrics).map(([arm, m]) => <tr key={arm}><th>{arm}</th>
      <td>{m.reference_forbidden_proposal}</td><td>{m.rejected_before_execution}</td>
      <td>{m.unauthorized_effect_observed}</td><td>{m.protected_value_exposure_observed}</td>
      <td>{m.source_derived_exposure_observed}</td><td>{m.benign_workflows_completed} / {m.benign_workflows}</td>
    </tr>)}</tbody>
  </table><p className="small muted">Proposals, rejected calls and actual disclosure are different measurements. Unmatched encodings are not proven safe. Repeats add no attack diversity.</p></div>;
}
