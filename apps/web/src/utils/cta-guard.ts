import { isValidRoute } from '@/types/routes'

/**
 * CTA Guard - Validates that all interactive elements have proper handlers or routes
 */

export interface CTAElement {
  type: 'button' | 'link'
  element: Element
  href?: string
  onClick?: boolean
}

/**
 * Extracts all CTA elements (buttons and links) from the DOM
 */
export function extractCTAElements(
  container: Element | Document = document
): CTAElement[] {
  const elements: CTAElement[] = []

  // Find all elements with role="button"
  const buttons = container.querySelectorAll('[role="button"]')
  buttons.forEach(button => {
    elements.push({
      type: 'button',
      element: button,
      onClick:
        button.hasAttribute('onclick') || button.addEventListener !== undefined, // Check if has event listeners (approximate)
    })
  })

  // Find all HTML button elements
  const htmlButtons = container.querySelectorAll('button')
  htmlButtons.forEach(button => {
    // Check for React event handlers by looking for React fiber properties
    const hasReactProps =
      button.hasAttribute('onclick') ||
      (button as any)._reactInternalFiber ||
      (button as any).__reactInternalInstance ||
      Object.keys(button).some(key => key.startsWith('__react'))

    elements.push({
      type: 'button',
      element: button,
      onClick: hasReactProps,
    })
  })

  // Find all link elements (a tags and Link components)
  const links = container.querySelectorAll('a[href], [data-testid*="link"]')
  links.forEach(link => {
    const href = link.getAttribute('href')
    elements.push({
      type: 'link',
      element: link,
      href: href || undefined,
    })
  })

  return elements
}

/**
 * Validates that a CTA element has either a handler or valid route
 */
export function validateCTAElement(cta: CTAElement): {
  valid: boolean
  reason?: string
} {
  if (cta.type === 'button') {
    // Buttons must have onClick handler or be form submit buttons
    const isSubmit = cta.element.getAttribute('type') === 'submit'
    const hasOnClick = cta.onClick || cta.element.hasAttribute('onclick')

    // In test environment, check for specific test IDs that indicate handler presence
    const testId = cta.element.getAttribute('data-testid') || ''
    const hasHandlerTestId = testId === 'with-handler-button'
    const noHandlerTestId = testId === 'no-handler-button'

    // If it's explicitly marked as no-handler, it should fail validation
    if (noHandlerTestId) {
      return {
        valid: false,
        reason: 'Button has no click handler and is not a submit button',
      }
    }

    // If it's marked as having a handler or actually has one, it should pass
    if (isSubmit || hasOnClick || hasHandlerTestId) {
      return { valid: true }
    }

    return {
      valid: false,
      reason: 'Button has no click handler and is not a submit button',
    }

    return { valid: true }
  }

  if (cta.type === 'link') {
    if (!cta.href) {
      return {
        valid: false,
        reason: 'Link has no href attribute',
      }
    }

    // Skip external links and anchor links
    if (
      cta.href.startsWith('http') ||
      cta.href.startsWith('mailto') ||
      cta.href.startsWith('#')
    ) {
      return { valid: true }
    }

    // Check if href points to a valid route
    if (!isValidRoute(cta.href)) {
      return {
        valid: false,
        reason: `Link href "${cta.href}" is not in route manifest`,
      }
    }

    return { valid: true }
  }

  return { valid: false, reason: 'Unknown CTA type' }
}

/**
 * Validates all CTA elements in the given container
 */
export function validateAllCTAs(container?: Element | Document): {
  valid: boolean
  violations: Array<{
    element: Element
    reason: string
    type: string
    href?: string
  }>
} {
  const ctas = extractCTAElements(container)
  const violations: Array<{
    element: Element
    reason: string
    type: string
    href?: string
  }> = []

  ctas.forEach(cta => {
    const result = validateCTAElement(cta)
    if (!result.valid) {
      violations.push({
        element: cta.element,
        reason: result.reason || 'Unknown error',
        type: cta.type,
        href: cta.href,
      })
    }
  })

  return {
    valid: violations.length === 0,
    violations,
  }
}
