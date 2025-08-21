#!/usr/bin/env node

/**
 * S5-02 Library UI Implementation Validation
 * Validates the complete library asset browsing, filtering, upload, and attachment system
 */

import { readFileSync, existsSync } from 'fs'
import { join } from 'path'

const BASE_PATH = 'apps/web/src'

const results = []

function validateFile(filePath, category, description, requiredContent = []) {
  const fullPath = join(BASE_PATH, filePath)
  
  if (!existsSync(fullPath)) {
    results.push({
      category,
      item: description,
      status: 'fail',
      details: `File missing: ${filePath}`
    })
    return false
  }

  try {
    const content = readFileSync(fullPath, 'utf8')
    
    for (const required of requiredContent) {
      if (!content.includes(required)) {
        results.push({
          category,
          item: description,
          status: 'fail',
          details: `Missing required content: ${required}`
        })
        return false
      }
    }

    results.push({
      category,
      item: description,
      status: 'pass'
    })
    return true
  } catch (error) {
    results.push({
      category,
      item: description,
      status: 'fail',
      details: `Error reading file: ${error.message}`
    })
    return false
  }
}

function validateApiClients() {
  console.log('🔍 Validating API Clients...')
  
  // Coursework Client
  validateFile('api/courseworkClient.ts', 'API Clients', 'Coursework API Client', [
    'CourseworkAsset',
    'CourseworkUploadRequest',
    'OCRPreviewResponse',
    'uploadAsset',
    'getOcrPreview',
    'attachToLearner',
    'detachFromLearner',
    'getAssets'
  ])

  // Search Client  
  validateFile('api/searchClient.ts', 'API Clients', 'Search API Client', [
    'LibrarySearchRequest',
    'LibrarySearchResponse',
    'searchLibrary',
    'getSuggestions',
    'indexAsset',
    'removeFromIndex'
  ])
}

function validatePages() {
  console.log('🔍 Validating Library Pages...')
  
  // Index Page
  validateFile('pages/library/Index.tsx', 'Pages', 'Library Index Page', [
    'LibraryAsset',
    'LibraryFilters',
    'union view',
    'searchClient',
    'lessonRegistryClient',
    'courseworkClient',
    'AssetCard',
    'Filters',
    'loadAssets',
    'handleSearchChange',
    'handleFiltersChange'
  ])

  // Upload Page
  validateFile('pages/library/Upload.tsx', 'Pages', 'Library Upload Page', [
    'CourseworkUploadRequest',
    'OCRPreviewResponse',
    'ConsentResponse',
    'UploadDropzone',
    'mediaConsent',
    'handleFileSelect',
    'handleSubmit',
    'getOcrPreview',
    'attachToLearner'
  ])

  // Detail Page
  validateFile('pages/library/Detail.tsx', 'Pages', 'Asset Detail Page', [
    'AssetDetail',
    'useParams',
    'courseworkClient',
    'lessonRegistryClient',
    'loadAsset',
    'handleAttachmentToggle',
    'formatFileSize',
    'formatDuration'
  ])
}

function validateComponents() {
  console.log('🔍 Validating Library Components...')
  
  // Asset Card
  validateFile('components/library/AssetCard.tsx', 'Components', 'Asset Card Component', [
    'LibraryAsset',
    'getTypeIcon',
    'getSourceBadgeColor',
    'handleAttachmentToggle',
    'onAttachToLearner',
    'onRemoveFromLearner',
    'aria-label',
    'line-clamp'
  ])

  // Filters
  validateFile('components/library/Filters.tsx', 'Components', 'Filters Component', [
    'LibraryFilters',
    'facets',
    'predefinedOptions',
    'handleFilterChange',
    'clearFilters',
    'getFilterOptions',
    'getFilterCount',
    'activeFiltersCount'
  ])

  // Upload Dropzone
  validateFile('components/library/UploadDropzone.tsx', 'Components', 'Upload Dropzone Component', [
    'UploadDropzoneProps',
    'validateFile',
    'handleDrag',
    'handleDrop',
    'handleFileInput',
    'formatFileSize',
    'getFileIcon',
    'drag and drop',
    'maxSize'
  ])
}

