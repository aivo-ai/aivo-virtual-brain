import type {
  DesignTokens,
  GradeBandTokens,
  ColorToken,
  FontFamilyTokens,
} from "./index";

// Base color palette - WCAG AA compliant
const colors = {
  // Primary - Education Blue
  primary: {
    50: "#eff6ff",
    100: "#dbeafe",
    200: "#bfdbfe",
    300: "#93c5fd",
    400: "#60a5fa",
    500: "#3b82f6",
    600: "#2563eb",
    700: "#1d4ed8",
    800: "#1e40af",
    900: "#1e3a8a",
    950: "#172554",
  } as ColorToken,

  // Secondary - Warm Gray
  secondary: {
    50: "#fafaf9",
    100: "#f5f5f4",
    200: "#e7e5e4",
    300: "#d6d3d1",
    400: "#a8a29e",
    500: "#78716c",
    600: "#57534e",
    700: "#44403c",
    800: "#292524",
    900: "#1c1917",
    950: "#0c0a09",
  } as ColorToken,

  // Success - Green
  success: {
    50: "#f0fdf4",
    100: "#dcfce7",
    200: "#bbf7d0",
    300: "#86efac",
    400: "#4ade80",
    500: "#22c55e",
    600: "#16a34a",
    700: "#15803d",
    800: "#166534",
    900: "#14532d",
    950: "#052e16",
  } as ColorToken,

  // Warning - Amber
  warning: {
    50: "#fffbeb",
    100: "#fef3c7",
    200: "#fde68a",
    300: "#fcd34d",
    400: "#fbbf24",
    500: "#f59e0b",
    600: "#d97706",
    700: "#b45309",
    800: "#92400e",
    900: "#78350f",
    950: "#451a03",
  } as ColorToken,

  // Error - Red
  error: {
    50: "#fef2f2",
    100: "#fee2e2",
    200: "#fecaca",
    300: "#fca5a5",
    400: "#f87171",
    500: "#ef4444",
    600: "#dc2626",
    700: "#b91c1c",
    800: "#991b1b",
    900: "#7f1d1d",
    950: "#450a0a",
  } as ColorToken,

  // Neutral - True Gray
  neutral: {
    50: "#fafafa",
    100: "#f5f5f5",
    200: "#e5e5e5",
    300: "#d4d4d4",
    400: "#a3a3a3",
    500: "#737373",
    600: "#525252",
    700: "#404040",
    800: "#262626",
    900: "#171717",
    950: "#0a0a0a",
  } as ColorToken,
};

// Font families with dyslexia-friendly options
const fonts: FontFamilyTokens = {
  display: [
    "Inter",
    "system-ui",
    "-apple-system",
    "BlinkMacSystemFont",
    '"Segoe UI"',
    "Roboto",
    '"Helvetica Neue"',
    "Arial",
    "sans-serif",
  ],
  body: [
    "Inter",
    "system-ui",
    "-apple-system",
    "BlinkMacSystemFont",
    '"Segoe UI"',
    "Roboto",
    '"Helvetica Neue"',
    "Arial",
    "sans-serif",
  ],
  mono: [
    '"JetBrains Mono"',
    '"Fira Code"',
    "ui-monospace",
    "SFMono-Regular",
    '"SF Mono"',
    "Consolas",
    '"Liberation Mono"',
    "Menlo",
    "monospace",
  ],
  dyslexic: [
    "OpenDyslexic",
    '"Noto Sans"',
    "system-ui",
    "-apple-system",
    "BlinkMacSystemFont",
    '"Segoe UI"',
    "Roboto",
    '"Helvetica Neue"',
    "Arial",
    "sans-serif",
  ],
};

