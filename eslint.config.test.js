import aivoPlugin from "./libs/eslint-plugin-aivo/dist/index.js";

export default [
  {
    files: ["**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx"],
    plugins: {
      "@aivo/aivo": aivoPlugin,
    },
    rules: {
      "@aivo/aivo/no-live-class": "error",
    },
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "module",
      globals: {
        console: "readonly",
        process: "readonly",
      },
    },
  },
];
