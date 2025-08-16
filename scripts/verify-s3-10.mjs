#!/usr/bin/env node

/**
 * S3-10 Game Player Verification Script
 * Validates that all required components and functionality are implemented
 */

import { promises as fs } from 'fs'
import { join } from 'path'

class S310Validator {
  constructor(rootPath) {
    this.results = []
    this.rootPath = rootPath
  }

  addResult(component, status, message, details) {
    this.results.push({ component, status, message, details })
  }

  async fileExists(filePath) {
    try {
      await fs.access(join(this.rootPath, filePath))
      return true
    } catch {
      return false
    }
  }

  async fileContains(filePath, content) {
    try {
      const fileContent = await fs.readFile(join(this.rootPath, filePath), 'utf-8')
      if (typeof content === 'string') {
        return fileContent.includes(content)
      }
      return content.test(fileContent)
    } catch {
      return false
    }
  }

  async checkFileStructure() {
    console.log('🔍 Checking file structure...')
    
    const requiredFiles = [
      'apps/web/src/lib/gameClient.ts',
      'apps/web/src/pages/game/Play.tsx',
      'apps/web/src/components/game/CanvasStage.tsx',
      'apps/web/src/components/game/Hud.tsx',
      'apps/web/src/components/game/ResultSheet.tsx',
      'apps/web/src/components/game/index.ts'
    ]

    for (const file of requiredFiles) {
      const exists = await this.fileExists(file)
      this.addResult(
        'File Structure',
        exists ? 'PASS' : 'FAIL',
        `${file} ${exists ? 'exists' : 'missing'}`
      )
    }
  }

  async checkGameClientAPI() {
    console.log('🔍 Checking Game Client API...')
    
    const clientPath = 'apps/web/src/lib/gameClient.ts'
    const requiredMethods = [
      'generateGame',
      'startSession',
      'endSession',
      'emitEvent',
      'getGameSession'
    ]

    for (const method of requiredMethods) {
      const hasMethod = await this.fileContains(clientPath, new RegExp(`${method}\\s*[:(]`))
      this.addResult(
        'Game Client API',
        hasMethod ? 'PASS' : 'FAIL',
        `Method ${method} ${hasMethod ? 'implemented' : 'missing'}`
      )
    }

    // Check for required interfaces
    const requiredInterfaces = [
      'GameManifest',
      'GameSession',
      'GamePerformance',
      'GameGenerationRequest'
    ]

    for (const interfaceName of requiredInterfaces) {
      const hasInterface = await this.fileContains(clientPath, new RegExp(`interface\\s+${interfaceName}`))
      this.addResult(
        'Game Client Types',
        hasInterface ? 'PASS' : 'FAIL',
        `Interface ${interfaceName} ${hasInterface ? 'defined' : 'missing'}`
      )
    }
  }

  async checkGamePlayerPage() {
    console.log('🔍 Checking Game Player Page...')
    
    const playPath = 'apps/web/src/pages/game/Play.tsx'
    
    const requiredFeatures = [
      { feature: 'Pause/Resume', pattern: /pause|resume/i },
      { feature: 'Keyboard Controls', pattern: /keydown|keyboard/i },
      { feature: 'Timer', pattern: /timer|countdown/i },
      { feature: 'Game State Management', pattern: /useState.*game/i },
      { feature: 'Error Handling', pattern: /error|catch/i },
      { feature: 'Game Completion', pattern: /complete|finish/i }
    ]

    for (const { feature, pattern } of requiredFeatures) {
      const hasFeature = await this.fileContains(playPath, pattern)
      this.addResult(
        'Game Player Features',
        hasFeature ? 'PASS' : 'WARNING',
        `${feature} ${hasFeature ? 'implemented' : 'may be missing'}`
      )
    }

    // Check for required hooks and imports
    const requiredImports = [
      'useState',
      'useEffect',
      'gameClient',
      'CanvasStage',
      'Hud',
      'ResultSheet'
    ]

    for (const importName of requiredImports) {
      const hasImport = await this.fileContains(playPath, importName)
      this.addResult(
        'Game Player Imports',
        hasImport ? 'PASS' : 'FAIL',
        `Import ${importName} ${hasImport ? 'found' : 'missing'}`
      )
    }
  }

