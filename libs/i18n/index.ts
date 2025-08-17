import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Import all translations
import en from "./resources/en.json";
import es from "./resources/es.json";
import fr from "./resources/fr.json";
import ar from "./resources/ar.json";
import zhHans from "./resources/zh-Hans.json";
import hi from "./resources/hi.json";
import pt from "./resources/pt.json";
import ig from "./resources/ig.json";
import yo from "./resources/yo.json";
import ha from "./resources/ha.json";
import efi from "./resources/efi.json";
import sw from "./resources/sw.json";
import xh from "./resources/xh.json";
import ki from "./resources/ki.json";

// Import locale configuration
import localesData from "./locales.json";

export interface Language {
  iso: string;
  displayName: string;
  nativeName: string;
  isRTL: boolean;
  fontStack: string;
  currency: string;
  dateFormat: string;
  timeFormat: string;
  decimalSeparator: string;
  thousandsSeparator: string;
  speechSupported: boolean;
}

// Extract languages from locales data
export const languages: Language[] = Object.entries(
  localesData.supported_locales,
).map(([iso, config]: [string, any]) => ({
  iso,
  displayName: config.display_name,
  nativeName: config.native_name,
  isRTL: localesData.rtl_locales.includes(iso),
  fontStack: config.font_stack,
  currency: config.currency,
  dateFormat: config.date_format,
  timeFormat: config.time_format,
  decimalSeparator: config.decimal_separator,
  thousandsSeparator: config.thousands_separator,
  speechSupported: config.speech_supported,
}));

const resources = {
  en: { translation: en },
  es: { translation: es },
  fr: { translation: fr },
  ar: { translation: ar },
  "zh-Hans": { translation: zhHans },
  hi: { translation: hi },
  pt: { translation: pt },
  ig: { translation: ig },
  yo: { translation: yo },
  ha: { translation: ha },
  efi: { translation: efi },
  sw: { translation: sw },
  xh: { translation: xh },
  ki: { translation: ki },
};

// Initialize i18next
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    debug: process.env.NODE_ENV === "development",

    detection: {
      order: ["localStorage", "navigator", "htmlTag"],
      caches: ["localStorage"],
      lookupLocalStorage: "aivoLanguage",
    },

    interpolation: {
      escapeValue: false,
      format: (value: any, format?: string, lng?: string) => {
        if (!format || !lng) return value;

        const language = getLanguageByIso(lng);
        if (!language) return value;

        if (format === "currency") {
          return new Intl.NumberFormat(lng, {
            style: "currency",
            currency: language.currency,
          }).format(value);
        }

        if (format === "number") {
          return new Intl.NumberFormat(lng, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
          }).format(value);
        }

        if (format === "date") {
          return new Intl.DateTimeFormat(lng, {
            year: "numeric",
            month: "long",
            day: "numeric",
          }).format(new Date(value));
        }

        if (format === "time") {
          return new Intl.DateTimeFormat(lng, {
            hour: "numeric",
            minute: "numeric",
            hour12: language.timeFormat === "12h",
          }).format(new Date(value));
        }

        return value;
      },
    },

    react: {
      useSuspense: false,
    },
  });

// Utility functions
export const getLanguageByIso = (iso: string): Language | undefined => {
  return languages.find((lang) => lang.iso === iso);
};

export const isRTLLanguage = (iso: string): boolean => {
  const language = getLanguageByIso(iso);
  return language?.isRTL || false;
};

export const getCurrentLanguage = (): Language => {
  const currentLang = i18n.language || "en";
  return getLanguageByIso(currentLang) || getLanguageByIso("en")!;
};

export const formatNumber = (value: number, locale?: string): string => {
  const lang = locale || i18n.language;
  const language = getLanguageByIso(lang);

  if (!language) return value.toString();

  return new Intl.NumberFormat(lang, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
};

export const formatCurrency = (value: number, locale?: string): string => {
  const lang = locale || i18n.language;
  const language = getLanguageByIso(lang);

  if (!language) return value.toString();

  return new Intl.NumberFormat(lang, {
    style: "currency",
    currency: language.currency,
  }).format(value);
};

export const formatDate = (date: Date | string, locale?: string): string => {
  const lang = locale || i18n.language;
  const dateObj = typeof date === "string" ? new Date(date) : date;

  return new Intl.DateTimeFormat(lang, {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(dateObj);
};

export const formatTime = (date: Date | string, locale?: string): string => {
  const lang = locale || i18n.language;
  const language = getLanguageByIso(lang);
  const dateObj = typeof date === "string" ? new Date(date) : date;

  return new Intl.DateTimeFormat(lang, {
    hour: "numeric",
    minute: "numeric",
    hour12: language?.timeFormat === "12h",
  }).format(dateObj);
};

export const formatDateTime = (
  date: Date | string,
  locale?: string,
): string => {
  const lang = locale || i18n.language;
  const language = getLanguageByIso(lang);
  const dateObj = typeof date === "string" ? new Date(date) : date;

  return new Intl.DateTimeFormat(lang, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    hour12: language?.timeFormat === "12h",
  }).format(dateObj);
};

export const getRelativeTime = (
  date: Date | string,
  locale?: string,
): string => {
  const lang = locale || i18n.language;
  const dateObj = typeof date === "string" ? new Date(date) : date;
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return i18n.t("dates.justNow");
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return i18n.t("dates.minutesAgo", { minutes });
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return i18n.t("dates.hoursAgo", { hours });
  } else if (diffInSeconds < 604800) {
    const days = Math.floor(diffInSeconds / 86400);
    return i18n.t("dates.daysAgo", { days });
  } else {
    return formatDate(dateObj, lang);
  }
};

// Re-export components
export { RTLProvider, useRTL } from "./RTLProvider";
export { default as LanguageSwitcher } from "./LanguageSwitcher";

export default i18n;
