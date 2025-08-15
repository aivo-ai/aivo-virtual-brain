/**
 * Tailwind CSS Extension for Grade Band Design Tokens
 * 
 * This file exports Tailwind configuration extensions based on the design tokens.
 * It dynamically generates CSS custom properties and utilities for each grade band.
 */

const { designTokens } = require('./gradeBands');

/**
 * Generate CSS custom properties for a grade band
 */
function generateCSSProperties(gradeBand) {
  const tokens = designTokens.gradeBands[gradeBand];
  const properties = {};

  // Spacing properties
  Object.entries(tokens.spacing).forEach(([key, value]) => {
    properties[`--spacing-${key}`] = value;
  });

  // Font size properties
  Object.entries(tokens.fontSize).forEach(([key, [size, config]]) => {
    properties[`--font-size-${key}`] = size;
    properties[`--line-height-${key}`] = config.lineHeight;
    if (config.letterSpacing) {
      properties[`--letter-spacing-${key}`] = config.letterSpacing;
    }
  });

  // Icon size properties
  Object.entries(tokens.iconSize).forEach(([key, value]) => {
    properties[`--icon-size-${key}`] = value;
  });

  // Border radius properties
  Object.entries(tokens.borderRadius).forEach(([key, value]) => {
    properties[`--border-radius-${key}`] = value;
  });

  // Motion properties
  Object.entries(tokens.motion.duration).forEach(([key, value]) => {
    properties[`--duration-${key}`] = value;
  });

  Object.entries(tokens.motion.easing).forEach(([key, value]) => {
    properties[`--easing-${key}`] = value;
  });

  Object.entries(tokens.motion.scale).forEach(([key, value]) => {
    properties[`--scale-${key}`] = value;
  });

  // Color properties
  Object.entries(tokens.colors).forEach(([colorName, colorObj]) => {
    Object.entries(colorObj).forEach(([shade, value]) => {
      properties[`--color-${colorName}-${shade}`] = value;
    });
  });

  return properties;
}

/**
 * Tailwind extension configuration
 */
