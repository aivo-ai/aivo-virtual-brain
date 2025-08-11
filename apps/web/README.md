# @aivo/web

React 19 + Vite 7 web application with TypeScript, Tailwind CSS, and comprehensive testing.

## 🚀 Features

- **React 19** with modern concurrent features
- **Vite 7** for fast development and optimized builds
- **TypeScript 5.6** with strict configuration
- **Tailwind CSS 3.4** for utility-first styling
- **i18next** for internationalization
- **PWA Support** with Vite PWA plugin
- **Route Manifest System** with type-safe navigation
- **CTA Guard** for interactive element validation
- **Comprehensive Testing** with Vitest, Playwright, and axe-core

## 📁 Project Structure

```
src/
├── main.tsx              # React 19 app entry point
├── App.tsx               # Main app with routing
├── index.css             # Tailwind CSS imports
├── types/routes.ts       # Route manifest system
├── utils/cta-guard.ts    # CTA validation utility
├── i18n/index.ts         # Internationalization setup
├── pages/                # Page components
└── tests/                # Test files
```

## 🛠️ Development

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Run tests
pnpm test

# Run accessibility tests
pnpm test:a11y

# Lint code
pnpm lint

# Type check
pnpm typecheck
```

## 🧪 Testing

- **Unit Tests**: Vitest + @testing-library/react
- **CTA Guard Tests**: Validates all interactive elements
- **Accessibility Tests**: Playwright + axe-core
- **Type Safety**: TypeScript strict mode

## 🎯 Route System

The app uses a type-safe route manifest system that prevents navigation to non-existent routes:

- All routes are defined in `src/types/routes.ts`
- CTA Guard validates all buttons and links
- Adding/removing routes automatically updates TypeScript types

## 🌐 Routes

- `/` - Home page
- `/health` - Health check endpoint
- `/_dev/mocks` - Development mocks (dev only)
