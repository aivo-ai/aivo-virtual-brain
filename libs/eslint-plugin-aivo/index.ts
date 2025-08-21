/**
 * AIVO ESLint Plugin
 *
 * Custom ESLint rules for AIVO Virtual Brain codebase.
 * Enforces coding standards and naming conventions.
 *
 * @fileoverview ESLint plugin for AIVO-specific rules
 * @author AIVO Team
 */

import noLiveClass from "./no-live-class";

const plugin = {
  meta: {
    name: "@aivo/eslint-plugin-aivo",
    version: "1.0.0",
  },
  rules: {
    "no-live-class": noLiveClass,
  },
  configs: {
    recommended: {
      plugins: ["@aivo/aivo"],
      rules: {
        "@aivo/aivo/no-live-class": "error",
      },
    },
    strict: {
      plugins: ["@aivo/aivo"],
      rules: {
        "@aivo/aivo/no-live-class": "error",
      },
    },
  },
};

export = plugin;
