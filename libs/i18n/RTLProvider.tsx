import React, { createContext, useContext, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

interface Language {
  iso: string;
  displayName: string;
  nativeName: string;
  isRTL: boolean;
  fontStack: string;
}

interface RTLContextType {
  isRTL: boolean;
  direction: "ltr" | "rtl";
  textAlign: "left" | "right";
  marginStart: string;
  marginEnd: string;
  paddingStart: string;
  paddingEnd: string;
  borderStart: string;
  borderEnd: string;
  language: Language | null;
  setLanguage: (language: Language) => void;
}

const RTLContext = createContext<RTLContextType | undefined>(undefined);

export const useRTL = () => {
  const context = useContext(RTLContext);
  if (context === undefined) {
    throw new Error("useRTL must be used within an RTLProvider");
  }
  return context;
};

interface RTLProviderProps {
  children: React.ReactNode;
  languages: Language[];
}

export const RTLProvider: React.FC<RTLProviderProps> = ({
  children,
  languages,
}) => {
  const { i18n } = useTranslation();
  const [currentLanguage, setCurrentLanguage] = useState<Language | null>(null);

  useEffect(() => {
    const savedLanguage = localStorage.getItem("preferred-language");
    const currentLang = savedLanguage || i18n.language || "en";

    const language =
      languages.find((lang) => lang.iso === currentLang) || languages[0];
    setCurrentLanguage(language);

    // Apply RTL styles to document
    if (language.isRTL) {
      document.documentElement.setAttribute("dir", "rtl");
      document.body.style.fontFamily = language.fontStack;
    } else {
      document.documentElement.setAttribute("dir", "ltr");
      document.body.style.fontFamily = language.fontStack;
    }
  }, [i18n.language, languages]);

  const setLanguage = (language: Language) => {
    setCurrentLanguage(language);
    i18n.changeLanguage(language.iso);
    localStorage.setItem("preferred-language", language.iso);

    // Update document direction and font
    document.documentElement.setAttribute(
      "dir",
      language.isRTL ? "rtl" : "ltr",
    );
    document.body.style.fontFamily = language.fontStack;
  };

  const isRTL = currentLanguage?.isRTL || false;
  const direction = isRTL ? "rtl" : "ltr";
  const textAlign = isRTL ? "right" : "left";

  const value: RTLContextType = {
    isRTL,
    direction,
    textAlign,
    marginStart: isRTL ? "marginRight" : "marginLeft",
    marginEnd: isRTL ? "marginLeft" : "marginRight",
    paddingStart: isRTL ? "paddingRight" : "paddingLeft",
    paddingEnd: isRTL ? "paddingLeft" : "paddingRight",
    borderStart: isRTL ? "borderRight" : "borderLeft",
    borderEnd: isRTL ? "borderLeft" : "borderRight",
    language: currentLanguage,
    setLanguage,
  };

  return (
    <RTLContext.Provider value={value}>
      <div dir={direction} style={{ fontFamily: currentLanguage?.fontStack }}>
        {children}
      </div>
    </RTLContext.Provider>
  );
};

export default RTLProvider;
