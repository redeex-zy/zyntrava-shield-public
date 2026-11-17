import assert from 'node:assert/strict';
import { describe, it, mock, afterEach } from 'node:test';
import { api, percentage } from './api.ts';
afterEach(() => mock.restoreAll());
describe('operator request contract', () => {
  it('uses bearer authentication without URL credentials', async () => {
    const fetcher = mock.method(globalThis, 'fetch', async () =>
      new Response(JSON.stringify({ status: 'saved' }), { status: 200 }));
    await api('/settings', 'synthetic-credential', { retention_days: 7 }, 'PUT');
    const [url, options] = fetcher.mock.calls[0].arguments;
    assert.equal(url, '/settings');
    assert.equal((options?.headers as Record<string, string>).Authorization, 'Bearer synthetic-credential');
    assert.equal(options?.body, '{"retention_days":7}');
  });
  it('surfaces safe structured errors', async () => {
    mock.method(globalThis, 'fetch', async () =>
      new Response(JSON.stringify({ detail: 'Policy changed' }), { status: 409 }));
    await assert.rejects(api('/policy', 'fixture'), { message: '409: Policy changed' });
    assert.equal(percentage(5 / 6), '83.3%');
  });
});
