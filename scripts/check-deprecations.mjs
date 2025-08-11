#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const root = process.cwd();
const lockfile = `${root}/pnpm-lock.yaml`;

if (!existsSync(lockfile)) {
  console.log('[deprecations] No pnpm-lock.yaml found. Skipping deprecation scan.');
  process.exit(0);
}

function run(cmd, args) {
  return spawnSync(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'], shell: true, encoding: 'utf-8' });
}

let foundDeprecated = false;

// Try pnpm list JSON and scan for deprecation markers in text (pnpm 9 removed --deprecated flag)
try {
  const res = run('pnpm', ['ls', '--depth', '100', '--json']);
  const output = `${res.stdout || ''}\n${res.stderr || ''}`;
  if (/deprecated/i.test(output)) {
    foundDeprecated = true;
    console.error('\n[deprecations] Deprecated packages detected (from pnpm ls output). Please review and update:');
    console.error(output);
  }
} catch {}

// Fallback: npm ls which often prints deprecation notices
if (!foundDeprecated) {
  try {
    const resNpm = run('npm', ['ls', '--depth=9999']);
    const outNpm = `${resNpm.stdout || ''}\n${resNpm.stderr || ''}`;
    if (/deprecated/i.test(outNpm)) {
      foundDeprecated = true;
      console.error('\n[deprecations] Deprecated packages detected (from npm ls output). Please review and update:');
      console.error(outNpm);
    }
  } catch {}
}

if (foundDeprecated) {
  // Non-zero to make it visible in CI pipelines if enabled via verify-all chaining
  process.exit(1);
}

console.log('[deprecations] No deprecated packages detected or scanner unsupported.');
