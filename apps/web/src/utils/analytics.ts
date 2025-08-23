/**
 * Analytics utility for tracking user interactions and page views
 */

export interface AnalyticsEvent {
  event: string
  properties?: Record<string, unknown>
}

export interface PageViewEvent {
  page: string
  title?: string
  path: string
  referrer?: string
  user_id?: string
  session_id?: string
  timestamp: number
}

export interface NavigationEvent {
  from: string
  to: string
  method: 'link' | 'programmatic' | 'back' | 'forward'
  user_id?: string
  session_id?: string
  timestamp: number
}

export interface UserContext {
  user_id?: string
  role?: 'parent' | 'teacher' | 'district_admin' | 'staff' | 'system_admin'
  dash_context?: 'parent' | 'teacher' | 'district'
  session_id?: string
}

class Analytics {
  private context: UserContext = {}
  private isEnabled = true
  private isDebug = import.meta.env.DEV

  /**
   * Initialize analytics with user context
   */
  initialize(context: UserContext) {
    this.context = { ...context }
    if (this.isDebug) {
      console.log('[Analytics] Initialized with context:', this.context)
    }
  }

  /**
   * Update user context
   */
  updateContext(updates: Partial<UserContext>) {
    this.context = { ...this.context, ...updates }
    if (this.isDebug) {
      console.log('[Analytics] Context updated:', updates)
    }
  }

  /**
   * Enable or disable analytics tracking
   */
  setEnabled(enabled: boolean) {
    this.isEnabled = enabled
    if (this.isDebug) {
      console.log(`[Analytics] ${enabled ? 'Enabled' : 'Disabled'}`)
    }
  }

  /**
   * Track a page view
   */
  trackPageView(page: string, additionalData?: Partial<PageViewEvent>) {
    if (!this.isEnabled) return

    const event: PageViewEvent = {
      page,
      title: document.title,
      path: window.location.pathname,
      referrer: document.referrer,
      ...this.context,
      timestamp: Date.now(),
      ...additionalData,
    }

    this.sendEvent('page_view', event)
  }

  /**
   * Track navigation between pages
   */
  trackNavigation(
    from: string,
    to: string,
    method: NavigationEvent['method'] = 'link'
  ) {
    if (!this.isEnabled) return

    const event: NavigationEvent = {
      from,
      to,
      method,
      ...this.context,
      timestamp: Date.now(),
    }

    this.sendEvent('navigation', event)
  }

  /**
   * Track custom events
   */
  track(eventName: string, properties?: Record<string, unknown>) {
    if (!this.isEnabled) return

    const event = {
      event: eventName,
      properties: {
        ...properties,
        ...this.context,
        timestamp: Date.now(),
      },
    }

    this.sendEvent(eventName, event)
  }

  /**
   * Track user interactions
   */
  trackInteraction(
    element: string,
    action: string,
    properties?: Record<string, unknown>
  ) {
    this.track('interaction', {
      element,
      action,
      ...properties,
    })
  }

  /**
   * Track route guard events
   */
  trackRouteGuard(
    route: string,
    allowed: boolean,
    reason?: string,
    userRole?: string
  ) {
    this.track('route_guard', {
      route,
      allowed,
      reason,
      user_role: userRole,
    })
  }

  /**
   * Track authentication events
   */
  trackAuth(action: 'login' | 'logout' | 'register', method?: string) {
    this.track('auth', {
      action,
      method,
    })
  }

  /**
   * Send event to analytics service
   */
  private sendEvent(eventType: string, data: unknown) {
    if (this.isDebug) {
      console.log(`[Analytics] ${eventType}:`, data)
    }

    // In a real implementation, this would send to your analytics service
    // For now, we'll just log and potentially send to a local endpoint
    try {
      // Example: Send to analytics API
      if (this.shouldSendToAPI()) {
        this.sendToAPI(eventType, data)
      }
    } catch (error) {
      if (this.isDebug) {
        console.warn('[Analytics] Failed to send event:', error)
      }
    }
  }

  /**
   * Check if we should send to analytics API
   */
  private shouldSendToAPI(): boolean {
    // Don't send in development unless explicitly enabled
    if (this.isDebug && !window.localStorage.getItem('analytics-debug')) {
      return false
    }

    // Don't send if user has opted out
    if (window.localStorage.getItem('analytics-opt-out') === 'true') {
      return false
    }

    return true
  }

  /**
   * Send event to analytics API
   */
  private async sendToAPI(eventType: string, data: unknown) {
    // This would integrate with your actual analytics service
    // For example: Google Analytics, Mixpanel, custom endpoint, etc.

    // Example implementation:
    try {
      await fetch('/api/analytics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: eventType,
          data,
        }),
      })
    } catch (error) {
      // Silently fail in production, log in development
      if (this.isDebug) {
        console.warn('[Analytics] API request failed:', error)
      }
    }
  }

  /**
   * Get current session info
   */
  getSessionInfo() {
    return {
      session_id: this.context.session_id,
      user_id: this.context.user_id,
      timestamp: Date.now(),
    }
  }
}

// Create singleton instance
export const analytics = new Analytics()

// React hook for analytics
export function useAnalytics() {
  return {
    trackPageView: analytics.trackPageView.bind(analytics),
    trackNavigation: analytics.trackNavigation.bind(analytics),
    track: analytics.track.bind(analytics),
    trackInteraction: analytics.trackInteraction.bind(analytics),
    trackRouteGuard: analytics.trackRouteGuard.bind(analytics),
    trackAuth: analytics.trackAuth.bind(analytics),
    updateContext: analytics.updateContext.bind(analytics),
    getSessionInfo: analytics.getSessionInfo.bind(analytics),
  }
}

// Utility functions for common tracking patterns
export function trackLinkClick(href: string, text?: string) {
  analytics.trackInteraction('link', 'click', {
    href,
    text,
  })
}

export function trackButtonClick(buttonId: string, text?: string) {
  analytics.trackInteraction('button', 'click', {
    button_id: buttonId,
    text,
  })
}

export function trackFormSubmission(
  formId: string,
  success: boolean,
  errors?: string[]
) {
  analytics.track('form_submission', {
    form_id: formId,
    success,
    errors,
  })
}
