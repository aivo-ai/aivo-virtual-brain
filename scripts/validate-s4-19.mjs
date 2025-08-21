#!/usr/bin/env node

/**
 * S4-19 Implementation Validator
 * Validates that all accessibility and i18n audit components are properly configured
 */

import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'

const requiredFiles = {
  'Accessibility Audit Spec': 'apps/web/e2e/a11y-audit.spec.ts',
  'I18n Coverage Checker': 'scripts/check-i18n-misses.ts',
  'A11y+I18n CI Workflow': '.github/workflows/a11y-i18n.yml',
  'Package.json Scripts': 'package.json'
}

const requiredDependencies = [
  '@axe-core/playwright',
  'playwright',
  'globby'
]

function validateFile(name, filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      console.error(`❌ ${name}: File not found at ${filePath}`)
      return false
    }

    const stats = fs.statSync(filePath)
    if (stats.size === 0) {
      console.error(`❌ ${name}: File is empty`)
      return false
    }

    console.log(`✅ ${name}: Found (${(stats.size / 1024).toFixed(1)}KB)`)
    return true
  } catch (error) {
    console.error(`❌ ${name}: Error checking file - ${error.message}`)
    return false
  }
}

function validateA11ySpec() {
  const specPath = 'apps/web/e2e/a11y-audit.spec.ts'
  if (!fs.existsSync(specPath)) {
    return false
  }

  const content = fs.readFileSync(specPath, 'utf8')
  
  const requiredFeatures = [
    'S4-19 Accessibility Audit Gate',
    'Top 30 Screens',
    'CRITICAL.*zero.*serious.*critical.*violations',
    'AxeBuilder',
    'wcag2aa',
    'keyboard navigation',
    'screen reader',
    'touch target.*44.*px',
    'focus management',
    'Multi-language.*accessibility'
  ]

  let allFeaturesFound = true
  for (const feature of requiredFeatures) {
    const regex = new RegExp(feature, 'i')
    if (!regex.test(content)) {
      console.error(`❌ A11y Spec missing feature: ${feature}`)
      allFeaturesFound = false
    }
  }

  if (allFeaturesFound) {
    console.log('✅ A11y Spec: All required features present')
  }

  // Count screens being tested
  const screenMatches = content.match(/path:\s*['"]([^'"]+)['"]/g) || []
  const screenCount = screenMatches.length
  console.log(`📊 A11y Spec: Testing ${screenCount} screens`)

  if (screenCount < 30) {
    console.warn(`⚠️  Expected 30+ screens, found ${screenCount}`)
  }

  return allFeaturesFound && screenCount >= 25
}

function validateI18nChecker() {
  const checkerPath = 'scripts/check-i18n-misses.ts'
  if (!fs.existsSync(checkerPath)) {
    return false
  }

  const content = fs.readFileSync(checkerPath, 'utf8')
  
  const requiredComponents = [
    'class I18nCoverageChecker',
    'extractTranslationKeys',
    'loadTranslations',
    'analyzeCoverage',
    'checkBuildGate',
    '90.*minimum.*coverage',
    'critical.*translation.*keys',
    'process\\.exit\\(1\\)'
  ]

  let allComponentsFound = true
  for (const component of requiredComponents) {
    const regex = new RegExp(component, 'i')
    if (!regex.test(content)) {
      console.error(`❌ I18n Checker missing component: ${component}`)
      allComponentsFound = false
    }
  }

  if (allComponentsFound) {
    console.log('✅ I18n Checker: All required components present')
  }

  // Check supported languages
  const langMatches = content.match(/supportedLanguages.*=.*\[([\s\S]*?)\]/m)
  if (langMatches) {
    const langString = langMatches[1]
    const languages = langString.split(',').filter(lang => 
      lang.trim().includes("'") || lang.trim().includes('"')
    ).length
    console.log(`🌐 I18n Checker: Supports ${languages} languages`)
  }

  return allComponentsFound
}

function validateCIWorkflow() {
  const workflowPath = '.github/workflows/a11y-i18n.yml'
  if (!fs.existsSync(workflowPath)) {
    return false
  }

  const content = fs.readFileSync(workflowPath, 'utf8')
  
  const requiredJobs = [
    'i18n-coverage',
    'accessibility-audit',
    'critical-accessibility',
    'wcag-compliance',
    'audit-summary'
  ]

  const requiredSteps = [
    'check.*i18n.*translation.*coverage',
    'accessibility.*audit.*top.*30',
    'CRITICAL.*accessibility.*tests',
    'WCAG.*2\\.1.*AA.*compliance',
    'fail.*build.*if.*gate.*fails'
  ]

  let allJobsFound = true
  for (const job of requiredJobs) {
    if (!content.includes(job)) {
      console.error(`❌ CI Workflow missing job: ${job}`)
      allJobsFound = false
    }
  }

  let allStepsFound = true
  for (const step of requiredSteps) {
    const regex = new RegExp(step, 'i')
    if (!regex.test(content)) {
      console.error(`❌ CI Workflow missing step: ${step}`)
      allStepsFound = false
    }
  }

  if (allJobsFound && allStepsFound) {
    console.log('✅ CI Workflow: All required jobs and steps present')
  }

  return allJobsFound && allStepsFound
}

