import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  getLocaleConfig,
  getSupportedLanguages,
  getLanguageDisplayName,
} from "../index";

// Simple SVG icons to avoid React version conflicts
const GlobeIcon = ({ className }: { className: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"
    />
  </svg>
);

const ChevronDownIcon = ({ className }: { className: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m19.5 8.25-7.5 7.5-7.5-7.5"
    />
  </svg>
);

const CheckIcon = ({ className }: { className: string }) => (
  <svg
    className={className}
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m4.5 12.75 6 6 9-13.5"
    />
  </svg>
);

interface LanguageSwitcherProps {
  variant?: "button" | "dropdown" | "inline";
  showIcon?: boolean;
  showNativeNames?: boolean;
  className?: string;
  placement?: "bottom-left" | "bottom-right" | "top-left" | "top-right";
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  variant = "dropdown",
  showIcon = true,
  showNativeNames = true,
  className = "",
  placement = "bottom-left",
}) => {
  const { i18n, t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const supportedLanguages = getSupportedLanguages();
  const currentLanguage = i18n.language;
  const currentLocale = getLocaleConfig(currentLanguage);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLanguageChange = async (languageCode: string) => {
    try {
      await i18n.changeLanguage(languageCode);
      setIsOpen(false);

      // Update document direction
      const locale = getLocaleConfig(languageCode);
      if (locale) {
        document.documentElement.dir = locale.isRTL ? "rtl" : "ltr";
        document.documentElement.lang = languageCode;
      }

      // Show success message
      setTimeout(() => {
        // Could integrate with a toast system here
        console.log(
          t("language.languageChanged", {
            language: getLanguageDisplayName(languageCode),
          }),
        );
      }, 100);
    } catch (error) {
      console.error("Failed to change language:", error);
    }
  };

  const getPlacementClasses = () => {
    const baseClasses =
      "absolute z-50 mt-1 w-48 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none";

    switch (placement) {
      case "bottom-right":
        return `${baseClasses} right-0`;
      case "top-left":
        return `${baseClasses} bottom-full mb-1 left-0`;
      case "top-right":
        return `${baseClasses} bottom-full mb-1 right-0`;
      default:
        return `${baseClasses} left-0`;
    }
  };

  if (variant === "inline") {
    return (
      <div className={`flex flex-wrap gap-2 ${className}`}>
        {supportedLanguages.map((lang) => {
          const locale = getLocaleConfig(lang.iso);
          const isActive = lang.iso === currentLanguage;

          return (
            <button
              key={lang.iso}
              onClick={() => handleLanguageChange(lang.iso)}
              className={`
                px-3 py-1 rounded-md text-sm font-medium transition-colors
                ${
                  isActive
                    ? "bg-blue-100 text-blue-700 border border-blue-200"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200"
                }
              `}
              title={getLanguageDisplayName(lang.iso)}
            >
              {showNativeNames && locale?.nativeName
                ? locale.nativeName
                : locale?.displayName || lang.iso}
            </button>
          );
        })}
      </div>
    );
  }

  if (variant === "button") {
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`
            inline-flex items-center px-3 py-2 border border-gray-300 rounded-md 
            bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 
            focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            ${currentLocale?.isRTL ? "flex-row-reverse" : ""}
            ${className}
          `}
          aria-expanded={isOpen}
          aria-haspopup="true"
          aria-label={t("language.selectLanguage")}
        >
          {showIcon && (
            <GlobeIcon
              className={`h-4 w-4 ${currentLocale?.isRTL ? "ml-2" : "mr-2"}`}
            />
          )}
          <span className="truncate">
            {showNativeNames && currentLocale?.nativeName
              ? currentLocale.nativeName
              : currentLocale?.displayName || currentLanguage}
          </span>
          <ChevronDownIcon
            className={`h-4 w-4 ${currentLocale?.isRTL ? "mr-2" : "ml-2"} transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </button>

        {isOpen && (
          <div className={getPlacementClasses()}>
            <div className="py-1">
              {supportedLanguages.map((lang) => {
                const locale = getLocaleConfig(lang.iso);
                const isActive = lang.iso === currentLanguage;

                return (
                  <button
                    key={lang.iso}
                    onClick={() => handleLanguageChange(lang.iso)}
                    className={`
                      w-full px-4 py-2 text-left text-sm flex items-center justify-between
                      ${
                        isActive
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-700 hover:bg-gray-50"
                      }
                      ${locale?.isRTL ? "flex-row-reverse text-right" : ""}
                    `}
                    role="menuitem"
                  >
                    <div
                      className={`flex flex-col ${locale?.isRTL ? "items-end" : "items-start"}`}
                    >
                      <span className="font-medium">
                        {showNativeNames && locale?.nativeName
                          ? locale.nativeName
                          : locale?.displayName || lang.iso}
                      </span>
                      {showNativeNames &&
                        locale?.nativeName &&
                        locale?.displayName !== locale?.nativeName && (
                          <span className="text-xs text-gray-500">
                            {locale?.displayName}
                          </span>
                        )}
                    </div>
                    {isActive && (
                      <CheckIcon className="h-4 w-4 text-blue-600" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Default dropdown variant
  return (
    <div className="relative" ref={dropdownRef}>
      <select
        value={currentLanguage}
        onChange={(e) => handleLanguageChange(e.target.value)}
        className={`
          block w-full px-3 py-2 border border-gray-300 rounded-md 
          bg-white text-sm text-gray-700 
          focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
          ${currentLocale?.isRTL ? "text-right" : "text-left"}
          ${className}
        `}
        aria-label={t("language.selectLanguage")}
      >
        {supportedLanguages.map((lang) => {
          const locale = getLocaleConfig(lang.iso);

          return (
            <option key={lang.iso} value={lang.iso}>
              {showNativeNames && locale?.nativeName
                ? `${locale.nativeName}${locale?.displayName !== locale?.nativeName ? ` (${locale?.displayName})` : ""}`
                : locale?.displayName || lang.iso}
            </option>
          );
        })}
      </select>
    </div>
  );
};

export default LanguageSwitcher;
