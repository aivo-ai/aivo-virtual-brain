import { describe, test, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useTranslation } from "react-i18next";
import i18n, {
  languages,
  getLanguageByIso,
  isRTLLanguage,
  getCurrentLanguage,
  formatNumber,
  formatCurrency,
  formatDate,
  formatTime,
  formatDateTime,
  getRelativeTime,
} from "./index";
import { RTLProvider, useRTL } from "./RTLProvider";
import LanguageSwitcher from "./LanguageSwitcher";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const translations: Record<string, string> = {
        "language.selectLanguage": "Select Language",
        "language.changeLanguage": "Change Language",
        "language.languageChanged": "Language changed to {{language}}",
        "dates.justNow": "Just now",
        "dates.minutesAgo": "{{minutes}} minutes ago",
        "dates.hoursAgo": "{{hours}} hours ago",
        "dates.daysAgo": "{{days}} days ago",
      };

      let result = translations[key] || key;
      if (options) {
        Object.keys(options).forEach((optionKey) => {
          result = result.replace(`{{${optionKey}}}`, options[optionKey]);
        });
      }
      return result;
    },
    i18n: {
      language: "en",
      changeLanguage: vi.fn(),
    },
  }),
  initReactI18next: {
    type: "3rdParty",
    init: vi.fn(),
  },
}));