// K-2 Grade Band - Larger, more playful
const k2Tokens: GradeBandTokens = {
  spacing: {
    xs: "0.25rem", // 4px
    sm: "0.5rem", // 8px
    md: "0.75rem", // 12px
    lg: "1rem", // 16px
    xl: "1.5rem", // 24px
    "2xl": "2rem", // 32px
    "3xl": "2.5rem", // 40px
    "4xl": "3rem", // 48px
  },
  fontSize: {
    xs: ["0.875rem", { lineHeight: "1.6", letterSpacing: "0.025em" }],
    sm: ["1rem", { lineHeight: "1.6", letterSpacing: "0.025em" }],
    base: ["1.125rem", { lineHeight: "1.6", letterSpacing: "0.025em" }],
    lg: ["1.25rem", { lineHeight: "1.6", letterSpacing: "0.025em" }],
    xl: ["1.5rem", { lineHeight: "1.5", letterSpacing: "0.025em" }],
    "2xl": ["1.875rem", { lineHeight: "1.4", letterSpacing: "0.025em" }],
    "3xl": ["2.25rem", { lineHeight: "1.3", letterSpacing: "0.025em" }],
    "4xl": ["3rem", { lineHeight: "1.2", letterSpacing: "0.025em" }],
    "5xl": ["3.75rem", { lineHeight: "1.1", letterSpacing: "0.025em" }],
  },
  iconSize: {
    xs: "1rem", // 16px
    sm: "1.25rem", // 20px
    md: "1.5rem", // 24px
    lg: "2rem", // 32px
    xl: "2.5rem", // 40px
    "2xl": "3rem", // 48px
  },
  borderRadius: {
    none: "0",
    sm: "0.375rem", // 6px
    md: "0.5rem", // 8px
    lg: "0.75rem", // 12px
    xl: "1rem", // 16px
    "2xl": "1.25rem", // 20px
    full: "9999px",
  },
  motion: {
    duration: {
      fast: "150ms",
      normal: "300ms",
      slow: "500ms",
    },
    easing: {
      ease: "ease",
      "ease-in": "ease-in",
      "ease-out": "ease-out",
      "ease-in-out": "ease-in-out",
    },
    scale: {
      sm: "1.02",
      md: "1.05",
      lg: "1.1",
    },
  },
  colors: {
    primary: colors.primary,
    secondary: colors.secondary,
    accent: colors.warning, // Bright accent for engagement
    neutral: colors.neutral,
    success: colors.success,
    warning: colors.warning,
    error: colors.error,
  },
};

// 3-5 Grade Band - Balanced approach
const grades35Tokens: GradeBandTokens = {
  spacing: {
    xs: "0.25rem", // 4px
    sm: "0.5rem", // 8px
    md: "0.75rem", // 12px
    lg: "1rem", // 16px
    xl: "1.25rem", // 20px
    "2xl": "1.5rem", // 24px
    "3xl": "2rem", // 32px
    "4xl": "2.5rem", // 40px
  },
  fontSize: {
    xs: ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.025em" }],
    sm: ["0.875rem", { lineHeight: "1.5", letterSpacing: "0.025em" }],
    base: ["1rem", { lineHeight: "1.5", letterSpacing: "0.025em" }],
    lg: ["1.125rem", { lineHeight: "1.5", letterSpacing: "0.025em" }],
    xl: ["1.25rem", { lineHeight: "1.4", letterSpacing: "0.025em" }],
    "2xl": ["1.5rem", { lineHeight: "1.4", letterSpacing: "0.025em" }],
    "3xl": ["1.875rem", { lineHeight: "1.3", letterSpacing: "0.025em" }],
    "4xl": ["2.25rem", { lineHeight: "1.2", letterSpacing: "0.025em" }],
    "5xl": ["3rem", { lineHeight: "1.1", letterSpacing: "0.025em" }],
  },
  iconSize: {
    xs: "0.875rem", // 14px
    sm: "1rem", // 16px
    md: "1.25rem", // 20px
    lg: "1.5rem", // 24px
    xl: "2rem", // 32px
    "2xl": "2.5rem", // 40px
  },
  borderRadius: {
    none: "0",
    sm: "0.25rem", // 4px
    md: "0.375rem", // 6px
    lg: "0.5rem", // 8px
    xl: "0.75rem", // 12px
    "2xl": "1rem", // 16px
    full: "9999px",
  },
  motion: {
    duration: {
      fast: "150ms",
      normal: "250ms",
      slow: "400ms",
    },
    easing: {
      ease: "ease",
      "ease-in": "ease-in",
      "ease-out": "ease-out",
      "ease-in-out": "ease-in-out",
    },
    scale: {
      sm: "1.02",
      md: "1.04",
      lg: "1.08",
    },
  },
  colors: {
    primary: colors.primary,
    secondary: colors.secondary,
    accent: colors.success, // Green accent for growth
    neutral: colors.neutral,
    success: colors.success,
    warning: colors.warning,
    error: colors.error,
  },
};

