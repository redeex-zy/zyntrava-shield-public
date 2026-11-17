import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { jobSummary, type Job } from './api.ts';

const demo: Job = { id: 'test', kind: 'demo', status: 'completed', experiment_id: null, error: null };
describe('actual job outcomes', () => {
  it('does not imply that completed activity and recovery demos await a result file', () => {
    assert.ok(jobSummary(demo).includes('Live Activity'));
    assert.ok(!jobSummary(demo).includes('Results pending'));
    assert.ok(jobSummary({ ...demo, kind: 'recovery-demo' }).includes('task history'));
    assert.ok(jobSummary({ ...demo, kind: 'trace' }).includes('no experiment artifact'));
  });
  it('preserves experiment identifiers and differentiates queued, running and failed', () => {
    assert.equal(jobSummary({ ...demo, experiment_id: 'trace-example' }), 'trace-example');
    assert.equal(jobSummary({ ...demo, status: 'queued' }), 'Queued');
    assert.equal(jobSummary({ ...demo, status: 'running' }), 'Results pending');
    assert.ok(jobSummary({ ...demo, status: 'failed' }).includes('Failed'));
    assert.equal(jobSummary({ ...demo, status: 'failed', error: 'TimeoutError' }), 'TimeoutError');
  });
});
