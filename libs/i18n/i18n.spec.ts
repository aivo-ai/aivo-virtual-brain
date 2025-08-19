// i18n Library Tests - Basic validation without external test framework
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
  getSupportedLanguages,
  getLanguageDisplayName,
} from './index';

// Basic test runner
function test(name: string, fn: () => void | Promise<void>) {
  try {
    console.log(`Running: ${name}`);
    fn();
    console.log(`✓ ${name}`);
  } catch (error) {
    console.error(`✗ ${name}: ${error}`);
    throw error;
  }
}

function expect(actual: any) {
  return {
    toBe: (expected: any) => {
      if (actual !== expected) {
        throw new Error(`Expected ${actual} to be ${expected}`);
      }
    },
    toContain: (expected: any) => {
      if (!actual.includes(expected)) {
        throw new Error(`Expected ${actual} to contain ${expected}`);
      }
    },
    toBeDefined: () => {
      if (actual === undefined) {
        throw new Error(`Expected ${actual} to be defined`);
      }
    },
    toBeUndefined: () => {
      if (actual !== undefined) {
        throw new Error(`Expected ${actual} to be undefined`);
      }
    },
    toBeGreaterThan: (expected: number) => {
      if (actual <= expected) {
        throw new Error(`Expected ${actual} to be greater than ${expected}`);
      }
    },
    toHaveLength: (expected: number) => {
      if (actual.length !== expected) {
        throw new Error(`Expected ${actual} to have length ${expected}`);
      }
    },
    toMatch: (pattern: RegExp) => {
      if (!pattern.test(actual)) {
        throw new Error(`Expected ${actual} to match ${pattern}`);
      }
    }
  };
}

// Run tests
console.log('🧪 Running i18n Library Tests\n');

// Language Configuration Tests
test('should have all required languages', () => {
  const expectedLanguages = [
    'en', 'es', 'fr', 'ar', 'zh-Hans', 'hi', 'pt', 
    'ig', 'yo', 'ha', 'efi', 'sw', 'xh', 'ki'
  ];
  
  const languageCodes = languages.map(lang => lang.iso);
  expectedLanguages.forEach(code => {
    expect(languageCodes).toContain(code);
  });
  
  expect(languages.length).toBe(14);
});

test('should have font stacks for all languages', () => {
  languages.forEach(language => {
    expect(language.fontStack).toBeDefined();
    expect(typeof language.fontStack).toBe('string');
    expect(language.fontStack.length).toBeGreaterThan(0);
  });
});

test('should correctly identify RTL languages', () => {
  expect(isRTLLanguage('ar')).toBe(true);
  expect(isRTLLanguage('en')).toBe(false);
  expect(isRTLLanguage('es')).toBe(false);
  expect(isRTLLanguage('zh-Hans')).toBe(false);
});

test('should have Arabic with proper RTL configuration', () => {
  const arabic = getLanguageByIso('ar');
  expect(arabic).toBeDefined();
  expect(arabic!.isRTL).toBe(true);
  expect(arabic!.fontStack).toContain('Arabic');
});

test('should have Chinese with proper font stack', () => {
  const chinese = getLanguageByIso('zh-Hans');
  expect(chinese).toBeDefined();
  expect(chinese!.fontStack).toContain('Noto Sans SC');
  expect(chinese!.isRTL).toBe(false);
});

test('should have Hindi with proper font stack', () => {
  const hindi = getLanguageByIso('hi');
  expect(hindi).toBeDefined();
  expect(hindi!.fontStack).toContain('Devanagari');
  expect(hindi!.isRTL).toBe(false);
});

// Language Utilities Tests
test('getLanguageByIso should return correct language', () => {
  const english = getLanguageByIso('en');
  expect(english).toBeDefined();
  expect(english!.iso).toBe('en');
  expect(english!.displayName).toBe('English');
  expect(english!.nativeName).toBe('English');
});

test('getLanguageByIso should return undefined for invalid ISO', () => {
  const invalid = getLanguageByIso('invalid');
  expect(invalid).toBeUndefined();
});

test('getSupportedLanguages should return all languages', () => {
  const supported = getSupportedLanguages();
  expect(supported.length).toBe(14);
});