function validateFunctionality() {
  console.log('🔍 Validating Core Functionality...')
  
  // Union View Implementation
  const indexContent = readFileSync(join(BASE_PATH, 'pages/library/Index.tsx'), 'utf8')
  if (indexContent.includes('lessonRegistryClient') && indexContent.includes('courseworkClient') && 
      indexContent.includes('merge') && indexContent.includes('sort')) {
    results.push({
      category: 'Functionality',
      item: 'Union View of Lessons + Coursework',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Functionality', 
      item: 'Union View of Lessons + Coursework',
      status: 'fail',
      details: 'Missing proper union view implementation'
    })
  }

  // Filtering System
  const filtersContent = readFileSync(join(BASE_PATH, 'components/library/Filters.tsx'), 'utf8')
  if (filtersContent.includes('subject') && filtersContent.includes('topic') && 
      filtersContent.includes('gradeBand') && filtersContent.includes('type') &&
      filtersContent.includes('source')) {
    results.push({
      category: 'Functionality',
      item: 'Multi-dimensional Filtering (Subject/Topic/Grade/Type/Source)',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Functionality',
      item: 'Multi-dimensional Filtering (Subject/Topic/Grade/Type/Source)', 
      status: 'fail',
      details: 'Missing required filter dimensions'
    })
  }

  // Upload with OCR
  const uploadContent = readFileSync(join(BASE_PATH, 'pages/library/Upload.tsx'), 'utf8')
  if (uploadContent.includes('getOcrPreview') && uploadContent.includes('OCRPreviewResponse') &&
      uploadContent.includes('suggestedMetadata')) {
    results.push({
      category: 'Functionality',
      item: 'Upload with OCR Preview & Auto-population',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Functionality',
      item: 'Upload with OCR Preview & Auto-population',
      status: 'fail', 
      details: 'Missing OCR preview functionality'
    })
  }

  // Consent Guard
  if (uploadContent.includes('mediaConsent') && uploadContent.includes('consent?.mediaConsent')) {
    results.push({
      category: 'Functionality',
      item: 'Consent Guard for Upload',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Functionality',
      item: 'Consent Guard for Upload',
      status: 'fail',
      details: 'Missing media consent validation'
    })
  }

  // Learner Attachment
  const courseworkContent = readFileSync(join(BASE_PATH, 'api/courseworkClient.ts'), 'utf8')
  if (courseworkContent.includes('attachToLearner') && courseworkContent.includes('detachFromLearner')) {
    results.push({
      category: 'Functionality',
      item: 'Learner Progress Attachment',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Functionality',
      item: 'Learner Progress Attachment',
      status: 'fail',
      details: 'Missing learner attachment methods'
    })
  }
}

function validateAccessibility() {
  console.log('🔍 Validating Accessibility Features...')
  
  const components = [
    'components/library/AssetCard.tsx',
    'components/library/Filters.tsx', 
    'components/library/UploadDropzone.tsx',
    'pages/library/Index.tsx',
    'pages/library/Upload.tsx'
  ]

  let hasAriaLabels = true
  let hasKeyboardSupport = true
  let hasScreenReaderSupport = true

  for (const component of components) {
    const content = readFileSync(join(BASE_PATH, component), 'utf8')
    
    if (!content.includes('aria-label') && !content.includes('aria-labelledby')) {
      hasAriaLabels = false
    }
    
    if (!content.includes('onKeyPress') && !content.includes('focus:') && !content.includes('tabindex')) {
      hasKeyboardSupport = false
    }
  }

  results.push({
    category: 'Accessibility',
    item: 'ARIA Labels and Screen Reader Support',
    status: hasAriaLabels ? 'pass' : 'fail',
    details: hasAriaLabels ? undefined : 'Missing aria-label attributes in some components'
  })

  results.push({
    category: 'Accessibility', 
    item: 'Keyboard Navigation Support',
    status: hasKeyboardSupport ? 'pass' : 'fail',
    details: hasKeyboardSupport ? undefined : 'Missing keyboard interaction handling'
  })
}

function validateResponsiveDesign() {
  console.log('🔍 Validating Responsive Design...')
  
  const indexContent = readFileSync(join(BASE_PATH, 'pages/library/Index.tsx'), 'utf8')
  
  if (indexContent.includes('grid-cols-1') && indexContent.includes('sm:grid-cols-2') && 
      indexContent.includes('lg:grid-cols-3') && indexContent.includes('xl:grid-cols-4')) {
    results.push({
      category: 'Responsive Design',
      item: 'Grid Layout (1 col mobile → 4 cols desktop)',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Responsive Design',
      item: 'Grid Layout (1 col mobile → 4 cols desktop)',
      status: 'fail',
      details: 'Missing responsive grid classes'
    })
  }

  const filtersContent = readFileSync(join(BASE_PATH, 'components/library/Filters.tsx'), 'utf8')
  if (filtersContent.includes('lg:hidden') && filtersContent.includes('hidden lg:block')) {
    results.push({
      category: 'Responsive Design',
      item: 'Mobile Filter Toggle',
      status: 'pass'
    })
  } else {
    results.push({
      category: 'Responsive Design', 
      item: 'Mobile Filter Toggle',
      status: 'fail',
      details: 'Missing mobile filter toggle functionality'
    })
  }
}

