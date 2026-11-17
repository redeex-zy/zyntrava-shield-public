import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { comparisonProblem } from './comparison.ts';
import type { Result } from './api.ts';
import { percentage } from './api.ts';

const a = { experiment_id: 'a', kind: 'synthetic', corpus_sha256: 'same', seed: 3100,
  repeats: 3, metrics: { full: {} } } as unknown as Result;
describe('paired experiment guard', () => {
  it('does not display unmeasured rates as zero', () => {
    assert.equal(percentage(null), 'Not measured');
    assert.equal(percentage(0), '0.0%');
  });
  it('allows equivalent configurations and rejects mixed evidence', () => {
    assert.equal(comparisonProblem(a, { ...a, experiment_id: 'b' }), null);
    assert.ok(comparisonProblem(a, { ...a, experiment_id: 'b', corpus_sha256: 'different' })?.includes('Datasets'));
    assert.ok(comparisonProblem(a, { ...a, experiment_id: 'b', seed: 42 })?.includes('Seeds'));
    assert.ok(comparisonProblem(a, a)?.includes('different'));
    assert.ok(comparisonProblem(a, { ...a, experiment_id: 'b', evaluation_methodologies: ['v4'] })?.includes('methodologies'));
  });
});
