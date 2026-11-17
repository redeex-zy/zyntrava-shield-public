// Installed-package browser journey. Ephemeral operator bearer arrives over stdin, never a file.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const require = createRequire(new URL('../apps/dashboard/package.json', import.meta.url));
const { chromium } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
let input = '';
for await (const chunk of process.stdin) input += chunk;
const { url, token, output, lean = true } = JSON.parse(input);
if (!/^http:\/\/127\.0\.0\.1:\d+\/app\/$/.test(url)) throw new Error('Owned loopback URL required');
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const errors = []; page.on('pageerror', e => errors.push(e.name));
const checks = {};
const assert = (value, message) => { if (!value) throw new Error(message); };
try {
  await page.goto(url);
  await page.getByLabel('Operator bearer').fill(token);
  await page.getByRole('button', { name: /Connect to local workspace/ }).click();
  await page.getByRole('heading', { name: 'Your agent’s security boundary.' }).waitFor();
  checks.authenticated_dashboard = true;
  await page.getByRole('button', { name: 'Research Laboratory', exact: true }).click();
  if (lean) {
    await page.getByRole('note').filter({ hasText: 'Desktop prototype' }).waitFor();
    assert(await page.getByRole('button', { name: /Run corpus v/ }).isDisabled(), 'Trace job unexpectedly enabled');
    assert(await page.getByRole('button', { name: 'Run local-model experiment' }).isDisabled(), 'Live job unexpectedly enabled');
    checks.excluded_research_disabled = true;
  } else {
    assert(await page.getByRole('button', { name: /Run corpus v/ }).isEnabled(), 'Installed research corpus unavailable');
    checks.research_profile_available = true;
  }
  await page.getByRole('button', { name: 'Run synthetic demonstration' }).click();
  await page.getByText('completed', { exact: true }).waitFor({ timeout: 15000 });
  await page.getByText('Completed — decisions in Live Activity; approvals may still be pending').waitFor();
  assert(await page.getByText('Results pending', { exact: true }).count() === 0, 'Completed demo still pending');
  checks.completed_job_status = true;
  await page.getByRole('button', { name: 'Policies', exact: true }).click();
  await page.getByRole('button', { name: 'Approve exact action' }).click();
  await page.getByText('No actions waiting for approval.').waitFor();
  checks.demo_and_approval = true;
  await page.getByRole('button', { name: 'Agent Integrations', exact: true }).click();
  await page.getByText('disconnected', { exact: true }).waitFor();
  checks.honest_disconnected_state = true;
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  if (lean) {
    await page.getByText('Not installed; desktop bundle excludes model assets.').waitFor();
    checks.honest_model_requirements = true;
  }
  await page.getByRole('button', { name: 'Overview', exact: true }).click();
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  writeFileSync(resolve(output, 'accessibility.json'), JSON.stringify(axe, null, 2));
  assert(axe.violations.length === 0, 'Selected dashboard accessibility violations');
  checks.selected_axe_check = true;
  await page.keyboard.press('Tab');
  assert(await page.evaluate(() => document.activeElement !== document.body), 'No keyboard focus');
  checks.keyboard_focus = true;
  await page.screenshot({ path: resolve(output, 'installed-dashboard.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile overflow');
  checks.mobile_no_horizontal_overflow = true;
  assert(errors.length === 0, 'Browser runtime error');
  checks.no_page_errors = true;
  writeFileSync(resolve(output, 'browser-checks.json'), JSON.stringify({ checks }, null, 2));
  console.log(JSON.stringify({ checks }));
} finally { await browser.close(); }