// Mock heroicons
vi.mock("@heroicons/react/24/outline", () => ({
  ChevronDownIcon: ({ className }: { className: string }) => (
    <div className={className} data-testid="chevron-down-icon" />
  ),
  GlobeIcon: ({ className }: { className: string }) => (
    <div className={className} data-testid="globe-icon" />
  ),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

describe("i18n Configuration", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  test("should have all required languages", () => {
    const expectedLanguages = [
      "en",
      "es",
      "fr",
      "ar",
      "zh-Hans",
      "hi",
      "pt",
      "ig",
      "yo",
      "ha",
      "efi",
      "sw",
      "xh",
      "ki",
    ];

    expectedLanguages.forEach((lang) => {
      expect(languages.some((l) => l.iso === lang)).toBe(true);
    });
  });

  test("should identify RTL languages correctly", () => {
    expect(isRTLLanguage("ar")).toBe(true);
    expect(isRTLLanguage("en")).toBe(false);
    expect(isRTLLanguage("es")).toBe(false);
  });

  test("should get language by ISO code", () => {
    const english = getLanguageByIso("en");
    expect(english).toBeDefined();
    expect(english?.displayName).toBe("English");
    expect(english?.isRTL).toBe(false);

    const arabic = getLanguageByIso("ar");
    expect(arabic).toBeDefined();
    expect(arabic?.displayName).toBe("Arabic");
    expect(arabic?.isRTL).toBe(true);
  });

  test("should format numbers correctly", () => {
    const number = 1234.56;

    // English formatting
    const englishFormatted = formatNumber(number, "en");
    expect(englishFormatted).toMatch(/1,234\.56|1234\.56/);

    // French formatting (different decimal separator)
    const frenchFormatted = formatNumber(number, "fr");
    expect(frenchFormatted).toBeDefined();
  });

  test("should format currency correctly", () => {
    const amount = 99.99;

    const usdFormatted = formatCurrency(amount, "en");
    expect(usdFormatted).toMatch(/\$|USD/);

    const eurFormatted = formatCurrency(amount, "fr");
    expect(eurFormatted).toMatch(/€|EUR/);
  });

  test("should format dates correctly", () => {
    const date = new Date("2025-08-17T10:30:00Z");

    const englishDate = formatDate(date, "en");
    expect(englishDate).toContain("August");
    expect(englishDate).toContain("17");
    expect(englishDate).toContain("2025");
  });

  test("should format time correctly", () => {
    const date = new Date("2025-08-17T10:30:00Z");

    const englishTime = formatTime(date, "en");
    expect(englishTime).toBeDefined();
  });

  test("should format relative time correctly", () => {
    const now = new Date();
    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    expect(getRelativeTime(new Date(now.getTime() - 30 * 1000))).toBe(
      "Just now",
    );
    expect(getRelativeTime(fiveMinutesAgo)).toBe("5 minutes ago");
    expect(getRelativeTime(oneHourAgo)).toBe("1 hours ago");
    expect(getRelativeTime(oneDayAgo)).toBe("1 days ago");
  });
});

describe("RTLProvider", () => {
  const mockLanguages = [
    {
      iso: "en",
      displayName: "English",
      nativeName: "English",
      isRTL: false,
      fontStack: "Arial, sans-serif",
      currency: "USD",
      dateFormat: "MM/DD/YYYY",
      timeFormat: "12h",
      decimalSeparator: ".",
      thousandsSeparator: ",",
      speechSupported: true,
    },
    {
      iso: "ar",
      displayName: "Arabic",
      nativeName: "العربية",
      isRTL: true,
      fontStack: "Noto Sans Arabic, Arial, sans-serif",
      currency: "SAR",
      dateFormat: "DD/MM/YYYY",
      timeFormat: "24h",
      decimalSeparator: ".",
      thousandsSeparator: ",",
      speechSupported: true,
    },
  ];

  const TestComponent = () => {
    const { isRTL, direction, language } = useRTL();
    return (
      <div data-testid="test-component" dir={direction}>
        <span data-testid="rtl-status">{isRTL ? "RTL" : "LTR"}</span>
        <span data-testid="language">{language?.displayName}</span>
      </div>
    );
  };

  test("should provide RTL context", () => {
    render(
      <RTLProvider languages={mockLanguages}>
        <TestComponent />
      </RTLProvider>,
    );

    expect(screen.getByTestId("rtl-status")).toHaveTextContent("LTR");
    expect(screen.getByTestId("language")).toHaveTextContent("English");
  });

  test("should update document direction when language changes", () => {
    const { rerender } = render(
      <RTLProvider languages={mockLanguages}>
        <TestComponent />
      </RTLProvider>,
    );

    // Initially LTR
    expect(document.documentElement.getAttribute("dir")).toBe("ltr");

    // Mock language change to Arabic
    vi.mocked(useTranslation().i18n.language).mockReturnValue("ar");

    rerender(
      <RTLProvider languages={mockLanguages}>
        <TestComponent />
      </RTLProvider>,
    );

    // Should be RTL for Arabic
    expect(document.documentElement.getAttribute("dir")).toBe("rtl");
  });
});

describe("LanguageSwitcher", () => {
  const mockLanguages = [
    {
      iso: "en",
      displayName: "English",
      nativeName: "English",
      isRTL: false,
      fontStack: "Arial, sans-serif",
      currency: "USD",
      dateFormat: "MM/DD/YYYY",
      timeFormat: "12h",
      decimalSeparator: ".",
      thousandsSeparator: ",",
      speechSupported: true,
    },
    {
      iso: "es",
      displayName: "Spanish",
      nativeName: "Español",
      isRTL: false,
      fontStack: "Arial, sans-serif",
      currency: "EUR",
      dateFormat: "DD/MM/YYYY",
      timeFormat: "24h",
      decimalSeparator: ",",
      thousandsSeparator: ".",
      speechSupported: true,
    },
    {
      iso: "ar",
      displayName: "Arabic",
      nativeName: "العربية",
      isRTL: true,
      fontStack: "Noto Sans Arabic, Arial, sans-serif",
      currency: "SAR",
      dateFormat: "DD/MM/YYYY",
      timeFormat: "24h",
      decimalSeparator: ".",
      thousandsSeparator: ",",
      speechSupported: true,
    },
  ];

  const WrappedLanguageSwitcher = ({
    variant = "dropdown",
  }: {
    variant?: "dropdown" | "inline" | "modal";
  }) => (
    <RTLProvider languages={mockLanguages}>
      <LanguageSwitcher languages={mockLanguages} variant={variant} />
    </RTLProvider>
  );

  test("should render dropdown variant", () => {
    render(<WrappedLanguageSwitcher />);

    expect(screen.getByRole("button")).toBeInTheDocument();
    expect(screen.getByTestId("globe-icon")).toBeInTheDocument();
    expect(screen.getByTestId("chevron-down-icon")).toBeInTheDocument();
  });

  test("should render inline variant", () => {
    render(<WrappedLanguageSwitcher variant="inline" />);

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(mockLanguages.length);

    // Should show language names
    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("Español")).toBeInTheDocument();
    expect(screen.getByText("العربية")).toBeInTheDocument();
  });

  test("should open dropdown when clicked", async () => {
    render(<WrappedLanguageSwitcher />);

    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    // Should show all language options
    expect(screen.getByText("Spanish")).toBeInTheDocument();
    expect(screen.getByText("Arabic")).toBeInTheDocument();
  });

  test("should handle language selection", async () => {
    const mockChangeLanguage = vi.fn();
    vi.mocked(useTranslation().i18n.changeLanguage).mockImplementation(
      mockChangeLanguage,
    );

    render(<WrappedLanguageSwitcher />);

    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    const spanishOption = screen.getByText("Spanish");
    fireEvent.click(spanishOption);

    expect(mockChangeLanguage).toHaveBeenCalledWith("es");
  });

  test("should be accessible", () => {
    render(<WrappedLanguageSwitcher />);

    const trigger = screen.getByRole("button");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveAttribute("aria-haspopup", "listbox");
    expect(trigger).toHaveAttribute("aria-label", "Select Language");
  });

  test("should support keyboard navigation", async () => {
    render(<WrappedLanguageSwitcher />);

    const trigger = screen.getByRole("button");

    // Open with Enter key
    fireEvent.keyDown(trigger, { key: "Enter" });

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    // Navigate with arrow keys
    const listbox = screen.getByRole("listbox");
    fireEvent.keyDown(listbox, { key: "ArrowDown" });

    // Should focus on first option
    const firstOption = screen.getAllByRole("option")[0];
    expect(firstOption).toBeInTheDocument();
  });

  test("should close on outside click", async () => {
    render(<WrappedLanguageSwitcher />);

    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    // Click outside
    fireEvent.mouseDown(document.body);

    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  test("should announce language changes for screen readers", async () => {
    const mockChangeLanguage = vi.fn();
    vi.mocked(useTranslation().i18n.changeLanguage).mockImplementation(
      mockChangeLanguage,
    );

    render(<WrappedLanguageSwitcher />);

    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    const spanishOption = screen.getByText("Spanish");
    fireEvent.click(spanishOption);

    // Should create aria-live announcement
    await waitFor(() => {
      const announcement = document.querySelector('[aria-live="polite"]');
      expect(announcement).toBeInTheDocument();
      expect(announcement?.textContent).toBe("Language changed to Spanish");
    });
  });
});

describe("Accessibility", () => {
  test("should support high contrast mode", () => {
    // Mock high contrast media query
    const mockMatchMedia = vi.fn(() => ({
      matches: true,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }));

    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: mockMatchMedia,
    });

    render(
      <RTLProvider languages={languages}>
        <LanguageSwitcher languages={languages} />
      </RTLProvider>,
    );

    expect(mockMatchMedia).toHaveBeenCalledWith("(prefers-contrast: high)");
  });

  test("should respect reduced motion preferences", () => {
    const mockMatchMedia = vi.fn(() => ({
      matches: true,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }));

    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: mockMatchMedia,
    });

    render(
      <RTLProvider languages={languages}>
        <LanguageSwitcher languages={languages} />
      </RTLProvider>,
    );

    expect(mockMatchMedia).toHaveBeenCalledWith(
      "(prefers-reduced-motion: reduce)",
    );
  });

  test("should provide proper ARIA labels and roles", () => {
    render(
      <RTLProvider languages={languages}>
        <LanguageSwitcher languages={languages} />
      </RTLProvider>,
    );

    const trigger = screen.getByRole("button");
    expect(trigger).toHaveAttribute("aria-label", "Select Language");
    expect(trigger).toHaveAttribute("aria-haspopup", "listbox");
  });
});

