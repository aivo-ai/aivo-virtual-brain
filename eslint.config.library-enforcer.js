import aivoPlugin from "@aivo/eslint-plugin-aivo";

export default [
  {
    // Global ignores (applied to all configs)
    ignores: [
      // TypeScript files
      "**/*.ts",
      "**/*.tsx",
      "**/*.d.ts",
      // Build outputs and generated files
      "dist/**",
      "types/**",
      "**/dist/**",
      "**/types/**",
      // Dependencies
      "**/node_modules/**",
      // Tests
      "test/**",
      "tests/**",
      "**/*.test.{js,jsx,ts,tsx}",
      "**/*.spec.{js,jsx,ts,tsx}",
      // Common patterns
      "build/**",
      "coverage/**",
      // Python virtual environment
      ".venv/**",
      // Validation scripts that legitimately reference the terminology being checked
      "scripts/validate-s5-01.mjs",
    ],
  },
  {
    files: ["**/*.{js,mjs,cjs,jsx}"],
    plugins: {
      "@aivo/aivo": aivoPlugin,
    },
    rules: {
      "@aivo/aivo/no-live-class": "error", // eslint-disable-line @aivo/aivo/no-live-class
    },
  },
];
