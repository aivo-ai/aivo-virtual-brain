#!/usr/bin/env tsx

/**
 * Release Notes Generator for AIVO Virtual Brain
 * Generates comprehensive release notes from git history, commits, and PRs
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

interface Commit {
  hash: string;
  subject: string;
  body: string;
  author: string;
  date: string;
  type: string;
  scope?: string;
  breaking: boolean;
  files: string[];
}

interface ReleaseNotes {
  version: string;
  date: string;
  summary: string;
  highlights: string[];
  features: Commit[];
  fixes: Commit[];
  breaking: Commit[];
  chores: Commit[];
  security: Commit[];
  dependencies: Commit[];
  services: Record<string, Commit[]>;
  migration: string[];
  acknowledgments: string[];
}

class ReleaseNotesGenerator {
  private currentVersion: string;
  private previousVersion: string;
  private commits: Commit[] = [];

  constructor() {
    this.currentVersion = this.getCurrentVersion();
    this.previousVersion = this.getPreviousVersion();
  }

  private getCurrentVersion(): string {
    try {
      // Try to get version from git tag
      const tag = execSync('git describe --tags --exact-match HEAD 2>/dev/null || echo ""', {
        encoding: 'utf8'
      }).trim();
      
      if (tag) {
        return tag;
      }

      // Fallback to workflow input or generated version
      const version = process.env.GITHUB_REF_NAME || process.env.INPUT_VERSION;
      if (version) {
        return version;
      }

      // Generate version from date if no tag
      const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
      const shortSha = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim();
      return `v${date}-${shortSha}`;
    } catch (error) {
      console.error('Error getting current version:', error);
      return 'v0.0.0-unknown';
    }
  }

  private getPreviousVersion(): string {
    try {
      // Get the previous tag
      const previousTag = execSync(
        'git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo ""',
        { encoding: 'utf8' }
      ).trim();

      if (previousTag) {
        return previousTag;
      }

      // If no previous tag, use first commit
      const firstCommit = execSync(
        'git rev-list --max-parents=0 HEAD',
        { encoding: 'utf8' }
      ).trim();

      return firstCommit;
    } catch (error) {
      console.error('Error getting previous version:', error);
      return 'HEAD~10'; // Fallback to last 10 commits
    }
  }

  private parseCommits(): void {
    try {
      const gitLog = execSync(
        `git log ${this.previousVersion}..HEAD --pretty=format:"%H|%s|%b|%an|%ai" --name-only`,
        { encoding: 'utf8' }
      );

      const commitEntries = gitLog.split('\n\n').filter(Boolean);
      
      for (const entry of commitEntries) {
        const lines = entry.split('\n');
        const [hash, subject, body, author, date] = lines[0].split('|');
        const files = lines.slice(1).filter(Boolean);

        const commit = this.parseCommitMessage({
          hash: hash?.substring(0, 7) || '',
          subject: subject || '',
          body: body || '',
          author: author || '',
          date: date || '',
          files
        });

        if (commit) {
          this.commits.push(commit);
        }
      }
    } catch (error) {
      console.error('Error parsing commits:', error);
      this.commits = [];
    }
  }

  private parseCommitMessage(raw: any): Commit | null {
    const { hash, subject, body, author, date, files } = raw;

    // Parse conventional commit format
    const conventionalRegex = /^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([^)]+\))?(!)?: (.+)$/;
    const match = subject.match(conventionalRegex);

    if (!match) {
      // Non-conventional commits are treated as chores
      return {
        hash,
        subject,
        body,
        author,
        date,
        type: 'chore',
        breaking: false,
        files
      };
    }

    const [, type, scopeMatch, breaking, description] = match;
    const scope = scopeMatch?.slice(1, -1); // Remove parentheses

    return {
      hash,
      subject: description,
      body,
      author,
      date,
      type,
      scope,
      breaking: !!breaking || body.includes('BREAKING CHANGE'),
      files
    };
  }

  private categorizeCommits(): ReleaseNotes {
    const notes: ReleaseNotes = {
      version: this.currentVersion,
      date: new Date().toISOString().split('T')[0],
      summary: '',
      highlights: [],
      features: [],
      fixes: [],
      breaking: [],
      chores: [],
      security: [],
      dependencies: [],
      services: {},
      migration: [],
      acknowledgments: []
    };

    // Categorize commits
    for (const commit of this.commits) {
      if (commit.breaking) {
        notes.breaking.push(commit);
      }

      switch (commit.type) {
        case 'feat':
          notes.features.push(commit);
          break;
        case 'fix':
          notes.fixes.push(commit);
          break;
        case 'security':
        case 'sec':
          notes.security.push(commit);
          break;
        case 'deps':
        case 'build':
          if (commit.subject.includes('bump') || commit.subject.includes('update')) {
            notes.dependencies.push(commit);
          } else {
            notes.chores.push(commit);
          }
          break;
        default:
          notes.chores.push(commit);
      }

      // Group by service/scope
      if (commit.scope) {
        if (!notes.services[commit.scope]) {
          notes.services[commit.scope] = [];
        }
        notes.services[commit.scope].push(commit);
      }
    }

    // Generate summary and highlights
    notes.summary = this.generateSummary(notes);
    notes.highlights = this.generateHighlights(notes);
    notes.migration = this.generateMigrationNotes(notes);
    notes.acknowledgments = this.generateAcknowledments();

    return notes;
  }

  private generateSummary(notes: ReleaseNotes): string {
    const featureCount = notes.features.length;
    const fixCount = notes.fixes.length;
    const serviceCount = Object.keys(notes.services).length;

    let summary = `Release ${notes.version} includes `;
    
    if (featureCount > 0) {
      summary += `${featureCount} new feature${featureCount > 1 ? 's' : ''}`;
    }
    
    if (fixCount > 0) {
      if (featureCount > 0) summary += ', ';
      summary += `${fixCount} bug fix${fixCount > 1 ? 'es' : ''}`;
    }
    
    if (serviceCount > 0) {
      if (featureCount > 0 || fixCount > 0) summary += ', and ';
      summary += `updates to ${serviceCount} service${serviceCount > 1 ? 's' : ''}`;
    }
    
    summary += '.';

    if (notes.breaking.length > 0) {
      summary += ` ⚠️ This release contains ${notes.breaking.length} breaking change${notes.breaking.length > 1 ? 's' : ''}.`;
    }

    if (notes.security.length > 0) {
      summary += ` 🔒 This release includes ${notes.security.length} security improvement${notes.security.length > 1 ? 's' : ''}.`;
    }

    return summary;
  }

  private generateHighlights(notes: ReleaseNotes): string[] {
    const highlights: string[] = [];

    // Major features
    const majorFeatures = notes.features.filter(c => 
      c.subject.toLowerCase().includes('implement') ||
      c.subject.toLowerCase().includes('add') && c.subject.length > 50
    );

    majorFeatures.forEach(feature => {
      highlights.push(`🚀 ${feature.subject}`);
    });

    // Critical fixes
    const criticalFixes = notes.fixes.filter(c =>
      c.subject.toLowerCase().includes('critical') ||
      c.subject.toLowerCase().includes('security') ||
      c.subject.toLowerCase().includes('vulnerability')
    );

    criticalFixes.forEach(fix => {
      highlights.push(`🔧 ${fix.subject}`);
    });

    // New services
    const newServices = notes.features.filter(c =>
      c.scope && !['ui', 'web', 'docs', 'test'].includes(c.scope)
    );

    newServices.forEach(service => {
      highlights.push(`⚡ New service: ${service.scope}`);
    });

    return highlights.slice(0, 5); // Limit to top 5 highlights
  }

  private generateMigrationNotes(notes: ReleaseNotes): string[] {
    const migration: string[] = [];

    // Breaking changes require migration
    notes.breaking.forEach(change => {
      if (change.body.includes('BREAKING CHANGE:')) {
        const breakingText = change.body.split('BREAKING CHANGE:')[1]?.trim();
        if (breakingText) {
          migration.push(`⚠️ ${breakingText}`);
        }
      } else {
        migration.push(`⚠️ ${change.subject} - Check documentation for migration steps`);
      }
    });

    // Database changes
    const dbChanges = this.commits.filter(c =>
      c.files.some(f => f.includes('migration') || f.includes('schema')) ||
      c.subject.toLowerCase().includes('database') ||
      c.subject.toLowerCase().includes('schema')
    );

    dbChanges.forEach(change => {
      migration.push(`🗄️ Database changes detected - Run migrations before deployment`);
    });

    // Configuration changes
    const configChanges = this.commits.filter(c =>
      c.files.some(f => f.includes('.env') || f.includes('config')) ||
      c.subject.toLowerCase().includes('config')
    );

    if (configChanges.length > 0) {
      migration.push(`⚙️ Configuration updates required - Check .env.example for new variables`);
    }

    return [...new Set(migration)]; // Remove duplicates
  }

  private generateAcknowledments(): string[] {
    const authors = [...new Set(this.commits.map(c => c.author))];
    return authors.map(author => `Thanks to @${author.replace(/\s+/g, '-').toLowerCase()} for their contributions! 🙏`);
  }

  private formatMarkdown(notes: ReleaseNotes): string {
    let markdown = `# Release ${notes.version}\n\n`;
    markdown += `**Release Date:** ${notes.date}\n\n`;
    markdown += `${notes.summary}\n\n`;

    // Highlights
    if (notes.highlights.length > 0) {
      markdown += `## ✨ Highlights\n\n`;
      notes.highlights.forEach(highlight => {
        markdown += `- ${highlight}\n`;
      });
      markdown += '\n';
    }

    // Breaking Changes
    if (notes.breaking.length > 0) {
      markdown += `## ⚠️ Breaking Changes\n\n`;
      notes.breaking.forEach(change => {
        markdown += `- **${change.scope || 'core'}**: ${change.subject} (${change.hash})\n`;
        if (change.body) {
          markdown += `  ${change.body.split('\n')[0]}\n`;
        }
      });
      markdown += '\n';
    }

    // Migration Notes
    if (notes.migration.length > 0) {
      markdown += `## 🔄 Migration Guide\n\n`;
      notes.migration.forEach(note => {
        markdown += `- ${note}\n`;
      });
      markdown += '\n';
    }

    // Features
    if (notes.features.length > 0) {
      markdown += `## 🚀 New Features\n\n`;
      notes.features.forEach(feature => {
        markdown += `- **${feature.scope || 'core'}**: ${feature.subject} (${feature.hash})\n`;
      });
      markdown += '\n';
    }

    // Bug Fixes
    if (notes.fixes.length > 0) {
      markdown += `## 🐛 Bug Fixes\n\n`;
      notes.fixes.forEach(fix => {
        markdown += `- **${fix.scope || 'core'}**: ${fix.subject} (${fix.hash})\n`;
      });
      markdown += '\n';
    }

    // Security
    if (notes.security.length > 0) {
      markdown += `## 🔒 Security\n\n`;
      notes.security.forEach(security => {
        markdown += `- **${security.scope || 'core'}**: ${security.subject} (${security.hash})\n`;
      });
      markdown += '\n';
    }

    // Service Changes
    if (Object.keys(notes.services).length > 0) {
      markdown += `## 📦 Service Updates\n\n`;
      Object.entries(notes.services).forEach(([service, commits]) => {
        markdown += `### ${service}\n`;
        commits.forEach(commit => {
          const icon = commit.type === 'feat' ? '✨' : commit.type === 'fix' ? '🔧' : '📝';
          markdown += `- ${icon} ${commit.subject} (${commit.hash})\n`;
        });
        markdown += '\n';
      });
    }

    // Dependencies
    if (notes.dependencies.length > 0) {
      markdown += `## 📚 Dependencies\n\n`;
      notes.dependencies.forEach(dep => {
        markdown += `- ${dep.subject} (${dep.hash})\n`;
      });
      markdown += '\n';
    }

    // Docker Images
    markdown += `## 🐳 Container Images\n\n`;
    markdown += `All container images are signed with Cosign and include SBOMs:\n\n`;
    
    // Get list of services with Dockerfiles
    try {
      const services = execSync('find services -name "Dockerfile" -type f | sed "s|services/||" | sed "s|/Dockerfile||"', {
        encoding: 'utf8'
      }).trim().split('\n').filter(Boolean);

      services.forEach(service => {
        markdown += `- \`ghcr.io/aivo-ai/aivo-virtual-brain/${service}:${notes.version}\`\n`;
      });
    } catch (error) {
      console.error('Error listing services:', error);
    }
    
    markdown += '\n';

    // Verification
    markdown += `## 🔐 Verification\n\n`;
    markdown += `Verify image signatures with Cosign:\n\n`;
    markdown += '```bash\n';
    markdown += `cosign verify ghcr.io/aivo-ai/aivo-virtual-brain/<service>:${notes.version} \\\n`;
    markdown += `  --certificate-identity-regexp="https://github.com/aivo-ai/aivo-virtual-brain" \\\n`;
    markdown += `  --certificate-oidc-issuer="https://token.actions.githubusercontent.com"\n`;
    markdown += '```\n\n';

    // Acknowledgments
    if (notes.acknowledgments.length > 0) {
      markdown += `## 🙏 Acknowledgments\n\n`;
      notes.acknowledgments.forEach(ack => {
        markdown += `${ack}\n`;
      });
      markdown += '\n';
    }

    // Footer
    markdown += `---\n\n`;
    markdown += `**Full Changelog**: https://github.com/aivo-ai/aivo-virtual-brain/compare/${this.previousVersion}...${this.currentVersion}\n`;
    markdown += `**Docker Images**: https://github.com/aivo-ai/aivo-virtual-brain/pkgs/container/aivo-virtual-brain\n`;
    markdown += `**Release Assets**: Includes SBOMs, provenance attestations, and Helm charts\n`;

    return markdown;
  }

  public generate(): string {
    console.error(`Generating release notes for ${this.currentVersion} (from ${this.previousVersion})`);
    
    this.parseCommits();
    const notes = this.categorizeCommits();
    const markdown = this.formatMarkdown(notes);

    console.error(`Generated release notes with ${this.commits.length} commits`);
    return markdown;
  }
}

// Main execution
if (require.main === module) {
  try {
    const generator = new ReleaseNotesGenerator();
    const releaseNotes = generator.generate();
    console.log(releaseNotes);
  } catch (error) {
    console.error('Error generating release notes:', error);
    process.exit(1);
  }
}
