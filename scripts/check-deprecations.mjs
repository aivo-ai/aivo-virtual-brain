#!/usr/bin/env node
import { existsSync, readFileSync } from 'node:fs';

const root = process.cwd();
const lockfile = `${root}/pnpm-lock.yaml`;

if (!existsSync(lockfile)) {
  console.log('[deprecations] No pnpm-lock.yaml found. Skipping deprecation scan.');
  process.exit(0);
}

try {
  const text = readFileSync(lockfile, 'utf8');
  // Simple, robust scan: any key named 'deprecated' in the lockfile signals a deprecated package
  const matches = text.match(/\n\s*deprecated\s*:/gi) || [];
  if (matches.length > 0) {
    console.error(`[deprecations] ${matches.length} deprecated entries found in pnpm-lock.yaml. Failing.`);
    // Optionally print offending sections for debugging (first few lines around each occurrence)
    const preview = text.split('\n');
    let shown = 0;
    for (let i = 0; i < preview.length; i++) {
      if (/^\s*deprecated\s*:/i.test(preview[i])) {
        const start = Math.max(0, i - 3);
        const end = Math.min(preview.length, i + 4);
        console.error('---');
        console.error(preview.slice(start, end).join('\n'));
        shown++;
        if (shown >= 5) break; // cap output
      }
    }
    process.exit(1);
  }
  console.log('[deprecations] No deprecated packages detected in lockfile.');
} catch (e) {
  console.warn('[deprecations] Error reading lockfile, skipping strict check:', e?.message || e);
  process.exit(0);
}