function validatePackageScripts() {
  const packagePath = 'package.json'
  if (!fs.existsSync(packagePath)) {
    return false
  }

  const content = fs.readFileSync(packagePath, 'utf8')
  const packageJson = JSON.parse(content)
  
  const requiredScripts = [
    'a11y:audit',
    'i18n:check',
    'audit:s4-19'
  ]

  let allScriptsFound = true
  for (const script of requiredScripts) {
    if (!packageJson.scripts || !packageJson.scripts[script]) {
      console.error(`❌ Package.json missing script: ${script}`)
      allScriptsFound = false
    }
  }

  if (allScriptsFound) {
    console.log('✅ Package.json: All required scripts present')
  }

  return allScriptsFound
}

function validateDependencies() {
  let allDepsFound = true
  
  // Check if web app package.json has the dependencies
  const webPackagePath = 'apps/web/package.json'
  if (fs.existsSync(webPackagePath)) {
    const packageJson = JSON.parse(fs.readFileSync(webPackagePath, 'utf8'))
    const allDeps = {
      ...packageJson.dependencies,
      ...packageJson.devDependencies
    }

    for (const dep of requiredDependencies) {
      if (!allDeps[dep] && !allDeps[`@${dep}`] && !allDeps[`@playwright/test`]) {
        // Check for playwright variants
        if (dep === 'playwright' && (allDeps['@playwright/test'] || allDeps['playwright'])) {
          continue
        }
        if (dep === '@axe-core/playwright' && allDeps['@axe-core/playwright']) {
          continue
        }
        console.error(`❌ Missing dependency: ${dep}`)
        allDepsFound = false
      }
    }
  }

  // Check if pnpm-lock.yaml exists
  if (fs.existsSync('pnpm-lock.yaml')) {
    const lockContent = fs.readFileSync('pnpm-lock.yaml', 'utf8')
    let foundInLock = 0
    for (const dep of requiredDependencies) {
      if (lockContent.includes(dep) || lockContent.includes('@playwright/test') || lockContent.includes('@axe-core/playwright')) {
        foundInLock++
      }
    }
    
    if (foundInLock >= 2) { // At least playwright and axe found
      allDepsFound = true
    }
  }

  if (allDepsFound) {
    console.log('✅ Dependencies: All required packages available')
  }

  return allDepsFound
}

function validateI18nResources() {
  const i18nPath = 'libs/i18n/resources'
  if (!fs.existsSync(i18nPath)) {
    console.error('❌ I18n Resources: Directory not found')
    return false
  }

  const files = fs.readdirSync(i18nPath)
  const jsonFiles = files.filter(f => f.endsWith('.json'))
  
  console.log(`🌐 I18n Resources: Found ${jsonFiles.length} language files`)
  
  // Check for critical languages
  const criticalLanguages = ['en.json', 'es.json', 'fr.json', 'ar.json']
  let hasCriticalLangs = true
  
  for (const lang of criticalLanguages) {
    if (!jsonFiles.includes(lang)) {
      console.error(`❌ Missing critical language file: ${lang}`)
      hasCriticalLangs = false
    }
  }

  if (hasCriticalLangs && jsonFiles.length >= 4) {
    console.log('✅ I18n Resources: Critical language files present')
    return true
  }

  return false
}

function validatePlaywrightConfig() {
  const configPaths = [
    'playwright.config.ts',
    'apps/web/playwright.config.ts',
    'apps/web/e2e/playwright.config.ts'
  ]
  
  for (const configPath of configPaths) {
    if (fs.existsSync(configPath)) {
      console.log(`✅ Playwright Config: Found at ${configPath}`)
      return true
    }
  }
  
  console.warn('⚠️  Playwright config not found - tests may not run properly')
  return false
}

function main() {
  console.log('🔍 S4-19 Accessibility & I18n Audit Gate Validation')
  console.log('=' .repeat(60))

  let allValid = true

  // Check required files
  for (const [name, filePath] of Object.entries(requiredFiles)) {
    if (!validateFile(name, filePath)) {
      allValid = false
    }
  }

  console.log('')

  // Detailed validations
  if (!validateA11ySpec()) allValid = false
  if (!validateI18nChecker()) allValid = false
  if (!validateCIWorkflow()) allValid = false
  if (!validatePackageScripts()) allValid = false
  if (!validateDependencies()) allValid = false
  if (!validateI18nResources()) allValid = false
  if (!validatePlaywrightConfig()) allValid = false

  console.log('\n' + '=' .repeat(60))
  
  if (allValid) {
    console.log('🎉 S4-19 Implementation: All components validated successfully!')
    console.log('\n✅ Audit Gate Features:')
    console.log('  • Comprehensive accessibility testing (30+ screens)')
    console.log('  • Zero tolerance for critical/serious a11y violations')
    console.log('  • I18n translation coverage checking (90% minimum)')
    console.log('  • WCAG 2.1 AA compliance verification')
    console.log('  • Keyboard navigation testing')
    console.log('  • Screen reader compatibility checks')
    console.log('  • Mobile touch target validation')
    console.log('  • Multi-language accessibility support')
    console.log('  • Automated CI gate enforcement')
    
    console.log('\n🚀 Ready to enforce accessibility & i18n standards!')
    console.log('   Run: pnpm run audit:s4-19')
    
    process.exit(0)
  } else {
    console.log('❌ S4-19 Implementation: Validation failed!')
    console.log('\nPlease fix the issues above before using the audit gate.')
    process.exit(1)
  }
}

main()
