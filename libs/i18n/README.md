# Internationalization (i18n) System

A comprehensive internationalization system for the Aivo Virtual Brains platform supporting 14 languages with RTL (Right-to-Left) support, accessibility features, and cultural adaptations.

## Features

- **14 Language Support**: English, Spanish, French, Arabic, Chinese (Simplified), Hindi, Portuguese, Igbo, Yoruba, Hausa, Efik, Swahili, Xhosa, and Kikuyu
- **RTL Support**: Full right-to-left layout support for Arabic
- **Font Stack Management**: Optimized font stacks for different language families
- **Locale Detection**: Automatic language detection based on browser preferences
- **Persistence**: User language preferences saved to localStorage
- **Number & Date Formatting**: Culture-aware formatting for numbers, currencies, dates, and times
- **Accessibility**: Screen reader announcements, high contrast support, reduced motion
- **React Integration**: Hooks and providers for seamless React integration

## Quick Start

### 1. Install Dependencies

```bash
pnpm add react-i18next i18next i18next-browser-languagedetector
```

### 2. Setup i18n

```typescript
import { RTLProvider, languages } from '@/libs/i18n';
import LanguageSwitcher from '@/libs/i18n/LanguageSwitcher';
import '@/libs/i18n/rtl.css';

function App() {
  return (
    <RTLProvider languages={languages}>
      <div className="app">
        <header>
          <LanguageSwitcher languages={languages} />
        </header>
        <main>
          {/* Your app content */}
        </main>
      </div>
    </RTLProvider>
  );
}
```

### 3. Use Translations

```typescript
import { useTranslation } from 'react-i18next';
import { useRTL } from '@/libs/i18n/RTLProvider';

function MyComponent() {
  const { t } = useTranslation();
  const { isRTL, direction } = useRTL();

  return (
    <div dir={direction}>
      <h1>{t('dashboard.welcome', { name: 'John' })}</h1>
      <p className={isRTL ? 'text-right' : 'text-left'}>
        {t('common.loading')}
      </p>
    </div>
  );
}
```

## Components

### RTLProvider

Provides RTL context and manages document direction, font stacks, and language persistence.

```typescript
<RTLProvider languages={languages}>
  {children}
</RTLProvider>
```

### LanguageSwitcher

A flexible language switcher component with multiple variants.

```typescript
// Dropdown variant (default)
<LanguageSwitcher languages={languages} />

// Inline buttons
<LanguageSwitcher
  languages={languages}
  variant="inline"
  showNativeName={true}
/>

// Custom styling
<LanguageSwitcher
  languages={languages}
  className="my-custom-class"
  showFlag={true}
/>
```

## Supported Languages

| Language             | ISO Code | RTL | Font Stack           | Currency |
| -------------------- | -------- | --- | -------------------- | -------- |
| English              | en       | No  | System UI            | USD      |
| Spanish              | es       | No  | System UI            | EUR      |
| French               | fr       | No  | System UI            | EUR      |
| Arabic               | ar       | Yes | Noto Sans Arabic     | SAR      |
| Chinese (Simplified) | zh-Hans  | No  | Noto Sans SC         | CNY      |
| Hindi                | hi       | No  | Noto Sans Devanagari | INR      |
| Portuguese           | pt       | No  | System UI            | BRL      |
| Igbo                 | ig       | No  | Noto Sans            | NGN      |
| Yoruba               | yo       | No  | Noto Sans            | NGN      |
| Hausa                | ha       | No  | Noto Sans            | NGN      |
| Efik                 | efi      | No  | Noto Sans            | NGN      |
| Swahili              | sw       | No  | Noto Sans            | KES      |
| Xhosa                | xh       | No  | Noto Sans            | ZAR      |
| Kikuyu               | ki       | No  | Noto Sans            | KES      |

## RTL (Right-to-Left) Support

### CSS Classes

Use direction-aware CSS classes for RTL-compatible layouts:

```css
/* Margins */
.ms-4  /* margin-inline-start: 1rem */
.me-4  /* margin-inline-end: 1rem */

/* Padding */
.ps-4  /* padding-inline-start: 1rem */
.pe-4  /* padding-inline-end: 1rem */

/* Text alignment */
.text-start  /* text-align: start */
.text-end    /* text-align: end */

/* Positioning */
.start-0  /* inset-inline-start: 0 */
.end-0    /* inset-inline-end: 0 */
```

### Font Stacks

Different font stacks are automatically applied based on language:

