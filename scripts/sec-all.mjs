#!/usr/bin/env node
import { spawn } from 'node:child_process';

function run(cmd, args = [], opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { shell: true, stdio: 'inherit', ...opts });
    child.on('exit', (code) => resolve(code ?? 0));
    child.on('error', () => resolve(127));
  });
}

async function exists(cmd) {
  const code = await run(process.platform === 'win32' ? 'where' : 'which', [cmd]);
  return code === 0;
}

async function main() {
  let failed = false;

  // osv-scanner
  if (await exists('osv-scanner')) {
    const osvArgs = ['--recursive', '.'];
    const code = await run('osv-scanner', osvArgs);
    if (code !== 0) failed = true;
  } else {
    console.warn('[sec] osv-scanner not found. Skipping.');
  }

  // trivy filesystem scan
  if (await exists('trivy')) {
    const trivyArgs = ['fs', '--scanners', 'vuln', '--severity', 'HIGH,CRITICAL', '--exit-code', '1', '--no-progress', '--skip-dirs', 'node_modules', '.'];
    const code = await run('trivy', trivyArgs);
    if (code !== 0) failed = true;
  } else {
    console.warn('[sec] trivy not found. Skipping.');
  }

  // Also run deprecation scan here
  const depCode = await run('node', ['scripts/check-deprecations.mjs']);
  if (depCode !== 0) failed = true;

  if (failed) {
    console.error('[sec] Security/deprecation checks failed.');
    process.exit(1);
  } else {
    console.log('[sec] All security/deprecation checks passed.');
  }
}

main();