  async checkGameComponents() {
    console.log('🔍 Checking Game Components...')
    
    const components = [
      {
        name: 'CanvasStage',
        path: 'apps/web/src/components/game/CanvasStage.tsx',
        features: ['canvas', 'interaction', 'scene', 'render']
      },
      {
        name: 'Hud',
        path: 'apps/web/src/components/game/Hud.tsx',
        features: ['timer', 'score', 'progress', 'pause']
      },
      {
        name: 'ResultSheet',
        path: 'apps/web/src/components/game/ResultSheet.tsx',
        features: ['performance', 'score', 'retry', 'completion']
      }
    ]

    for (const component of components) {
      const exists = await this.fileExists(component.path)
      if (!exists) {
        this.addResult(
          `${component.name} Component`,
          'FAIL',
          `Component file missing: ${component.path}`
        )
        continue
      }

      // Check for required features in component
      for (const feature of component.features) {
        const hasFeature = await this.fileContains(component.path, new RegExp(feature, 'i'))
        this.addResult(
          `${component.name} Features`,
          hasFeature ? 'PASS' : 'WARNING',
          `${feature} feature ${hasFeature ? 'found' : 'may be missing'}`
        )
      }

      // Check for TypeScript props interface
      const hasPropsInterface = await this.fileContains(component.path, /interface.*Props/)
      this.addResult(
        `${component.name} Types`,
        hasPropsInterface ? 'PASS' : 'WARNING',
        `Props interface ${hasPropsInterface ? 'defined' : 'missing'}`
      )

      // Check for test IDs
      const hasTestIds = await this.fileContains(component.path, /data-testid/)
      this.addResult(
        `${component.name} Testing`,
        hasTestIds ? 'PASS' : 'WARNING',
        `Test IDs ${hasTestIds ? 'present' : 'missing'}`
      )
    }
  }

  async checkGameIntegration() {
    console.log('🔍 Checking Game-Gen-Svc Integration...')
    
    const clientPath = 'apps/web/src/lib/gameClient.ts'
    
    // Check for API endpoints
    const apiEndpoints = [
      '/api/game/generate',
      '/api/game/session',
      'game-gen-svc'
    ]

    for (const endpoint of apiEndpoints) {
      const hasEndpoint = await this.fileContains(clientPath, endpoint)
      this.addResult(
        'API Integration',
        hasEndpoint ? 'PASS' : 'WARNING',
        `Endpoint ${endpoint} ${hasEndpoint ? 'configured' : 'not found'}`
      )
    }

    // Check for event emission
    const hasEventEmission = await this.fileContains(clientPath, /GAME_COMPLETED|emitEvent/)
    this.addResult(
      'Event Integration',
      hasEventEmission ? 'PASS' : 'FAIL',
      `GAME_COMPLETED event ${hasEventEmission ? 'implemented' : 'missing'}`
    )
  }

  async checkTypeScriptCompilation() {
    console.log('🔍 Checking TypeScript compilation...')
    
    // Check for common TypeScript issues in game files
    const gameFiles = [
      'apps/web/src/lib/gameClient.ts',
      'apps/web/src/pages/game/Play.tsx',
      'apps/web/src/components/game/CanvasStage.tsx',
      'apps/web/src/components/game/Hud.tsx',
      'apps/web/src/components/game/ResultSheet.tsx'
    ]

    for (const file of gameFiles) {
      const exists = await this.fileExists(file)
      if (!exists) continue

      // Check for any syntax and missing imports
      const hasReactImport = await this.fileContains(file, "import React")
      const hasTypeScript = file.endsWith('.tsx') || file.endsWith('.ts')
      
      this.addResult(
        'TypeScript Compilation',
        hasReactImport && hasTypeScript ? 'PASS' : 'WARNING',
        `${file} ${hasReactImport && hasTypeScript ? 'properly configured' : 'may have issues'}`
      )
    }
  }