describe("Font Stack Support", () => {
  test("should apply correct font stacks for different languages", () => {
    const arabicLang = getLanguageByIso("ar");
    const chineseLang = getLanguageByIso("zh-Hans");
    const hindiLang = getLanguageByIso("hi");

    expect(arabicLang?.fontStack).toContain("Noto Sans Arabic");
    expect(chineseLang?.fontStack).toContain("Noto Sans SC");
    expect(hindiLang?.fontStack).toContain("Noto Sans Devanagari");
  });

  test("should fall back to system fonts", () => {
    const englishLang = getLanguageByIso("en");
    expect(englishLang?.fontStack).toContain("system-ui");
  });
});

describe("Performance", () => {
  test("should not cause memory leaks with event listeners", () => {
    const addEventListenerSpy = vi.spyOn(document, "addEventListener");
    const removeEventListenerSpy = vi.spyOn(document, "removeEventListener");

    const { unmount } = render(
      <RTLProvider languages={languages}>
        <LanguageSwitcher languages={languages} />
      </RTLProvider>,
    );

    // Should add event listeners
    expect(addEventListenerSpy).toHaveBeenCalled();

    unmount();

    // Should clean up event listeners
    expect(removeEventListenerSpy).toHaveBeenCalled();
  });

  test("should handle rapid language switching", async () => {
    const mockChangeLanguage = vi.fn();
    vi.mocked(useTranslation().i18n.changeLanguage).mockImplementation(
      mockChangeLanguage,
    );

    render(
      <RTLProvider languages={languages}>
        <LanguageSwitcher languages={languages} variant="inline" />
      </RTLProvider>,
    );

    const buttons = screen.getAllByRole("button");

    // Rapidly click different language buttons
    for (let i = 0; i < 5; i++) {
      fireEvent.click(buttons[i % buttons.length]);
    }

    // Should handle all calls without errors
    expect(mockChangeLanguage).toHaveBeenCalledTimes(5);
  });
});
