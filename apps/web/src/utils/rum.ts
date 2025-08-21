/**
 * Real User Monitoring (RUM) Implementation
 * Captures Web Vitals and sends telemetry to OTEL collector
 */

import { getCLS, getFID, getFCP, getLCP, getTTFB, Metric } from 'web-vitals'
import { trace, context, SpanStatusCode, SpanKind } from '@opentelemetry/api'
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { Resource } from '@opentelemetry/resources'
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions'
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base'
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-http'
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web'
import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction'
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load'
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request'
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch'

// Configuration
const RUM_CONFIG = {
  serviceName: 'aivo-web-client',
  serviceVersion: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'development',
  collectorUrl:
    process.env.NEXT_PUBLIC_OTEL_COLLECTOR_URL ||
    'http://localhost:4318/v1/traces',
  sampleRate: parseFloat(process.env.NEXT_PUBLIC_RUM_SAMPLE_RATE || '0.1'),
  enableDebug: process.env.NEXT_PUBLIC_RUM_DEBUG === 'true',
}

// Session and user context
interface RUMContext {
  sessionId: string
  hashedLearnerId?: string
  userRole?: string
  gradeBand?: string
  tenantId?: string
  instanceId: string
}

class RUMService {
  private tracer: any
  private context: RUMContext
  private vitalsCollected: Set<string> = new Set()
  private isInitialized = false

  constructor() {
    this.context = {
      sessionId: this.generateSessionId(),
      instanceId: this.generateInstanceId(),
    }
  }

  /**
   * Initialize RUM service
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) return

    try {
      // Only initialize in browser environment
      if (typeof window === 'undefined') return

      // Check if we should sample this session
      if (Math.random() > RUM_CONFIG.sampleRate) {
        if (RUM_CONFIG.enableDebug) {
          console.log('[RUM] Session not sampled')
        }
        return
      }

      await this.setupOpenTelemetry()
      this.setupWebVitalsCollection()
      this.setupErrorTracking()
      this.setupNavigationTracking()
      this.trackPageLoad()

      this.isInitialized = true

      if (RUM_CONFIG.enableDebug) {
        console.log('[RUM] Initialized successfully', {
          sessionId: this.context.sessionId,
          instanceId: this.context.instanceId,
        })
      }
    } catch (error) {
      console.error('[RUM] Failed to initialize:', error)
    }
  }

  /**
   * Set user context (with hashed learner ID for privacy)
   */
  public setUserContext(context: Partial<RUMContext>): void {
    this.context = { ...this.context, ...context }

    // Update active span with new context
    const activeSpan = trace.getActiveSpan()
    if (activeSpan) {
      this.addContextToSpan(activeSpan)
    }

    if (RUM_CONFIG.enableDebug) {
      console.log('[RUM] User context updated', this.context)
    }
  }

  /**
   * Track custom user interaction
   */
  public trackInteraction(
    name: string,
    properties?: Record<string, any>
  ): void {
    if (!this.isInitialized) return

    const span = this.tracer.startSpan(`user.interaction.${name}`, {
      kind: SpanKind.CLIENT,
      attributes: {
        'interaction.type': name,
        'session.id': this.context.sessionId,
        'service.instance.id': this.context.instanceId,
        ...this.getUserAttributes(),
        ...properties,
      },
    })

    span.setStatus({ code: SpanStatusCode.OK })
    span.end()
  }

