/**
 * Design Tokens - Grade Band Theming System
 * Provides accessible, grade-appropriate theming for K-2, 3-5, 6-8, 9-12
 */

export type GradeBand = "k-2" | "3-5" | "6-8" | "9-12";

export type ColorToken = {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
  950?: string;
};

export type SpacingScale = {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  "2xl": string;
  "3xl": string;
  "4xl": string;
};

export type FontSizeScale = {
  xs: [string, { lineHeight: string; letterSpacing?: string }];
  sm: [string, { lineHeight: string; letterSpacing?: string }];
  base: [string, { lineHeight: string; letterSpacing?: string }];
  lg: [string, { lineHeight: string; letterSpacing?: string }];
  xl: [string, { lineHeight: string; letterSpacing?: string }];
  "2xl": [string, { lineHeight: string; letterSpacing?: string }];
  "3xl": [string, { lineHeight: string; letterSpacing?: string }];
  "4xl": [string, { lineHeight: string; letterSpacing?: string }];
  "5xl": [string, { lineHeight: string; letterSpacing?: string }];
};

export type IconSizeScale = {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  "2xl": string;
};

export type BorderRadiusScale = {
  none: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  "2xl": string;
  full: string;
};

export type MotionTokens = {
  duration: {
    fast: string;
    normal: string;
    slow: string;
  };
  easing: {
    ease: string;
    "ease-in": string;
    "ease-out": string;
    "ease-in-out": string;
  };
  scale: {
    sm: string;
    md: string;
    lg: string;
  };
  disabled?: boolean; // For reduced motion preference
};

export type FontFamilyTokens = {
  display: string[];
  body: string[];
  mono: string[];
  dyslexic: string[];
};

export type GradeBandTokens = {
  spacing: SpacingScale;
  fontSize: FontSizeScale;
  iconSize: IconSizeScale;
  borderRadius: BorderRadiusScale;
  motion: MotionTokens;
  colors: {
    primary: ColorToken;
    secondary: ColorToken;
    accent: ColorToken;
    neutral: ColorToken;
    success: ColorToken;
    warning: ColorToken;
    error: ColorToken;
  };
};

export type DesignTokens = {
  fonts: FontFamilyTokens;
  gradeBands: Record<GradeBand, GradeBandTokens>;
  accessibility: {
    contrast: {
      normal: number; // 4.5:1
      large: number; // 3:1
      enhanced: number; // 7:1
    };
    focusRing: {
      width: string;
      offset: string;
      color: string;
    };
  };
};

// Utility functions
export function getGradeBandFromGrade(grade: number): GradeBand {
  if (grade <= 2) return "k-2";
  if (grade <= 5) return "3-5";
  if (grade <= 8) return "6-8";
  return "9-12";
}

export function isValidGradeBand(value: string): value is GradeBand {
  return ["k-2", "3-5", "6-8", "9-12"].includes(value);
}

export * from "./gradeBands";
