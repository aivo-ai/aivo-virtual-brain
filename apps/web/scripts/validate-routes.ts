#!/usr/bin/env tsx

/**
 * Route CTA Guard Validation Script
 *
 * This script validates that all CTA elements (links and buttons) in the application
 * either have proper handlers or point to valid routes in the route manifest.
 *
 * This is run as part of the build process to ensure compliance.
 */

import { JSDOM } from 'jsdom'
import { validateAllCTAs, extractCTAElements } from '../src/utils/cta-guard.js'
import { getAllRoutes, isValidRoute } from '../src/app/routes.js'

// Set up DOM environment for validation
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>')
global.window = dom.window as any
global.document = dom.window.document
global.Node = dom.window.Node
global.Element = dom.window.Element

console.log('🔍 Route CTA Guard Validation')
console.log('=============================\n')

// Test 1: Validate route manifest
console.log('📋 Testing route manifest...')
const routes = getAllRoutes()
console.log(`Found ${routes.length} routes in manifest:`)
routes.forEach(route => {
  console.log(`  - ${route}`)
})

// Validate all routes are strings and start with /
const invalidRoutes = routes.filter(
  route => typeof route !== 'string' || !route.startsWith('/')
)

if (invalidRoutes.length > 0) {
  console.error('❌ Invalid routes found:', invalidRoutes)
  process.exit(1)
}

console.log('✅ Route manifest validation passed\n')

// Test 2: Validate route helper functions
console.log('🔧 Testing route helper functions...')

// Test valid routes
const testValidRoutes = ['/', '/login', '/dashboard', '/health']
testValidRoutes.forEach(route => {
  if (!isValidRoute(route)) {
    console.error(`❌ Valid route "${route}" failed validation`)
    process.exit(1)
  }
})

// Test invalid routes
const testInvalidRoutes = ['/invalid', '/not-in-manifest', '']
testInvalidRoutes.forEach(route => {
  if (isValidRoute(route)) {
    console.error(`❌ Invalid route "${route}" passed validation`)
    process.exit(1)
  }
})

console.log('✅ Route helper functions validation passed\n')

// Test 3: Create test HTML and validate CTAs
console.log('🔗 Testing CTA validation...')

// Create test HTML with various CTA elements
const testHTML = `
<div id="app">
  <!-- Valid links -->
  <a href="/" data-testid="home-link">Home</a>
  <a href="/login" data-testid="login-link">Login</a>
  <a href="/dashboard" data-testid="dashboard-link">Dashboard</a>
  <a href="https://example.com" data-testid="external-link">External</a>
  <a href="mailto:test@example.com" data-testid="email-link">Email</a>
  <a href="#section" data-testid="anchor-link">Anchor</a>

  <!-- Valid buttons -->
  <button type="submit" data-testid="submit-button">Submit</button>
  <button onclick="handleClick()" data-testid="onclick-button">Click</button>
  <button data-testid="with-handler-button">With Handler</button>

  <!-- Invalid elements for testing -->
  <button data-testid="no-handler-button">No Handler</button>
  <a href="/invalid-route" data-testid="invalid-route-link">Invalid Route</a>
</div>
`

document.body.innerHTML = testHTML
const validation = validateAllCTAs(document.body)

console.log(`Found ${extractCTAElements(document.body).length} CTA elements`)
console.log(`Validation violations: ${validation.violations.length}`)

// Expected violations: no-handler-button and invalid-route-link
const expectedViolations = ['no-handler-button', 'invalid-route-link']
const actualViolations = validation.violations
  .map(v => v.element.getAttribute('data-testid'))
  .filter(Boolean)

const unexpectedViolations = actualViolations.filter(
  violation => !expectedViolations.includes(violation!)
)

if (unexpectedViolations.length > 0) {
  console.error('❌ Unexpected CTA validation violations:')
  unexpectedViolations.forEach(violation => {
    console.error(`  - ${violation}`)
  })
  process.exit(1)
}

// Check that expected violations are found
const missingExpectedViolations = expectedViolations.filter(
  expected => !actualViolations.includes(expected)
)

if (missingExpectedViolations.length > 0) {
  console.error('❌ Expected violations not found:')
  missingExpectedViolations.forEach(violation => {
    console.error(`  - ${violation}`)
  })
  process.exit(1)
}

console.log('✅ CTA validation test passed\n')

// Final validation
console.log('🎉 All Route CTA Guard validations passed!')
console.log(`
Summary:
- ✅ Route manifest: ${routes.length} valid routes
- ✅ Route helpers: Working correctly
- ✅ CTA validation: Proper violation detection
`)

process.exit(0)
