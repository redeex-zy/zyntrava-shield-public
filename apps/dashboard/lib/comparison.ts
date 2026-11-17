import type { Result } from './api';

export function comparisonProblem(a?: Result, b?: Result): string | null {
  if (!a || !b) return 'Choose two saved trace experiments.';
  if (a.experiment_id === b.experiment_id) return 'Choose different experiments.';
  if (!a.corpus_sha256 || a.corpus_sha256 !== b.corpus_sha256 || a.kind !== b.kind)
    return 'Datasets or experiment methods differ. Compare their full artifacts separately.';
  if (a.seed !== b.seed || a.repeats !== b.repeats)
    return 'Seeds or repeat counts differ. No paired comparison is shown.';
  if (JSON.stringify(a.evaluation_methodologies ?? ['legacy-static']) !== JSON.stringify(b.evaluation_methodologies ?? ['legacy-static']))
    return 'Evaluation methodologies differ. Review legacy and execution-aware evidence separately.';
  if (!Object.keys(a.metrics).length || !Object.keys(b.metrics).length)
    return 'Live-model transcripts need case-level review; trace metrics do not apply.';
  return null;
}