  /**
   * Track custom error with session correlation
   */
  public trackError(error: Error, context?: Record<string, any>): void {
    if (!this.isInitialized) return

    const span = this.tracer.startSpan('user.error', {
      kind: SpanKind.CLIENT,
      attributes: {
        'error.type': error.name,
        'error.message': error.message,
        'error.stack': error.stack?.substring(0, 1000), // Truncate stack trace
        'session.id': this.context.sessionId,
        'service.instance.id': this.context.instanceId,
        'url.full': window.location.href,
        'url.path': window.location.pathname,
        ...this.getUserAttributes(),
        ...context,
      },
    })

    span.recordException(error)
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: error.message,
    })
    span.end()
  }

  /**
   * Track feature flag evaluation for correlation
   */
  public trackFeatureFlag(
    flagKey: string,
    value: any,
    context?: Record<string, any>
  ): void {
    if (!this.isInitialized) return

    const span = this.tracer.startSpan('feature.flag.evaluation', {
      kind: SpanKind.CLIENT,
      attributes: {
        'feature.flag.key': flagKey,
        'feature.flag.value': JSON.stringify(value),
        'session.id': this.context.sessionId,
        'service.instance.id': this.context.instanceId,
        ...this.getUserAttributes(),
        ...context,
      },
    })

    span.setStatus({ code: SpanStatusCode.OK })
    span.end()
  }

  /**
   * Set up OpenTelemetry web tracing
   */
  private async setupOpenTelemetry(): Promise<void> {
    const resource = new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: RUM_CONFIG.serviceName,
      [SemanticResourceAttributes.SERVICE_VERSION]: RUM_CONFIG.serviceVersion,
      [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]:
        RUM_CONFIG.environment,
      [SemanticResourceAttributes.SERVICE_INSTANCE_ID]: this.context.instanceId,
    })

    const provider = new WebTracerProvider({
      resource,
    })

    // Configure OTLP exporter
    const exporter = new OTLPTraceExporter({
      url: RUM_CONFIG.collectorUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    provider.addSpanProcessor(
      new BatchSpanProcessor(exporter, {
        exportTimeoutMillis: 5000,
        scheduledDelayMillis: 1000,
        maxExportBatchSize: 50,
      })
    )

    provider.register()

    // Register auto-instrumentations
    registerInstrumentations({
      instrumentations: [
        new UserInteractionInstrumentation({
          eventNames: ['click', 'submit', 'keydown'],
        }),
        new DocumentLoadInstrumentation(),
        new XMLHttpRequestInstrumentation({
          clearTimingResources: true,
        }),
        new FetchInstrumentation({
          clearTimingResources: true,
          propagateTraceHeaderCorsUrls: [
            /^https?:\/\/localhost(:\d+)?\//,
            /^https?:\/\/.*\.aivo\.ai\//,
          ],
        }),
      ],
    })

    this.tracer = trace.getTracer(
      RUM_CONFIG.serviceName,
      RUM_CONFIG.serviceVersion
    )
  }

  /**
   * Set up Web Vitals collection
   */
  private setupWebVitalsCollection(): void {
    const sendVital = (metric: Metric) => {
      if (this.vitalsCollected.has(metric.name)) return
      this.vitalsCollected.add(metric.name)

      const span = this.tracer.startSpan(
        `web.vital.${metric.name.toLowerCase()}`,
        {
          kind: SpanKind.CLIENT,
          attributes: {
            'web.vital.name': metric.name,
            'web.vital.value': metric.value,
            'web.vital.rating': this.getVitalRating(metric),
            'web.vital.delta': metric.delta,
            'session.id': this.context.sessionId,
            'service.instance.id': this.context.instanceId,
            'url.full': window.location.href,
            'url.path': window.location.pathname,
            ...this.getUserAttributes(),
          },
        }
      )

      span.setStatus({ code: SpanStatusCode.OK })
      span.end()

      if (RUM_CONFIG.enableDebug) {
        console.log(`[RUM] Web Vital: ${metric.name}`, metric)
      }
    }

    // Collect Core Web Vitals
    getCLS(sendVital)
    getFID(sendVital)
    getFCP(sendVital)
    getLCP(sendVital)
    getTTFB(sendVital)
  }

  /**
   * Set up global error tracking
   */
  private setupErrorTracking(): void {
    // Unhandled JavaScript errors
    window.addEventListener('error', event => {
      this.trackError(new Error(event.message), {
        'error.filename': event.filename,
        'error.lineno': event.lineno,
        'error.colno': event.colno,
      })
    })

    // Unhandled promise rejections
    window.addEventListener('unhandledrejection', event => {
      this.trackError(
        new Error(event.reason?.toString() || 'Unhandled Promise Rejection'),
        {
          'error.type': 'UnhandledPromiseRejection',
        }
      )
    })

    // React error boundary integration
    ;(window as any).__RUM_TRACK_ERROR = this.trackError.bind(this)
  }

  /**
   * Set up navigation tracking
   */
  private setupNavigationTracking(): void {
    // Track page visibility changes
    document.addEventListener('visibilitychange', () => {
      this.trackInteraction('page.visibility.change', {
        'page.visible': !document.hidden,
      })
    })

    // Track page unload
    window.addEventListener('beforeunload', () => {
      this.trackInteraction('page.unload')
    })

    // Track hash changes (for SPA navigation)
    window.addEventListener('hashchange', () => {
      this.trackInteraction('navigation.hash.change', {
        'url.hash': window.location.hash,
      })
    })
  }

  /**
   * Track initial page load
   */
  private trackPageLoad(): void {
    const span = this.tracer.startSpan('page.load', {
      kind: SpanKind.CLIENT,
      attributes: {
        'session.id': this.context.sessionId,
        'service.instance.id': this.context.instanceId,
        'url.full': window.location.href,
        'url.path': window.location.pathname,
        'url.query': window.location.search,
        'url.hash': window.location.hash,
        'page.title': document.title,
        'user_agent.original': navigator.userAgent,
        'screen.width': screen.width,
        'screen.height': screen.height,
        ...this.getUserAttributes(),
      },
    })

    span.setStatus({ code: SpanStatusCode.OK })
    span.end()
  }

  /**
   * Get Web Vital rating (good/needs-improvement/poor)
   */
  private getVitalRating(metric: Metric): string {
    const thresholds: Record<string, [number, number]> = {
      CLS: [0.1, 0.25],
      FID: [100, 300],
      FCP: [1800, 3000],
      LCP: [2500, 4000],
      TTFB: [800, 1800],
    }

    const [good, poor] = thresholds[metric.name] || [0, 0]
    if (metric.value <= good) return 'good'
    if (metric.value <= poor) return 'needs-improvement'
    return 'poor'
  }

  /**
   * Add context attributes to span
   */
  private addContextToSpan(span: any): void {
    const attributes = {
      'session.id': this.context.sessionId,
      'service.instance.id': this.context.instanceId,
      ...this.getUserAttributes(),
    }

    for (const [key, value] of Object.entries(attributes)) {
      if (value !== undefined) {
        span.setAttribute(key, value)
      }
    }
  }

  /**
   * Get user-related attributes (with privacy protection)
   */
  private getUserAttributes(): Record<string, string> {
    const attributes: Record<string, string> = {}

    if (this.context.hashedLearnerId) {
      attributes['user.id.hashed'] = this.context.hashedLearnerId
    }
    if (this.context.userRole) {
      attributes['user.role'] = this.context.userRole
    }
    if (this.context.gradeBand) {
      attributes['user.grade_band'] = this.context.gradeBand
    }
    if (this.context.tenantId) {
      attributes['tenant.id'] = this.context.tenantId
    }

    return attributes
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Generate service instance ID
   */
  private generateInstanceId(): string {
    return `web_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Hash learner ID for privacy
   */
  public static hashLearnerId(learnerId: string): string {
    // Simple hash for demo - in production use crypto.subtle.digest
    let hash = 0
    for (let i = 0; i < learnerId.length; i++) {
      const char = learnerId.charCodeAt(i)
      hash = (hash << 5) - hash + char
      hash = hash & hash // Convert to 32-bit integer
    }
    return `hashed_${Math.abs(hash).toString(36)}`
  }
}

// Singleton instance
export const rumService = new RUMService()

// React hook for easy integration
export function useRUM() {
  return {
    trackInteraction: rumService.trackInteraction.bind(rumService),
    trackError: rumService.trackError.bind(rumService),
    trackFeatureFlag: rumService.trackFeatureFlag.bind(rumService),
    setUserContext: rumService.setUserContext.bind(rumService),
  }
}

// React Error Boundary HOC
export function withRUMErrorTracking<P extends object>(
  WrappedComponent: React.ComponentType<P>
): React.ComponentType<P> {
  return class extends React.Component<P, { hasError: boolean }> {
    constructor(props: P) {
      super(props)
      this.state = { hasError: false }
    }

    static getDerivedStateFromError(): { hasError: boolean } {
      return { hasError: true }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
      rumService.trackError(error, {
        'react.component': WrappedComponent.name,
        'react.error_boundary': true,
        'react.component_stack': errorInfo.componentStack,
      })
    }

    render() {
      if (this.state.hasError) {
        return React.createElement(
          'div',
          null,
          'Something went wrong. Please refresh the page.'
        )
      }

      return React.createElement(WrappedComponent, this.props)
    }
  }
}

// Auto-initialize RUM service
if (typeof window !== 'undefined') {
  rumService.initialize().catch(console.error)
}

export default rumService