```css
.font-arabic   /* Arabic fonts: Noto Sans Arabic, Dubai, Tahoma */
.font-chinese  /* Chinese fonts: Noto Sans SC, PingFang SC */
.font-hindi    /* Hindi fonts: Noto Sans Devanagari, Mangal */
.font-african  /* African languages: Noto Sans, DejaVu Sans */
```

## Formatting Utilities

### Numbers

```typescript
import { formatNumber, formatCurrency } from "@/libs/i18n";

formatNumber(1234.56, "en"); // "1,234.56"
formatNumber(1234.56, "fr"); // "1 234,56"
formatCurrency(99.99, "en"); // "$99.99"
formatCurrency(99.99, "fr"); // "99,99 €"
```

### Dates and Times

```typescript
import {
  formatDate,
  formatTime,
  formatDateTime,
  getRelativeTime,
} from "@/libs/i18n";

const date = new Date();

formatDate(date, "en"); // "August 17, 2025"
formatTime(date, "en"); // "10:30 AM"
formatDateTime(date, "en"); // "Aug 17, 2025, 10:30 AM"
getRelativeTime(date, "en"); // "2 hours ago"
```

## Translation Keys

### Common UI Elements

```json
{
  "common": {
    "loading": "Loading...",
    "error": "Error",
    "success": "Success",
    "save": "Save",
    "cancel": "Cancel"
  }
}
```

### Navigation

```json
{
  "navigation": {
    "dashboard": "Dashboard",
    "learners": "Learners",
    "analytics": "Analytics",
    "settings": "Settings"
  }
}
```

### Authentication

```json
{
  "auth": {
    "login": "Sign In",
    "register": "Sign Up",
    "email": "Email",
    "password": "Password"
  }
}
```

### Validation

```json
{
  "validation": {
    "required": "This field is required",
    "email": "Please enter a valid email",
    "minLength": "Must be at least {{min}} characters"
  }
}
```

## Accessibility Features

### Screen Reader Support

- Language changes are announced via `aria-live` regions
- Proper ARIA labels and roles on interactive elements
- Semantic HTML structure maintained in all languages

### High Contrast Mode

```css
@media (prefers-contrast: high) {
  /* Enhanced borders and contrast */
}
```

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  /* Disabled animations and transitions */
}
```

### Keyboard Navigation

- Full keyboard navigation support
- Focus management in dropdowns and modals
- Proper tab order in RTL layouts

## Testing

Run the comprehensive test suite:

```bash
pnpm test libs/i18n/i18n.spec.ts
```

Tests cover:

- Language switching functionality
- RTL layout behavior
- Formatting utilities
- Accessibility features
- Keyboard navigation
- Performance scenarios

## Configuration

### Adding New Languages

1. Add translation file to `resources/[iso].json`
2. Update `locales.json` with language configuration
3. Add font stack if needed
4. Update documentation

### Customizing Locales

Edit `locales.json` to modify:

- Currency settings
- Date/time formats
- Number formatting
- Font preferences
- RTL configuration

## Performance Considerations

- Translations are bundled and tree-shaken
- Lazy loading support for large translation files
- Efficient font loading strategies
- Memory leak prevention in event listeners

## Browser Support

- Modern browsers with CSS Logical Properties support
- Fallbacks for older browsers via PostCSS plugins
- Progressive enhancement for advanced features

## Migration Guide

### From Previous i18n Systems

1. Map existing translation keys to new structure
2. Update component imports
3. Replace direction-specific CSS with logical properties
4. Test RTL layouts thoroughly

### Adding RTL Support to Existing Components

1. Replace directional CSS classes with logical equivalents
2. Test component behavior in RTL mode
3. Ensure proper text alignment and icon positioning
4. Validate accessibility in both directions

## Contributing

When adding new translations:

1. Use native speakers for accuracy
2. Consider cultural context, not just language
3. Test with real users from target regions
4. Maintain consistency in tone and terminology
5. Update tests for new languages

## Troubleshooting

### Common Issues

**Fonts not loading properly:**

- Check font stack configuration in `locales.json`
- Ensure web fonts are properly loaded
- Verify fallback fonts are available

**RTL layout issues:**

- Use logical CSS properties instead of physical ones
- Test with Arabic language selected
- Check component positioning and alignment

**Performance problems:**

- Monitor bundle size with translation files
- Consider lazy loading for large translations
- Optimize font loading strategies

**Accessibility failures:**

- Test with screen readers in multiple languages
- Verify keyboard navigation works in RTL
- Check contrast ratios for all language fonts