test('getLanguageDisplayName should return display name', () => {
  expect(getLanguageDisplayName('en')).toBe('English');
  expect(getLanguageDisplayName('ar')).toBe('Arabic');
  expect(getLanguageDisplayName('invalid')).toBe('invalid');
});

// Number and Currency Formatting Tests
test('should format numbers correctly for English locale', () => {
  const number = 1234.56;
  const englishNumber = formatNumber(number, 'en');
  expect(englishNumber).toBe('1,234.56');
});

test('should format currency correctly for English locale', () => {
  const amount = 1234.56;
  const usd = formatCurrency(amount, 'en');
  expect(usd).toMatch(/\$1,234\.56/);
});

test('should handle edge cases in formatting', () => {
  expect(formatNumber(0)).toBe('0');
  const zeroCurrency = formatCurrency(0);
  expect(typeof zeroCurrency).toBe('string');
});

// Date and Time Formatting Tests
test('should format dates correctly for English locale', () => {
  const testDate = new Date('2023-12-25T15:30:00Z');
  const englishDate = formatDate(testDate, 'en');
  expect(englishDate).toContain('December');
  expect(englishDate).toContain('25');
  expect(englishDate).toContain('2023');
});

test('should format time correctly for English locale', () => {
  const testDate = new Date('2023-12-25T15:30:00Z');
  const englishTime = formatTime(testDate, 'en');
  expect(englishTime).toMatch(/\d{1,2}:\d{2}/);
});

// African Languages Support Tests
test('should support Nigerian languages', () => {
  const nigerianLanguages = ['ig', 'yo', 'ha', 'efi'];
  nigerianLanguages.forEach(code => {
    const lang = getLanguageByIso(code);
    expect(lang).toBeDefined();
    expect(lang!.region).toBe('NG');
    expect(lang!.currency).toBe('NGN');
  });
});

test('should support East African languages', () => {
  const swahili = getLanguageByIso('sw');
  const kikuyu = getLanguageByIso('ki');
  
  expect(swahili).toBeDefined();
  expect(swahili!.region).toBe('KE');
  expect(swahili!.currency).toBe('KES');
  
  expect(kikuyu).toBeDefined();
  expect(kikuyu!.region).toBe('KE');
});

test('should support South African languages', () => {
  const xhosa = getLanguageByIso('xh');
  expect(xhosa).toBeDefined();
  expect(xhosa!.region).toBe('ZA');
  expect(xhosa!.currency).toBe('ZAR');
});

// Font Stack Validation Tests
test('Arabic should have proper Arabic fonts', () => {
  const arabic = getLanguageByIso('ar');
  expect(arabic!.fontStack).toContain('Noto Sans Arabic');
  expect(arabic!.fontStack).toContain('Arabic Typesetting');
});

test('Chinese should have proper Chinese fonts', () => {
  const chinese = getLanguageByIso('zh-Hans');
  expect(chinese!.fontStack).toContain('Noto Sans SC');
  expect(chinese!.fontStack).toContain('PingFang SC');
});

test('Hindi should have proper Devanagari fonts', () => {
  const hindi = getLanguageByIso('hi');
  expect(hindi!.fontStack).toContain('Noto Sans Devanagari');
  expect(hindi!.fontStack).toContain('Mangal');
});

test('African languages should have fallback fonts', () => {
  const africanLanguages = ['ig', 'yo', 'ha', 'sw', 'xh', 'ki'];
  africanLanguages.forEach(code => {
    const lang = getLanguageByIso(code);
    expect(lang!.fontStack).toContain('Noto Sans');
    expect(lang!.fontStack).toContain('sans-serif');
  });
});

// RTL Support Tests
test('should identify RTL languages correctly', () => {
  expect(isRTLLanguage('ar')).toBe(true);
  const rtlLanguages = languages.filter(lang => lang.isRTL);
  expect(rtlLanguages).toHaveLength(1);
  expect(rtlLanguages[0].iso).toBe('ar');
});

test('should have proper font support for RTL languages', () => {
  const arabic = getLanguageByIso('ar');
  expect(arabic!.fontStack).toContain('Arabic');
  expect(arabic!.isRTL).toBe(true);
});

console.log('\n🎉 All tests passed!');

export {};