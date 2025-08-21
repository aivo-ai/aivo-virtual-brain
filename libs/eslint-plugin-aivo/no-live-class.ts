/**
 * ESLint Rule: no-live-class
 *
 * Prevents usage of "live-class" terminology in code.
 * All references should use "library" instead.
 *
 * @fileoverview ESLint rule to enforce Library terminology over live-class
 * @author AIVO Team
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: 'Disallow "live-class" terminology - use "library" instead',
      category: "Best Practices",
      recommended: true,
    },
    fixable: "code",
    schema: [],
    messages: {
      noLiveClass:
        'Use "library" instead of "live-class" terminology. Found: {{identifier}}',
      noLiveClassPath:
        'File paths should not contain "live-class" - use "library" instead. Path: {{path}}',
      noLiveClassComment:
        'Comments should not reference "live-class" - use "library" instead.',
    },
  },

  create(context) {
    const sourceCode = context.getSourceCode();
    const filename = context.getFilename();

    // Check if filename contains live-class patterns
    const liveClassPatterns = /live[-_]?class|liveclass/gi;

    if (liveClassPatterns.test(filename)) {
      context.report({
        loc: { line: 1, column: 0 },
        messageId: "noLiveClassPath",
        data: { path: filename },
      });
    }

    return {
      // Check all identifiers (variables, functions, classes, etc.)
      Identifier(node: any) {
        if (liveClassPatterns.test(node.name)) {
          context.report({
            node,
            messageId: "noLiveClass",
            data: { identifier: node.name },
            fix(fixer) {
              const replacement = node.name
                .replace(/live[-_]?class/gi, "library")
                .replace(/liveclass/gi, "library");
              return fixer.replaceText(node, replacement);
            },
          });
        }
      },

      // Check string literals
      Literal(node: any) {
        if (
          typeof node.value === "string" &&
          liveClassPatterns.test(node.value)
        ) {
          context.report({
            node,
            messageId: "noLiveClass",
            data: { identifier: node.value },
            fix(fixer) {
              const originalText = sourceCode.getText(node);
              const replacement = originalText
                .replace(/live[-_]?class/gi, "library")
                .replace(/liveclass/gi, "library");
              return fixer.replaceText(node, replacement);
            },
          });
        }
      },

      // Check template literals
      TemplateLiteral(node: any) {
        node.quasis.forEach((quasi: any) => {
          if (liveClassPatterns.test(quasi.value.raw)) {
            context.report({
              node: quasi,
              messageId: "noLiveClass",
              data: { identifier: quasi.value.raw },
              fix(fixer) {
                const replacement = quasi.value.raw
                  .replace(/live[-_]?class/gi, "library")
                  .replace(/liveclass/gi, "library");
                return fixer.replaceText(quasi, `\`${replacement}\``);
              },
            });
          }
        });
      },

      // Check JSX attributes
      JSXAttribute(node: any) {
        if (
          node.name &&
          node.name.name &&
          liveClassPatterns.test(node.name.name)
        ) {
          context.report({
            node: node.name,
            messageId: "noLiveClass",
            data: { identifier: node.name.name },
            fix(fixer) {
              const replacement = node.name.name
                .replace(/live[-_]?class/gi, "library")
                .replace(/liveclass/gi, "library");
              return fixer.replaceText(node.name, replacement);
            },
          });
        }
      },

      // Check object property keys
      Property(node: any) {
        if (
          node.key.type === "Identifier" &&
          node.key.name &&
          liveClassPatterns.test(node.key.name)
        ) {
          context.report({
            node: node.key,
            messageId: "noLiveClass",
            data: { identifier: node.key.name },
            fix(fixer) {
              const replacement = node.key.name
                .replace(/live[-_]?class/gi, "library")
                .replace(/liveclass/gi, "library");
              return fixer.replaceText(node.key, replacement);
            },
          });
        }
      },

      // Check comments
      Program() {
        const comments = sourceCode.getAllComments();
        comments.forEach((comment: any) => {
          if (liveClassPatterns.test(comment.value)) {
            context.report({
              loc: comment.loc || { line: 1, column: 0 },
              messageId: "noLiveClassComment",
              fix(fixer) {
                const replacement = comment.value
                  .replace(/live[-_]?class/gi, "library")
                  .replace(/liveclass/gi, "library");
                const commentText =
                  comment.type === "Block"
                    ? `/*${replacement}*/`
                    : `//${replacement}`;
                return fixer.replaceText(comment, commentText);
              },
            });
          }
        });
      },
    };
  },
};

export = rule;
