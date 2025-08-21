/**
 * Unit tests for no-live-class ESLint rule
 */

const { RuleTester } = require("eslint");
const rule = require("./dist/no-live-class.js");

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },
});

// Run the tests
try {
  ruleTester.run("no-live-class", rule, {
    valid: [
      'const libraryComponent = "library-page";',
      'function libraryHandler() { return "library-service"; }',
      "class LibraryService { getLibraryData() {} }",
      'const config = { libraryEndpoint: "/api/library" };',
      'const path = "/library/sessions";',
      'import { LibraryModule } from "./library";',
      '<LibraryComponent libraryProp="value" />',
    ],
    invalid: [
      {
        code: 'const liveClassComponent = "live-class-page";',
        errors: [{ messageId: "noLiveClass" }],
        output: 'const libraryComponent = "live-class-page";',
      },
      {
        code: 'function liveClassHandler() { return "live-class-service"; }',
        errors: 1,
        output: 'function libraryHandler() { return "live-class-service"; }',
      },
      {
        code: 'const config = { liveClassEndpoint: "/api/live-class" };',
        errors: 2,
        output: 'const config = { libraryEndpoint: "/api/library" };',
      },
      {
        code: "const url = `/${liveClassType}/sessions`;",
        errors: 1,
        output: "const url = `/${libraryType}/sessions`;",
      },
      {
        code: 'const liveClassData = "live-class-info";',
        errors: 1,
        output: 'const libraryData = "live-class-info";',
      },
      {
        code: 'const live_class_service = "live_class_endpoint";',
        errors: 1,
        output: 'const library_service = "live_class_endpoint";',
      },
      {
        code: 'import { LiveClassModule } from "./live-class";',
        errors: 2,
        output: 'import { libraryModule } from "./library";',
      },
      {
        code: 'const LiveClass = "LIVE-CLASS";',
        errors: [{ messageId: "noLiveClass" }],
        output: 'const library = "LIVE-CLASS";',
      },
      // Invalid: JSX Component with live-class
      {
        code: '<LiveClassComponent liveClassProp="value" />',
        errors: [{ messageId: "noLiveClass" }],
        output: '<LiveClassComponent libraryProp="value" />',
      },
    ],
  });

  console.log("✅ All ESLint rule tests passed!");
  process.exit(0);
} catch (error) {
  console.error("❌ ESLint rule tests failed:", error.message);
  process.exit(1);
}