// 6-8 Grade Band - More sophisticated
const grades68Tokens: GradeBandTokens = {
  spacing: {
    xs: "0.25rem", // 4px
    sm: "0.5rem", // 8px
    md: "0.75rem", // 12px
    lg: "1rem", // 16px
    xl: "1.25rem", // 20px
    "2xl": "1.5rem", // 24px
    "3xl": "2rem", // 32px
    "4xl": "2.5rem", // 40px
  },
  fontSize: {
    xs: ["0.75rem", { lineHeight: "1.4", letterSpacing: "0.01em" }],
    sm: ["0.875rem", { lineHeight: "1.4", letterSpacing: "0.01em" }],
    base: ["1rem", { lineHeight: "1.5", letterSpacing: "0.01em" }],
    lg: ["1.125rem", { lineHeight: "1.4", letterSpacing: "0.01em" }],
    xl: ["1.25rem", { lineHeight: "1.4", letterSpacing: "0.01em" }],
    "2xl": ["1.5rem", { lineHeight: "1.3", letterSpacing: "0.01em" }],
    "3xl": ["1.875rem", { lineHeight: "1.3", letterSpacing: "0.01em" }],
    "4xl": ["2.25rem", { lineHeight: "1.2", letterSpacing: "0.01em" }],
    "5xl": ["3rem", { lineHeight: "1.1", letterSpacing: "0.01em" }],
  },
  iconSize: {
    xs: "0.75rem", // 12px
    sm: "0.875rem", // 14px
    md: "1rem", // 16px
    lg: "1.25rem", // 20px
    xl: "1.5rem", // 24px
    "2xl": "2rem", // 32px
  },
  borderRadius: {
    none: "0",
    sm: "0.25rem", // 4px
    md: "0.375rem", // 6px
    lg: "0.5rem", // 8px
    xl: "0.75rem", // 12px
    "2xl": "1rem", // 16px
    full: "9999px",
  },
  motion: {
    duration: {
      fast: "150ms",
      normal: "200ms",
      slow: "300ms",
    },
    easing: {
      ease: "ease",
      "ease-in": "ease-in",
      "ease-out": "ease-out",
      "ease-in-out": "ease-in-out",
    },
    scale: {
      sm: "1.01",
      md: "1.03",
      lg: "1.05",
    },
  },
  colors: {
    primary: colors.primary,
    secondary: colors.secondary,
    accent: {
      ...colors.primary,
      500: "#6366f1", // Indigo accent for sophistication
      600: "#4f46e5",
      700: "#4338ca",
    },
    neutral: colors.neutral,
    success: colors.success,
    warning: colors.warning,
    error: colors.error,
  },
};

// 9-12 Grade Band - Professional, refined
const grades912Tokens: GradeBandTokens = {
  spacing: {
    xs: "0.25rem", // 4px
    sm: "0.5rem", // 8px
    md: "0.75rem", // 12px
    lg: "1rem", // 16px
    xl: "1.25rem", // 20px
    "2xl": "1.5rem", // 24px
    "3xl": "2rem", // 32px
    "4xl": "2.5rem", // 40px
  },
  fontSize: {
    xs: ["0.75rem", { lineHeight: "1.4" }],
    sm: ["0.875rem", { lineHeight: "1.4" }],
    base: ["1rem", { lineHeight: "1.5" }],
    lg: ["1.125rem", { lineHeight: "1.4" }],
    xl: ["1.25rem", { lineHeight: "1.4" }],
    "2xl": ["1.5rem", { lineHeight: "1.3" }],
    "3xl": ["1.875rem", { lineHeight: "1.3" }],
    "4xl": ["2.25rem", { lineHeight: "1.2" }],
    "5xl": ["3rem", { lineHeight: "1.1" }],
  },
  iconSize: {
    xs: "0.75rem", // 12px
    sm: "0.875rem", // 14px
    md: "1rem", // 16px
    lg: "1.25rem", // 20px
    xl: "1.5rem", // 24px
    "2xl": "2rem", // 32px
  },
  borderRadius: {
    none: "0",
    sm: "0.125rem", // 2px
    md: "0.25rem", // 4px
    lg: "0.375rem", // 6px
    xl: "0.5rem", // 8px
    "2xl": "0.75rem", // 12px
    full: "9999px",
  },
  motion: {
    duration: {
      fast: "100ms",
      normal: "150ms",
      slow: "250ms",
    },
    easing: {
      ease: "ease",
      "ease-in": "ease-in",
      "ease-out": "ease-out",
      "ease-in-out": "ease-in-out",
    },
    scale: {
      sm: "1.01",
      md: "1.02",
      lg: "1.04",
    },
  },
  colors: {
    primary: colors.primary,
    secondary: colors.secondary,
    accent: {
      ...colors.secondary,
      500: "#6b7280", // Neutral accent for professional look
      600: "#4b5563",
      700: "#374151",
    },
    neutral: colors.neutral,
    success: colors.success,
    warning: colors.warning,
    error: colors.error,
  },
};

// Complete design tokens export
export const designTokens: DesignTokens = {
  fonts,
  gradeBands: {
    "k-2": k2Tokens,
    "3-5": grades35Tokens,
    "6-8": grades68Tokens,
    "9-12": grades912Tokens,
  },
  accessibility: {
    contrast: {
      normal: 4.5, // WCAG AA
      large: 3.0, // WCAG AA Large Text
      enhanced: 7.0, // WCAG AAA
    },
    focusRing: {
      width: "2px",
      offset: "2px",
      color: "#2563eb", // primary-600
    },
  },
};

export default designTokens;
