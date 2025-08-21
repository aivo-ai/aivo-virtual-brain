# @aivo/eslint-plugin-aivo

ESLint plugin for AIVO Virtual Brain codebase standards and naming conventions.

## 🎯 Purpose

This ESLint plugin enforces consistent terminology and coding standards across the AIVO Virtual Brain codebase. It prevents the use of deprecated or incorrect terminology and ensures all code follows established naming conventions.

## 📋 Rules

### `no-live-class`

**Type:** Error  
**Fixable:** Yes  
**Category:** Best Practices

Prevents usage of "live-class" terminology in code. All references should use "library" instead.

#### ❌ Invalid

```javascript
// Variables
const liveClassComponent = "live-class-page";
const live_class_service = "endpoint";

// Functions
function liveClassHandler() {
  return getLiveClassData();
}

// Classes
class LiveClassService {
  getLiveClassSessions() {}
}

// Objects
const config = {
  liveClassEndpoint: "/api/live-class",
  endpoints: {
    liveClassSessions: "/sessions",
  },
};

// JSX
<LiveClassComponent liveClassProp="value" />;

// Comments
/* Handle live-class sessions */
// Process live-class data

// Template literals
const url = `/${liveClassType}/sessions`;

// Imports/Exports
import { LiveClassModule } from "./live-class";
export const liveClassUtils = {};
```

#### ✅ Valid

```javascript
// Variables
const libraryComponent = "library-page";
const library_service = "endpoint";

// Functions
function libraryHandler() {
  return getLibraryData();
}

// Classes
class LibraryService {
  getLibrarySessions() {}
}

// Objects
const config = {
  libraryEndpoint: "/api/library",
  endpoints: {
    librarySessions: "/sessions",
  },
};

// JSX
<LibraryComponent libraryProp="value" />;

// Comments
/* Handle library sessions */
// Process library data

// Template literals
const url = `/${libraryType}/sessions`;

// Imports/Exports
import { LibraryModule } from "./library";
export const libraryUtils = {};
```

#### Rule Configuration

```json
{
  "rules": {
    "@aivo/aivo/no-live-class": "error"
  }
}
```

## 🚀 Installation

### In a monorepo workspace:

```bash
# Install in the specific package
cd libs/eslint-plugin-aivo
pnpm install

# Build the plugin
pnpm run build
```

### Add to your ESLint configuration:

```javascript
// eslint.config.js
import aivoPlugin from "../../libs/eslint-plugin-aivo/dist/index.js";

export default [
  {
    plugins: {
      "@aivo/aivo": aivoPlugin,
    },
    rules: {
      "@aivo/aivo/no-live-class": "error",
    },
  },
];
```

### Or use the recommended configuration:

```javascript
import aivoPlugin from "@aivo/eslint-plugin-aivo";

export default [...aivoPlugin.configs.recommended];
```

## 🧪 Testing

```bash
# Run tests
pnpm test

# Run tests with coverage
pnpm test -- --coverage

# Run tests in watch mode
pnpm test -- --watch
```

## 🔧 Development

### Project Structure

```
libs/eslint-plugin-aivo/
├── index.ts              # Plugin entry point
├── no-live-class.ts      # No live-class rule implementation
├── no-live-class.test.ts # Rule tests
├── package.json          # Package configuration
├── tsconfig.json         # TypeScript configuration
├── jest.config.json      # Jest test configuration
└── README.md             # This file
```

### Adding New Rules

1. Create a new rule file (e.g., `new-rule.ts`)
2. Export the rule from `index.ts`
3. Add comprehensive tests
4. Update documentation

### Building

```bash
# Build the plugin
pnpm run build

# Watch mode for development
pnpm run build -- --watch
```

## 🚦 CI Integration

The plugin is automatically tested in CI via `.github/workflows/no-live-class.yml`:

- **Rule Testing:** Validates rule functionality with unit tests
- **Enforcement:** Scans entire codebase for violations
- **File/Directory Names:** Checks for live-class in paths
- **Content Scanning:** Searches file content for violations
- **Simulated Failure:** Tests that CI catches violations

### CI Failure Examples

The CI will fail if it finds:

```bash
# File names
live-class-component.ts
liveClassService.js
live_class_utils.py

# Directory names
src/live-class/
components/liveclass/
utils/live_class/

# Code content
const liveClassData = "live-class-info";
function getLiveClassSessions() {}
class LiveClassManager {}
```

## 📊 Coverage

The plugin maintains high test coverage:

- **Branches:** 80%+
- **Functions:** 80%+
- **Lines:** 80%+
- **Statements:** 80%+

## 🔄 Auto-fixing

The `no-live-class` rule supports automatic fixing:

```bash
# Fix violations automatically
npx eslint --fix src/

# Preview fixes without applying
npx eslint --fix-dry-run src/
```

## 📝 Configuration Examples

### Strict Configuration

```javascript
export default [
  {
    plugins: {
      "@aivo/aivo": aivoPlugin,
    },
    rules: {
      "@aivo/aivo/no-live-class": "error",
    },
  },
];
```

### Warning Only

```javascript
export default [
  {
    plugins: {
      "@aivo/aivo": aivoPlugin,
    },
    rules: {
      "@aivo/aivo/no-live-class": "warn",
    },
  },
];
```

### Disabled (Not Recommended)

```javascript
export default [
  {
    plugins: {
      "@aivo/aivo": aivoPlugin,
    },
    rules: {
      "@aivo/aivo/no-live-class": "off",
    },
  },
];
```

## 🤝 Contributing

1. Follow the existing code style
2. Add tests for new features
3. Ensure all tests pass
4. Update documentation
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 Related

- [ESLint Documentation](https://eslint.org/docs/developer-guide/)
- [Writing Custom Rules](https://eslint.org/docs/developer-guide/working-with-rules)
- [AIVO Coding Standards](../../docs/coding-standards.md)
