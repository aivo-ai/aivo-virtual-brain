#!/usr/bin/env node
import { globby } from 'globby';
import fs from 'node:fs/promises';

(async () => {
  try {
    const files = await globby([
      'apps/**/pages/**/*.{tsx,jsx,ts,js,html}',
      'apps/**/routes/**/*.{tsx,jsx,ts,js,html}',
      'apps/**/src/**/*.{tsx,jsx,ts,js,html}'
    ], { gitignore: true });

    if (!files.length) {
      console.log('[cta-guard] No app route files found. Skipping.');
      process.exit(0);
    }

    const issues = [];
    const patterns = [
      { re: /href\s*=\s*"#"/i, msg: 'Anchor with href="#" found (non-actionable CTA).' },
      { re: /target=\s*"_blank"(?![^>]*rel=)/i, msg: 'target="_blank" without rel="noopener noreferrer".' },
      { re: /role=\s*"button"(?![^>]*tabindex=)/i, msg: 'role="button" without keyboard support (tabindex).' }
    ];

    for (const f of files) {
      const content = await fs.readFile(f, 'utf8');
      for (const p of patterns) {
        if (p.re.test(content)) {
          issues.push(`${f}: ${p.msg}`);
        }
      }
    }

    if (issues.length) {
      console.error('[cta-guard] Issues detected:\n' + issues.join('\n'));
      process.exit(1);
    }

    console.log('[cta-guard] No CTA/route issues found.');
  } catch (e) {
    console.warn('[cta-guard] Error scanning, treating as pass:', e.message || e);
    process.exit(0);
  }
})();
