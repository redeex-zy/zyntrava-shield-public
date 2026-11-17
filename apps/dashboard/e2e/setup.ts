import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
export default async function setup() {
  const root = resolve('../..'); const python = process.env.ZYNTRAVA_TEST_PYTHON || resolve(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  mkdirSync(resolve(root, 'artifacts'), { recursive: true });
  const state = `.state/browser-${Date.now()}`;
  const initialized = spawnSync(python, ['-m', 'zyntrava', 'init-lab', '--state', state], { cwd: root, encoding: 'utf8', windowsHide: true });
  if (initialized.status !== 0) throw new Error('Could not initialize browser test workspace');
  const child = spawn(python, ['-u', '-m', 'zyntrava', 'serve', '--state', state, '--port', '8876'], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = ''; child.stdout.on('data', chunk => { output += chunk.toString(); });
  for (let i = 0; i < 100; i++) {
    const match = output.match(/Operator bearer: ([^\r\n]+)/);
    if (match) process.env.ZYNTRAVA_BROWSER_OPERATOR = match[1];
    const ready = await fetch('http://127.0.0.1:8876/health').then(r => r.ok).catch(() => false);
    if (ready && match) return async () => { child.kill(); };
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  child.kill(); throw new Error('Local backend did not become ready');
}
