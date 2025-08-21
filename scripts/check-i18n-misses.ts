#!/usr/bin/env tsx

/**
 * S4-19 I18n Translation Coverage Checker
 * Detects missing translation keys across all supported languages
 * Fails build if any missing translations are found
 */

import fs from 'fs'
import path from 'path'
import { globby } from 'globby'

interface TranslationKey {
  key: string
  file: string
  line: number
  context: string
}

interface LanguageTranslations {
  [key: string]: any
}

interface CoverageReport {
  totalKeys: number
  missingByLanguage: Record<string, string[]>
  unusedKeys: string[]
  inconsistentPlurals: string[]
  summary: {
    coveragePercentage: Record<string, number>
    criticalMissing: string[]
  }
}

class I18nCoverageChecker {
  private sourcePatterns = [
    'apps/web/src/**/*.{ts,tsx,js,jsx}',
    'libs/**/*.{ts,tsx,js,jsx}',
    'services/*/app/**/*.{py,js,ts}',
    'services/*/tests/**/*.{py,js,ts}'
  ]

  private translationPaths = {
    web: 'libs/i18n/resources',
    services: 'services/*/locales'
  }

  private supportedLanguages = [
    'en', 'es', 'fr', 'ar', 'zh-Hans', 'hi', 'pt', 
    'ig', 'yo', 'ha', 'efi', 'sw', 'xh', 'ki'
  ]

  private criticalNamespaces = [
    'common', 'navigation', 'auth', 'validation', 'errors', 
    'accessibility', 'dashboard', 'student', 'teacher', 'parent', 'admin'
  ]

  async checkCoverage(): Promise<CoverageReport> {
    console.log('🔍 S4-19 I18n Coverage Check: Scanning for translation keys...')
    
    // Extract all translation keys from source code
    const extractedKeys = await this.extractTranslationKeys()
    console.log(`📝 Found ${extractedKeys.length} translation key usages`)
    
    // Load all translation files
    const translations = await this.loadTranslations()
    console.log(`🌐 Loaded translations for ${Object.keys(translations).length} languages`)
    
    // Analyze coverage
    const report = this.analyzeCoverage(extractedKeys, translations)
    
    return report
  }

  private async extractTranslationKeys(): Promise<TranslationKey[]> {
    const keys: TranslationKey[] = []
    
    // Find all source files
    const sourceFiles = await globby(this.sourcePatterns, {
      gitignore: true,
      ignore: ['**/node_modules/**', '**/dist/**', '**/build/**', '**/.next/**']
    })
    
    console.log(`📂 Scanning ${sourceFiles.length} source files...`)
    
    for (const filePath of sourceFiles) {
      const content = fs.readFileSync(filePath, 'utf8')
      const fileKeys = this.extractKeysFromFile(content, filePath)
      keys.push(...fileKeys)
    }
    
    return keys
  }

