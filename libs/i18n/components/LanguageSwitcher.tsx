import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  ChevronDownIcon,
  CheckIcon,
  GlobeAltIcon,
} from "@heroicons/react/24/outline";
import {
  getLocaleConfig,
  getSupportedLanguages,
  getLanguageDisplayName,
} from "../index";

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
        document.documentElement.dir = locale.rtl ? "rtl" : "ltr";
        document.documentElement.lang = languageCode;
      }

      // Show success message
      setTimeout(() => {
        // Could integrate with a toast system here
        console.log(
          t("language.languageChanged", {
            language: getLanguageDisplayName(languageCode, languageCode),
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
          const locale = getLocaleConfig(lang);
          const isActive = lang === currentLanguage;

          return (
            <button
              key={lang}
              onClick={() => handleLanguageChange(lang)}
              className={`
                px-3 py-1 rounded-md text-sm font-medium transition-colors
                ${
                  isActive
                    ? "bg-blue-100 text-blue-700 border border-blue-200"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200"
                }
              `}
              title={getLanguageDisplayName(lang, currentLanguage)}
            >
              {showNativeNames && locale?.nativeName
                ? locale.nativeName
                : locale?.name || lang}
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
            ${currentLocale?.rtl ? "flex-row-reverse" : ""}
            ${className}
          `}
          aria-expanded={isOpen}
          aria-haspopup="true"
          aria-label={t("language.selectLanguage")}
        >
          {showIcon && (
            <GlobeAltIcon
              className={`h-4 w-4 ${currentLocale?.rtl ? "ml-2" : "mr-2"}`}
            />
          )}
          <span className="truncate">
            {showNativeNames && currentLocale?.nativeName
              ? currentLocale.nativeName
              : currentLocale?.name || currentLanguage}
          </span>
          <ChevronDownIcon
            className={`h-4 w-4 ${currentLocale?.rtl ? "mr-2" : "ml-2"} transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </button>

        {isOpen && (
          <div className={getPlacementClasses()}>
            <div className="py-1">
              {supportedLanguages.map((lang) => {
                const locale = getLocaleConfig(lang);
                const isActive = lang === currentLanguage;

                return (
                  <button
                    key={lang}
                    onClick={() => handleLanguageChange(lang)}
                    className={`
                      w-full px-4 py-2 text-left text-sm flex items-center justify-between
                      ${
                        isActive
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-700 hover:bg-gray-50"
                      }
                      ${locale?.rtl ? "flex-row-reverse text-right" : ""}
                    `}
                    role="menuitem"
                  >
                    <div
                      className={`flex flex-col ${locale?.rtl ? "items-end" : "items-start"}`}
                    >
                      <span className="font-medium">
                        {showNativeNames && locale?.nativeName
                          ? locale.nativeName
                          : locale?.name || lang}
                      </span>
                      {showNativeNames &&
                        locale?.nativeName &&
                        locale?.name !== locale?.nativeName && (
                          <span className="text-xs text-gray-500">
                            {locale?.name}
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
          ${currentLocale?.rtl ? "text-right" : "text-left"}
          ${className}
        `}
        aria-label={t("language.selectLanguage")}
      >
        {supportedLanguages.map((lang) => {
          const locale = getLocaleConfig(lang);

          return (
            <option key={lang} value={lang}>
              {showNativeNames && locale?.nativeName
                ? `${locale.nativeName}${locale?.name !== locale?.nativeName ? ` (${locale?.name})` : ""}`
                : locale?.name || lang}
            </option>
          );
        })}
      </select>
    </div>
  );
};

export default LanguageSwitcher;