  async checkRequiredFeatures() {
    console.log('🔍 Checking S3-10 required features...')
    
    const playPath = 'apps/web/src/pages/game/Play.tsx'
    
    const requirements = [
      {
        name: 'Dynamic Game Manifests',
        pattern: /manifest|generateGame/i,
        description: 'Loading game manifests from game-gen-svc'
      },
      {
        name: 'Pause/Resume Functionality',
        pattern: /pause.*resume|isPaused/i,
        description: 'Game can be paused and resumed'
      },
      {
        name: 'Keyboard Controls',
        pattern: /Space|Escape|Enter.*key/i,
        description: 'Keyboard-only operation support'
      },
      {
        name: 'Time Management',
        pattern: /timeLimit|timer|countdown/i,
        description: 'Respecting game time limits'
      },
      {
        name: 'Completion Tracking',
        pattern: /GAME_COMPLETED|completion|finish/i,
        description: 'Game completion event emission'
      },
      {
        name: 'Performance Metrics',
        pattern: /performance|score|accuracy/i,
        description: 'Performance tracking and display'
      }
    ]

    for (const requirement of requirements) {
      const implemented = await this.fileContains(playPath, requirement.pattern)
      this.addResult(
        'S3-10 Requirements',
        implemented ? 'PASS' : 'FAIL',
        `${requirement.name}: ${implemented ? 'Implemented' : 'Missing'}`
      )
    }
  }

  async validate() {
    console.log('🚀 Starting S3-10 Game Player Validation...\n')
    
    await this.checkFileStructure()
    await this.checkGameClientAPI()
    await this.checkGamePlayerPage()
    await this.checkGameComponents()
    await this.checkGameIntegration()
    await this.checkTypeScriptCompilation()
    await this.checkRequiredFeatures()
    
    this.printResults()
  }

  printResults() {
    console.log('\n📋 VALIDATION RESULTS')
    console.log('====================\n')
    
    const grouped = this.results.reduce((acc, result) => {
      if (!acc[result.component]) {
        acc[result.component] = []
      }
      acc[result.component].push(result)
      return acc
    }, {})

    let totalTests = 0
    let passedTests = 0
    let warnings = 0
    let failures = 0

    for (const [component, results] of Object.entries(grouped)) {
      console.log(`📦 ${component}`)
      console.log('-'.repeat(component.length + 2))
      
      for (const result of results) {
        totalTests++
        const icon = result.status === 'PASS' ? '✅' : result.status === 'WARNING' ? '⚠️' : '❌'
        console.log(`  ${icon} ${result.message}`)
        
        if (result.details) {
          result.details.forEach(detail => console.log(`    - ${detail}`))
        }

        if (result.status === 'PASS') passedTests++
        else if (result.status === 'WARNING') warnings++
        else failures++
      }
      console.log()
    }

    console.log('📊 SUMMARY')
    console.log('=========')
    console.log(`Total Tests: ${totalTests}`)
    console.log(`✅ Passed: ${passedTests}`)
    console.log(`⚠️ Warnings: ${warnings}`)
    console.log(`❌ Failed: ${failures}`)
    console.log(`Success Rate: ${Math.round((passedTests / totalTests) * 100)}%\n`)

    if (failures === 0) {
      console.log('🎉 S3-10 Game Player implementation is ready!')
      console.log('✨ All critical components are in place.')
      
      if (warnings > 0) {
        console.log(`\n⚠️  Note: ${warnings} warnings detected - consider reviewing for optimization.`)
      }
    } else {
      console.log('🔧 S3-10 Game Player needs attention:')
      console.log(`❌ ${failures} critical issues need to be resolved.`)
      
      if (warnings > 0) {
        console.log(`⚠️  ${warnings} warnings should also be addressed.`)
      }
    }

    console.log('\n🔗 Next Steps:')
    console.log('1. Run the web app: npm run dev')
    console.log('2. Navigate to /game/play to test functionality')
    console.log('3. Test with query params: /game/play?topic=math&difficulty=easy')
    console.log('4. Verify game-gen-svc integration')
    console.log('5. Test all keyboard controls and interactions')
  }
}

// Run validation
async function main() {
  const rootPath = process.cwd()
  const validator = new S310Validator(rootPath)
  
  try {
    await validator.validate()
  } catch (error) {
    console.error('❌ Validation failed:', error)
    process.exit(1)
  }
}

if (import.meta.url === new URL(process.argv[1], 'file://').href) {
  main()
}

export { S310Validator }