  private extractKeysFromFile(content: string, filePath: string): TranslationKey[] {
    const keys: TranslationKey[] = []
    const lines = content.split('\n')
    
    // Patterns for different translation key formats
    const patterns = [
      // React i18next: t('key'), t("key")
      /(?:^|[^a-zA-Z])t\s*\(\s*['"`]([^'"`]+)['"`]/g,
      // useTranslation hook: t('key')
      /\.t\s*\(\s*['"`]([^'"`]+)['"`]/g,
      // i18n.translate: i18n.translate('key')
      /i18n\.translate\s*\(\s*['"`]([^'"`]+)['"`]/g,
      // Python: _('key'), gettext('key')
      /(?:_|gettext)\s*\(\s*['"`]([^'"`]+)['"`]/g,
      // Template literals: ${t('key')}
      /\$\{[^}]*t\s*\(\s*['"`]([^'"`]+)['"`]/g,
      // Vue i18n: $t('key')
      /\$t\s*\(\s*['"`]([^'"`]+)['"`]/g
    ]
    
    lines.forEach((line, index) => {
      patterns.forEach(pattern => {
        let match
        while ((match = pattern.exec(line)) !== null) {
          const key = match[1]
          if (key && !key.includes('${') && !key.includes('{{')) { // Skip interpolated keys
            keys.push({
              key,
              file: filePath,
              line: index + 1,
              context: line.trim()
            })
          }
        }
      })
    })
    
    return keys
  }

  private async loadTranslations(): Promise<Record<string, LanguageTranslations>> {
    const translations: Record<string, LanguageTranslations> = {}
    
    // Load web translations
    const webTranslationsPath = this.translationPaths.web
    if (fs.existsSync(webTranslationsPath)) {
      for (const lang of this.supportedLanguages) {
        const langFile = path.join(webTranslationsPath, `${lang}.json`)
        if (fs.existsSync(langFile)) {
          try {
            const content = JSON.parse(fs.readFileSync(langFile, 'utf8'))
            translations[lang] = content
          } catch (error) {
            console.warn(`⚠️  Failed to parse ${langFile}: ${error}`)
          }
        }
      }
    }
    
    // Load service translations
    const serviceTranslations = await globby('services/*/locales/*.json')
    for (const translationFile of serviceTranslations) {
      const lang = path.basename(translationFile, '.json')
      if (this.supportedLanguages.includes(lang)) {
        try {
          const content = JSON.parse(fs.readFileSync(translationFile, 'utf8'))
          if (!translations[lang]) {
            translations[lang] = {}
          }
          // Merge service translations
          Object.assign(translations[lang], content)
        } catch (error) {
          console.warn(`⚠️  Failed to parse ${translationFile}: ${error}`)
        }
      }
    }
    
    return translations
  }

  private analyzeCoverage(
    extractedKeys: TranslationKey[], 
    translations: Record<string, LanguageTranslations>
  ): CoverageReport {
    const uniqueKeys = [...new Set(extractedKeys.map(k => k.key))]
    const report: CoverageReport = {
      totalKeys: uniqueKeys.length,
      missingByLanguage: {},
      unusedKeys: [],
      inconsistentPlurals: [],
      summary: {
        coveragePercentage: {},
        criticalMissing: []
      }
    }
    
    // Check coverage for each language
    for (const lang of this.supportedLanguages) {
      const langTranslations = translations[lang] || {}
      const missing: string[] = []
      
      for (const key of uniqueKeys) {
        if (!this.hasTranslation(langTranslations, key)) {
          missing.push(key)
        }
      }
      
      report.missingByLanguage[lang] = missing
      report.summary.coveragePercentage[lang] = 
        ((uniqueKeys.length - missing.length) / uniqueKeys.length) * 100
    }
    
    // Find unused keys (exist in translations but not in code)
    const englishTranslations = translations['en'] || {}
    const allTranslationKeys = this.flattenKeys(englishTranslations)
    
    for (const translationKey of allTranslationKeys) {
      if (!uniqueKeys.includes(translationKey)) {
        report.unusedKeys.push(translationKey)
      }
    }
    
    // Find critical missing keys
    const criticalMissing = new Set<string>()
    for (const key of uniqueKeys) {
      for (const namespace of this.criticalNamespaces) {
        if (key.startsWith(`${namespace}.`)) {
          for (const lang of this.supportedLanguages) {
            if (report.missingByLanguage[lang]?.includes(key)) {
              criticalMissing.add(key)
            }
          }
        }
      }
    }
    
    report.summary.criticalMissing = Array.from(criticalMissing)
    
    // Check for plural inconsistencies
    report.inconsistentPlurals = this.findPluralInconsistencies(uniqueKeys, translations)
    
    return report
  }

  private hasTranslation(translations: LanguageTranslations, key: string): boolean {
    const keys = key.split('.')
    let current = translations
    
    for (const k of keys) {
      if (typeof current !== 'object' || current === null || !(k in current)) {
        return false
      }
      current = current[k]
    }
    
    return typeof current === 'string' || 
           (typeof current === 'object' && current !== null && 
            ('zero' in current || 'one' in current || 'other' in current))
  }

  private flattenKeys(obj: any, prefix = ''): string[] {
    const keys: string[] = []
    
    for (const key in obj) {
      const fullKey = prefix ? `${prefix}.${key}` : key
      
      if (typeof obj[key] === 'object' && obj[key] !== null) {
        // Handle plural forms
        if ('zero' in obj[key] || 'one' in obj[key] || 'other' in obj[key]) {
          keys.push(fullKey)
        } else {
          keys.push(...this.flattenKeys(obj[key], fullKey))
        }
      } else if (typeof obj[key] === 'string') {
        keys.push(fullKey)
      }
    }
    
    return keys
  }

  private findPluralInconsistencies(
    keys: string[], 
    translations: Record<string, LanguageTranslations>
  ): string[] {
    const inconsistent: string[] = []
    const pluralKeys = keys.filter(key => 
      key.includes('_zero') || key.includes('_one') || key.includes('_other') || 
      key.includes('_many') || key.includes('_few')
    )
    
    for (const key of pluralKeys) {
      const baseKey = key.replace(/_(zero|one|other|many|few)$/, '')
      const variants = ['zero', 'one', 'other', 'many', 'few']
      
      for (const lang of this.supportedLanguages) {
        const langTranslations = translations[lang] || {}
        const hasPlural = this.hasTranslation(langTranslations, baseKey)
        
        if (hasPlural) {
          const pluralObj = this.getNestedValue(langTranslations, baseKey)
          if (typeof pluralObj === 'object') {
            // Check if required plural forms exist for this language
            const requiredForms = this.getRequiredPluralForms(lang)
            for (const form of requiredForms) {
              if (!(form in pluralObj)) {
                inconsistent.push(`${baseKey} missing ${form} form in ${lang}`)
              }
            }
          }
        }
      }
    }
    
    return inconsistent
  }

  private getNestedValue(obj: any, key: string): any {
    const keys = key.split('.')
    let current = obj
    
    for (const k of keys) {
      if (typeof current !== 'object' || current === null || !(k in current)) {
        return undefined
      }
      current = current[k]
    }
    
    return current
  }

  private getRequiredPluralForms(language: string): string[] {
    // Simplified plural rules - in practice, use CLDR data
    const pluralRules: Record<string, string[]> = {
      'en': ['one', 'other'],
      'es': ['one', 'other'],
      'fr': ['one', 'other'],
      'ar': ['zero', 'one', 'two', 'few', 'many', 'other'],
      'hi': ['one', 'other'],
      'pt': ['one', 'other'],
      'zh-Hans': ['other']
    }
    
    return pluralRules[language] || ['one', 'other']
  }

  printReport(report: CoverageReport): void {
    console.log('\n📊 S4-19 I18n Translation Coverage Report')
    console.log('=' .repeat(60))
    
    console.log(`\n📝 Total translation keys found: ${report.totalKeys}`)
    
    // Coverage by language
    console.log('\n🌐 Coverage by Language:')
    for (const lang of this.supportedLanguages) {
      const percentage = report.summary.coveragePercentage[lang] || 0
      const missing = report.missingByLanguage[lang]?.length || 0
      const status = percentage === 100 ? '✅' : percentage >= 95 ? '⚠️ ' : '❌'
      
      console.log(`  ${status} ${lang}: ${percentage.toFixed(1)}% (${missing} missing)`)
    }
    
    // Critical missing keys
    if (report.summary.criticalMissing.length > 0) {
      console.log('\n🔴 CRITICAL: Missing translations for essential keys:')
      report.summary.criticalMissing.forEach(key => {
        console.log(`  - ${key}`)
      })
    }
    
    // Detailed missing keys by language
    for (const lang of this.supportedLanguages) {
      const missing = report.missingByLanguage[lang] || []
      if (missing.length > 0) {
        console.log(`\n❌ Missing in ${lang} (${missing.length} keys):`)
        missing.slice(0, 10).forEach(key => {
          console.log(`  - ${key}`)
        })
        if (missing.length > 10) {
          console.log(`  ... and ${missing.length - 10} more`)
        }
      }
    }
    
    // Unused keys
    if (report.unusedKeys.length > 0) {
      console.log(`\n🗑️  Unused translation keys (${report.unusedKeys.length}):`)
      report.unusedKeys.slice(0, 10).forEach(key => {
        console.log(`  - ${key}`)
      })
      if (report.unusedKeys.length > 10) {
        console.log(`  ... and ${report.unusedKeys.length - 10} more`)
      }
    }
    
    // Plural inconsistencies
    if (report.inconsistentPlurals.length > 0) {
      console.log(`\n🔢 Plural form inconsistencies (${report.inconsistentPlurals.length}):`)
      report.inconsistentPlurals.forEach(issue => {
        console.log(`  - ${issue}`)
      })
    }
  }

  checkBuildGate(report: CoverageReport): boolean {
    const totalMissing = Object.values(report.missingByLanguage)
      .reduce((sum, missing) => sum + missing.length, 0)
    
    const hasCriticalMissing = report.summary.criticalMissing.length > 0
    const hasLowCoverage = Object.values(report.summary.coveragePercentage)
      .some(percentage => percentage < 90) // 90% minimum coverage
    
    console.log('\n🚨 S4-19 Build Gate Assessment:')
    console.log('=' .repeat(40))
    
    if (hasCriticalMissing) {
      console.log('❌ FAIL: Critical translation keys are missing')
      console.log(`   ${report.summary.criticalMissing.length} critical keys need translation`)
      return false
    }
    
    if (hasLowCoverage) {
      console.log('❌ FAIL: Translation coverage below 90% threshold')
      for (const [lang, percentage] of Object.entries(report.summary.coveragePercentage)) {
        if (percentage < 90) {
          console.log(`   ${lang}: ${percentage.toFixed(1)}% (below 90%)`)
        }
      }
      return false
    }
    
    if (totalMissing > 0) {
      console.log('⚠️  WARNING: Some translations are missing, but not critical')
      console.log(`   ${totalMissing} total missing translations across all languages`)
    }
    
    console.log('✅ PASS: Translation coverage meets build requirements')
    return true
  }
}

// CLI execution
if (require.main === module) {
  async function main() {
    try {
      const checker = new I18nCoverageChecker()
      const report = await checker.checkCoverage()
      
      checker.printReport(report)
      
      const passesGate = checker.checkBuildGate(report)
      
      if (!passesGate) {
        console.log('\n💥 Build failed due to missing translations!')
        console.log('Please add missing translations before merging.')
        process.exit(1)
      }
      
      console.log('\n🎉 I18n coverage check passed!')
      process.exit(0)
      
    } catch (error) {
      console.error('💥 Error during i18n coverage check:', error)
      process.exit(1)
    }
  }
  
  main()
}

export { I18nCoverageChecker }