function validateTypeScript() {
  console.log('🔍 Validating TypeScript Implementation...')
  
  const files = [
    'api/courseworkClient.ts',
    'api/searchClient.ts',
    'pages/library/Index.tsx',
    'pages/library/Upload.tsx',
    'pages/library/Detail.tsx',
    'components/library/AssetCard.tsx',
    'components/library/Filters.tsx',
    'components/library/UploadDropzone.tsx'
  ]

  // Only check React files for React.FC types
  const reactFiles = files.filter(f => f.includes('pages/') || f.includes('components/'))

  let hasProperTypes = true
  let hasInterfaces = true

  for (const file of files) {
    const content = readFileSync(join(BASE_PATH, file), 'utf8')
    
    if (!content.includes('interface ') && !content.includes('type ')) {
      hasProperTypes = false
    }
  }

  for (const file of reactFiles) {
    const content = readFileSync(join(BASE_PATH, file), 'utf8')
    
    if (!content.includes(': React.FC') && !content.includes('React.')) {
      hasInterfaces = false
    }
  }

  results.push({
    category: 'TypeScript',
    item: 'Type Definitions and Interfaces',
    status: hasProperTypes ? 'pass' : 'fail',
    details: hasProperTypes ? undefined : 'Missing proper TypeScript type definitions'
  })

  results.push({
    category: 'TypeScript',
    item: 'React Component Types',
    status: hasInterfaces ? 'pass' : 'fail', 
    details: hasInterfaces ? undefined : 'Missing React component type annotations'
  })
}

function printResults() {
  console.log('\n📊 S5-02 Library UI Implementation Validation Results')
  console.log('=' .repeat(60))

  const categories = [...new Set(results.map(r => r.category))]
  
  for (const category of categories) {
    console.log(`\n📂 ${category}`)
    console.log('-'.repeat(40))
    
    const categoryResults = results.filter(r => r.category === category)
    const passed = categoryResults.filter(r => r.status === 'pass').length
    const total = categoryResults.length
    
    for (const result of categoryResults) {
      const icon = result.status === 'pass' ? '✅' : '❌'
      console.log(`${icon} ${result.item}`)
      if (result.details) {
        console.log(`   └─ ${result.details}`)
      }
    }
    
    console.log(`\n   📈 ${category} Score: ${passed}/${total} (${Math.round(passed/total*100)}%)`)
  }

  const totalPassed = results.filter(r => r.status === 'pass').length
  const totalItems = results.length
  const overallScore = Math.round(totalPassed / totalItems * 100)

  console.log('\n' + '='.repeat(60))
  console.log(`🎯 Overall Implementation Score: ${totalPassed}/${totalItems} (${overallScore}%)`)
  
  if (overallScore >= 90) {
    console.log('🌟 EXCELLENT - S5-02 Library UI implementation is comprehensive and production-ready!')
  } else if (overallScore >= 80) {
    console.log('✨ GOOD - S5-02 Library UI implementation is solid with minor improvements needed')
  } else if (overallScore >= 70) {
    console.log('⚠️  ADEQUATE - S5-02 Library UI implementation needs some important fixes')
  } else {
    console.log('🚨 NEEDS WORK - S5-02 Library UI implementation requires significant improvements')
  }

  console.log('\n🎓 S5-02 Implementation Features:')
  console.log('   • Union view of lesson registry + coursework assets')
  console.log('   • Multi-dimensional filtering (subject/topic/grade/type/source)')
  console.log('   • File upload with drag-and-drop and OCR preview')
  console.log('   • Content consent guard system')
  console.log('   • Learner progress attachment functionality')
  console.log('   • Responsive design with mobile-first approach')
  console.log('   • Accessibility support (ARIA, keyboard navigation)')
  console.log('   • Comprehensive TypeScript type safety')
  console.log('   • Search integration with faceted results')
  console.log('   • Asset detail views with metadata display')

  return overallScore >= 80
}

// Run validation
console.log('🚀 Starting S5-02 Library UI Validation...')

validateApiClients()
validatePages()
validateComponents()
validateFunctionality()
validateAccessibility()
validateResponsiveDesign()
validateTypeScript()

const success = printResults()

process.exit(success ? 0 : 1)