module.exports = {
  theme: {
    extend: {
      // Font families
      fontFamily: {
        'display': designTokens.fonts.display,
        'body': designTokens.fonts.body,
        'mono': designTokens.fonts.mono,
        'dyslexic': designTokens.fonts.dyslexic,
      },

      // Grade band spacing (using CSS custom properties)
      spacing: {
        'gb-xs': 'var(--spacing-xs, 0.25rem)',
        'gb-sm': 'var(--spacing-sm, 0.5rem)',
        'gb-md': 'var(--spacing-md, 0.75rem)',
        'gb-lg': 'var(--spacing-lg, 1rem)',
        'gb-xl': 'var(--spacing-xl, 1.25rem)',
        'gb-2xl': 'var(--spacing-2xl, 1.5rem)',
        'gb-3xl': 'var(--spacing-3xl, 2rem)',
        'gb-4xl': 'var(--spacing-4xl, 2.5rem)',
      },

      // Grade band font sizes
      fontSize: {
        'gb-xs': ['var(--font-size-xs, 0.75rem)', {
          lineHeight: 'var(--line-height-xs, 1.4)',
          letterSpacing: 'var(--letter-spacing-xs, 0)',
        }],
        'gb-sm': ['var(--font-size-sm, 0.875rem)', {
          lineHeight: 'var(--line-height-sm, 1.4)',
          letterSpacing: 'var(--letter-spacing-sm, 0)',
        }],
        'gb-base': ['var(--font-size-base, 1rem)', {
          lineHeight: 'var(--line-height-base, 1.5)',
          letterSpacing: 'var(--letter-spacing-base, 0)',
        }],
        'gb-lg': ['var(--font-size-lg, 1.125rem)', {
          lineHeight: 'var(--line-height-lg, 1.4)',
          letterSpacing: 'var(--letter-spacing-lg, 0)',
        }],
        'gb-xl': ['var(--font-size-xl, 1.25rem)', {
          lineHeight: 'var(--line-height-xl, 1.4)',
          letterSpacing: 'var(--letter-spacing-xl, 0)',
        }],
        'gb-2xl': ['var(--font-size-2xl, 1.5rem)', {
          lineHeight: 'var(--line-height-2xl, 1.3)',
          letterSpacing: 'var(--letter-spacing-2xl, 0)',
        }],
        'gb-3xl': ['var(--font-size-3xl, 1.875rem)', {
          lineHeight: 'var(--line-height-3xl, 1.3)',
          letterSpacing: 'var(--letter-spacing-3xl, 0)',
        }],
        'gb-4xl': ['var(--font-size-4xl, 2.25rem)', {
          lineHeight: 'var(--line-height-4xl, 1.2)',
          letterSpacing: 'var(--letter-spacing-4xl, 0)',
        }],
        'gb-5xl': ['var(--font-size-5xl, 3rem)', {
          lineHeight: 'var(--line-height-5xl, 1.1)',
          letterSpacing: 'var(--letter-spacing-5xl, 0)',
        }],
      },

      // Grade band border radius
      borderRadius: {
        'gb-none': 'var(--border-radius-none, 0)',
        'gb-sm': 'var(--border-radius-sm, 0.25rem)',
        'gb-md': 'var(--border-radius-md, 0.375rem)',
        'gb-lg': 'var(--border-radius-lg, 0.5rem)',
        'gb-xl': 'var(--border-radius-xl, 0.75rem)',
        'gb-2xl': 'var(--border-radius-2xl, 1rem)',
        'gb-full': 'var(--border-radius-full, 9999px)',
      },

      // Animation durations
      transitionDuration: {
        'gb-fast': 'var(--duration-fast, 150ms)',
        'gb-normal': 'var(--duration-normal, 200ms)',
        'gb-slow': 'var(--duration-slow, 300ms)',
      },

      // Animation timing functions
      transitionTimingFunction: {
        'gb-ease': 'var(--easing-ease, ease)',
        'gb-ease-in': 'var(--easing-ease-in, ease-in)',
        'gb-ease-out': 'var(--easing-ease-out, ease-out)',
        'gb-ease-in-out': 'var(--easing-ease-in-out, ease-in-out)',
      },

      // Scale transforms
      scale: {
        'gb-sm': 'var(--scale-sm, 1.02)',
        'gb-md': 'var(--scale-md, 1.04)',
        'gb-lg': 'var(--scale-lg, 1.08)',
      },

      // Grade band colors (using CSS custom properties)
      colors: {
        'gb-primary': {
          50: 'var(--color-primary-50)',
          100: 'var(--color-primary-100)',
          200: 'var(--color-primary-200)',
          300: 'var(--color-primary-300)',
          400: 'var(--color-primary-400)',
          500: 'var(--color-primary-500)',
          600: 'var(--color-primary-600)',
          700: 'var(--color-primary-700)',
          800: 'var(--color-primary-800)',
          900: 'var(--color-primary-900)',
        },
        'gb-secondary': {
          50: 'var(--color-secondary-50)',
          100: 'var(--color-secondary-100)',
          200: 'var(--color-secondary-200)',
          300: 'var(--color-secondary-300)',
          400: 'var(--color-secondary-400)',
          500: 'var(--color-secondary-500)',
          600: 'var(--color-secondary-600)',
          700: 'var(--color-secondary-700)',
          800: 'var(--color-secondary-800)',
          900: 'var(--color-secondary-900)',
        },
        'gb-accent': {
          50: 'var(--color-accent-50)',
          100: 'var(--color-accent-100)',
          200: 'var(--color-accent-200)',
          300: 'var(--color-accent-300)',
          400: 'var(--color-accent-400)',
          500: 'var(--color-accent-500)',
          600: 'var(--color-accent-600)',
          700: 'var(--color-accent-700)',
          800: 'var(--color-accent-800)',
          900: 'var(--color-accent-900)',
        },
        'gb-success': {
          50: 'var(--color-success-50)',
          100: 'var(--color-success-100)',
          200: 'var(--color-success-200)',
          300: 'var(--color-success-300)',
          400: 'var(--color-success-400)',
          500: 'var(--color-success-500)',
          600: 'var(--color-success-600)',
          700: 'var(--color-success-700)',
          800: 'var(--color-success-800)',
          900: 'var(--color-success-900)',
        },
        'gb-warning': {
          50: 'var(--color-warning-50)',
          100: 'var(--color-warning-100)',
          200: 'var(--color-warning-200)',
          300: 'var(--color-warning-300)',
          400: 'var(--color-warning-400)',
          500: 'var(--color-warning-500)',
          600: 'var(--color-warning-600)',
          700: 'var(--color-warning-700)',
          800: 'var(--color-warning-800)',
          900: 'var(--color-warning-900)',
        },
        'gb-error': {
          50: 'var(--color-error-50)',
          100: 'var(--color-error-100)',
          200: 'var(--color-error-200)',
          300: 'var(--color-error-300)',
          400: 'var(--color-error-400)',
          500: 'var(--color-error-500)',
          600: 'var(--color-error-600)',
          700: 'var(--color-error-700)',
          800: 'var(--color-error-800)',
          900: 'var(--color-error-900)',
        },
        'gb-neutral': {
          50: 'var(--color-neutral-50)',
          100: 'var(--color-neutral-100)',
          200: 'var(--color-neutral-200)',
          300: 'var(--color-neutral-300)',
          400: 'var(--color-neutral-400)',
          500: 'var(--color-neutral-500)',
          600: 'var(--color-neutral-600)',
          700: 'var(--color-neutral-700)',
          800: 'var(--color-neutral-800)',
          900: 'var(--color-neutral-900)',
        },
      },

      // Icon sizes
      width: {
        'icon-xs': 'var(--icon-size-xs, 0.75rem)',
        'icon-sm': 'var(--icon-size-sm, 0.875rem)',
        'icon-md': 'var(--icon-size-md, 1rem)',
        'icon-lg': 'var(--icon-size-lg, 1.25rem)',
        'icon-xl': 'var(--icon-size-xl, 1.5rem)',
        'icon-2xl': 'var(--icon-size-2xl, 2rem)',
      },
      height: {
        'icon-xs': 'var(--icon-size-xs, 0.75rem)',
        'icon-sm': 'var(--icon-size-sm, 0.875rem)',
        'icon-md': 'var(--icon-size-md, 1rem)',
        'icon-lg': 'var(--icon-size-lg, 1.25rem)',
        'icon-xl': 'var(--icon-size-xl, 1.5rem)',
        'icon-2xl': 'var(--icon-size-2xl, 2rem)',
      },
    },
  },

  // CSS utilities and components
  addBase: {
    ':root': generateCSSProperties('9-12'), // Default to high school
    '[data-grade-band="k-2"]': generateCSSProperties('k-2'),
    '[data-grade-band="3-5"]': generateCSSProperties('3-5'),
    '[data-grade-band="6-8"]': generateCSSProperties('6-8'),
    '[data-grade-band="9-12"]': generateCSSProperties('9-12'),
    
    // Reduced motion support
    '@media (prefers-reduced-motion: reduce)': {
      ':root': {
        '--duration-fast': '0ms',
        '--duration-normal': '0ms',
        '--duration-slow': '0ms',
        '--scale-sm': '1',
        '--scale-md': '1',
        '--scale-lg': '1',
      },
    },

    // Focus ring utilities
    '.focus-ring': {
      '@apply outline-2 outline-offset-2 outline-gb-primary-600': {},
    },
    
    // Dyslexic font utility
    '.font-dyslexic': {
      'font-family': designTokens.fonts.dyslexic.join(', '),
    },
  },

  // Utility classes
  addUtilities: {
    '.grade-band-spacing': {
      '--spacing-xs': 'var(--spacing-xs)',
      '--spacing-sm': 'var(--spacing-sm)',
      '--spacing-md': 'var(--spacing-md)',
      '--spacing-lg': 'var(--spacing-lg)',
      '--spacing-xl': 'var(--spacing-xl)',
      '--spacing-2xl': 'var(--spacing-2xl)',
      '--spacing-3xl': 'var(--spacing-3xl)',
      '--spacing-4xl': 'var(--spacing-4xl)',
    },
  },

  // Grade band CSS property generators
  generateCSSProperties,
  designTokens,
};
