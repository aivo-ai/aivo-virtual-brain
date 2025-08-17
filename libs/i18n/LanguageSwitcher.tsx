import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useRTL } from "./RTLProvider";

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

interface Language {
  iso: string;
  displayName: string;
  nativeName: string;
  isRTL: boolean;
  fontStack: string;
}

interface LanguageSwitcherProps {
  languages: Language[];
  className?: string;
  variant?: "dropdown" | "modal" | "inline";
  showNativeName?: boolean;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  languages,
  className = "",
  variant = "dropdown",
  showNativeName = true,
}) => {
  const { t } = useTranslation();
  const { language, setLanguage, isRTL, direction } = useRTL();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  const handleLanguageChange = (newLanguage: Language) => {
    setLanguage(newLanguage);
    setIsOpen(false);

    // Announce language change for screen readers
    const announcement = t("language.languageChanged", {
      language: newLanguage.displayName,
    });
    const ariaLive = document.createElement("div");
    ariaLive.setAttribute("aria-live", "polite");
    ariaLive.setAttribute("aria-atomic", "true");
    ariaLive.className = "sr-only";
    ariaLive.textContent = announcement;
    document.body.appendChild(ariaLive);
    setTimeout(() => document.body.removeChild(ariaLive), 1000);
  };

  if (variant === "inline") {
    return (
      <div className={`flex flex-wrap gap-2 ${className}`} dir={direction}>
        {languages.map((lang) => (
          <button
            key={lang.iso}
            onClick={() => handleLanguageChange(lang)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              language?.iso === lang.iso
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
            style={{ fontFamily: lang.fontStack }}
            aria-label={t("language.changeLanguage")}
            aria-current={language?.iso === lang.iso ? "true" : "false"}
          >
            {showNativeName ? lang.nativeName : lang.displayName}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef} dir={direction}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={t("language.selectLanguage")}
        style={{ fontFamily: language?.fontStack }}
      >
        <GlobeIcon className="w-4 h-4" aria-hidden="true" />
        <span>
          {language
            ? showNativeName
              ? language.nativeName
              : language.displayName
            : t("language.selectLanguage")}
        </span>
        <ChevronDownIcon
          className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""} ${isRTL ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          className={`absolute z-50 w-64 mt-1 bg-white border border-gray-300 rounded-md shadow-lg ${
            isRTL ? "right-0" : "left-0"
          }`}
          role="listbox"
          aria-label={t("language.selectLanguage")}
        >
          <div className="py-1 max-h-60 overflow-auto">
            {languages.map((lang) => (
              <button
                key={lang.iso}
                onClick={() => handleLanguageChange(lang)}
                className={`w-full px-4 py-2 text-sm text-left hover:bg-gray-100 focus:outline-none focus:bg-gray-100 ${
                  language?.iso === lang.iso
                    ? "bg-blue-50 text-blue-600"
                    : "text-gray-700"
                } ${isRTL ? "text-right" : "text-left"}`}
                style={{ fontFamily: lang.fontStack }}
                role="option"
                aria-selected={language?.iso === lang.iso}
              >
                <div className="flex flex-col">
                  <span className="font-medium">{lang.displayName}</span>
                  {showNativeName && lang.nativeName !== lang.displayName && (
                    <span className="text-xs text-gray-500">
                      {lang.nativeName}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;
