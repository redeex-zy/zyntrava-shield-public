'use client';
import { useState } from 'react';
import { percentage, type Result } from '../lib/api';
import { comparisonProblem } from '../lib/comparison';

export function Comparison({ results }: { results: Result[] }) {
  const [left, setLeft] = useState(''); const [right, setRight] = useState('');
  const a = results.find(r => r.experiment_id === left);
  const b = results.find(r => r.experiment_id === right);
  const problem = comparisonProblem(a, b);
  return <section className="panel"><h2>Compare saved experiments</h2>
    <p className="muted">Paired display requires the same dataset hash, method, seed and repeats.
      Machine load and source versions can still differ. This is not an independent ranking.</p>
    <div className="filters">{[['First experiment', left, setLeft], ['Second experiment', right, setRight]].map(([label, value, change]) =>
      <label key={String(label)}>{String(label)}<select aria-label={String(label)} value={String(value)} onChange={e => (change as (v: string) => void)(e.target.value)}>
        <option value="">Choose experiment</option>{results.map(r => <option key={r.experiment_id} value={r.experiment_id}>{r.experiment_id}</option>)}
      </select></label>)}</div>
    {problem ? <p role="status" className="small muted">{problem}</p> : <div className="table-wrap"><table>
      <caption>Measured held-out outcomes: first / second experiment</caption>
      <thead><tr><th>Configuration</th><th>Legacy contract-labeled executions</th><th>Benign completion</th><th>Median action</th></tr></thead>
      <tbody>{Object.entries(a!.metrics).filter(([arm]) => b!.metrics[arm]).map(([arm, x]) => {
        const y = b!.metrics[arm]; return <tr key={arm}><th>{arm}</th>
          <td>{x.unauthorized_actions_executed}/{x.unauthorized_actions} / {y.unauthorized_actions_executed}/{y.unauthorized_actions}</td>
          <td>{percentage(x.legitimate_task_completion)} / {percentage(y.legitimate_task_completion)}</td>
          <td>{x.median_action_ms.toFixed(2)} / {y.median_action_ms.toFixed(2)} ms</td></tr>;
      })}</tbody></table></div>}
  </section>;
}
