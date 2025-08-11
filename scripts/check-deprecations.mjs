#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const root = process.cwd();
const lockfile = `${root}/pnpm-lock.yaml`;

if (!existsSync(lockfile)) {
  console.log('[deprecations] No pnpm-lock.yaml found. Skipping deprecation scan.');
  process.exit(0);
}

const res = spawnSync('pnpm', ['ls', '--deprecated'], {
  stdio: ['ignore', 'pipe', 'pipe'],
  shell: true,
  encoding: 'utf-8',
});

if (res.error) {
  console.warn('[deprecations] Could not run pnpm ls --deprecated:', res.error?.message || res.error);
  process.exit(0);
}

const stdout = res.stdout || '';
const stderr = res.stderr || '';
const output = `${stdout}\n${stderr}`;

if (/deprecated/i.test(output)) {
  console.error('\n[deprecations] Deprecated packages detected. Please review and update:');
  console.error(output);
  process.exit(1);
}

console.log('[deprecations] No deprecated packages detected.');
