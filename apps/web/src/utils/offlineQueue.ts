import Dexie, { type Table } from 'dexie'

// Types for offline queue
export interface QueuedRequest {
  id?: number
  url: string
  method: string
  headers: Record<string, string>
  body?: string
  timestamp: number
  retryCount: number
  maxRetries: number
  queueType: 'event-collector' | 'inference-gateway'
}

export interface OfflineData {
  id?: number
  type: 'lesson' | 'user-data' | 'assessment' | 'content'
  key: string
  data: any
  timestamp: number
  expiry?: number
}

// Dexie database for offline functionality
class OfflineDatabase extends Dexie {
  requestQueue!: Table<QueuedRequest>
  offlineData!: Table<OfflineData>

  constructor() {
    super('AivoOfflineDB')
    
    this.version(1).stores({
      requestQueue: '++id, timestamp, queueType, retryCount',
      offlineData: '++id, type, key, timestamp, expiry'
    })
  }
}

const db = new OfflineDatabase()

// Offline queue manager
export class OfflineQueue {
  private static instance: OfflineQueue
  private isOnline = navigator.onLine
  private retryInterval: number | null = null

  private constructor() {
    // Listen for online/offline events
    window.addEventListener('online', this.handleOnline.bind(this))
    window.addEventListener('offline', this.handleOffline.bind(this))
    
    // Start processing queue if online
    if (this.isOnline) {
      this.startProcessingQueue()
    }
  }

  static getInstance(): OfflineQueue {
    if (!OfflineQueue.instance) {
      OfflineQueue.instance = new OfflineQueue()
    }
    return OfflineQueue.instance
  }

  // Queue a request for background sync
  async queueRequest(
    url: string,
    options: RequestInit,
    queueType: QueuedRequest['queueType'],
    maxRetries = 3
  ): Promise<void> {
    const request: QueuedRequest = {
      url,
      method: options.method || 'GET',
      headers: this.extractHeaders(options.headers),
      body: typeof options.body === 'string' ? options.body : JSON.stringify(options.body),
      timestamp: Date.now(),
      retryCount: 0,
      maxRetries,
      queueType
    }

    await db.requestQueue.add(request)
    console.log(`Queued ${queueType} request for offline sync:`, url)

    // Notify UI about queued request
    this.notifyQueueUpdate()
  }

  // Process queued requests when back online
  private async processQueue(): Promise<void> {
    const requests = await db.requestQueue.orderBy('timestamp').toArray()
    
    for (const request of requests) {
      try {
        const response = await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body
        })

        if (response.ok) {
          // Success - remove from queue
          await db.requestQueue.delete(request.id!)
          console.log(`Successfully synced ${request.queueType} request:`, request.url)
        } else {
          // Handle retry logic
          await this.handleRetry(request)
        }
      } catch (error) {
        console.error(`Failed to sync ${request.queueType} request:`, error)
        await this.handleRetry(request)
      }
    }

    this.notifyQueueUpdate()
  }

  private async handleRetry(request: QueuedRequest): Promise<void> {
    if (request.retryCount < request.maxRetries) {
      // Increment retry count and try again later
      await db.requestQueue.update(request.id!, {
        retryCount: request.retryCount + 1
      })
    } else {
      // Max retries reached - remove from queue
      await db.requestQueue.delete(request.id!)
      console.warn(`Max retries reached for ${request.queueType} request:`, request.url)
    }
  }

  private extractHeaders(headers?: HeadersInit): Record<string, string> {
    if (!headers) return {}
    
    if (headers instanceof Headers) {
      const result: Record<string, string> = {}
      headers.forEach((value, key) => {
        result[key] = value
      })
      return result
    }
    
    if (Array.isArray(headers)) {
      const result: Record<string, string> = {}
      headers.forEach(([key, value]) => {
        result[key] = value
      })
      return result
    }
    
    return headers as Record<string, string>
  }

  private handleOnline(): void {
    this.isOnline = true
    console.log('Connection restored - processing queued requests')
    this.startProcessingQueue()
    this.notifyConnectionChange(true)
  }

  private handleOffline(): void {
    this.isOnline = false
    console.log('Connection lost - requests will be queued')
    this.stopProcessingQueue()
    this.notifyConnectionChange(false)
  }

  private startProcessingQueue(): void {
    // Process queue immediately
    this.processQueue()
    
    // Set up interval to process queue periodically
    if (!this.retryInterval) {
      this.retryInterval = window.setInterval(() => {
        this.processQueue()
      }, 30000) // Every 30 seconds
    }
  }

  private stopProcessingQueue(): void {
    if (this.retryInterval) {
      clearInterval(this.retryInterval)
      this.retryInterval = null
    }
  }

  private notifyQueueUpdate(): void {
    // Dispatch custom event for UI updates
    window.dispatchEvent(new CustomEvent('offline-queue-update', {
      detail: { isProcessing: this.isOnline }
    }))
  }

  private notifyConnectionChange(isOnline: boolean): void {
    // Dispatch custom event for connection status
    window.dispatchEvent(new CustomEvent('connection-change', {
      detail: { isOnline }
    }))
  }

  // Public API
  async getQueuedRequestsCount(): Promise<number> {
    return await db.requestQueue.count()
  }

  async clearQueue(): Promise<void> {
    await db.requestQueue.clear()
    this.notifyQueueUpdate()
  }

  get online(): boolean {
    return this.isOnline
  }
}

// Offline data storage utilities
export class OfflineDataManager {
  // Store data for offline access
  static async storeData(
    type: OfflineData['type'],
    key: string,
    data: any,
    expiryHours = 24
  ): Promise<void> {
    const item: OfflineData = {
      type,
      key,
      data,
      timestamp: Date.now(),
      expiry: Date.now() + (expiryHours * 60 * 60 * 1000)
    }

    await db.offlineData.put(item)
  }

  // Retrieve stored data
  static async getData(type: OfflineData['type'], key: string): Promise<any | null> {
    const item = await db.offlineData
      .where({ type, key })
      .first()

    if (!item) return null

    // Check if expired
    if (item.expiry && Date.now() > item.expiry) {
      await db.offlineData.delete(item.id!)
      return null
    }

    return item.data
  }

  // Clean up expired data
  static async cleanupExpiredData(): Promise<void> {
    const now = Date.now()
    await db.offlineData
      .where('expiry')
      .below(now)
      .delete()
  }

  // Get storage usage estimate
  static async getStorageUsage(): Promise<{ used: number; quota: number }> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate()
      return {
        used: estimate.usage || 0,
        quota: estimate.quota || 0
      }
    }
    return { used: 0, quota: 0 }
  }
}

// Enhanced fetch wrapper for offline support
export async function offlineFetch(
  url: string,
  options: RequestInit = {},
  queueType: QueuedRequest['queueType'] = 'event-collector'
): Promise<Response> {
  const queue = OfflineQueue.getInstance()

  try {
    const response = await fetch(url, options)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response
  } catch (error) {
    console.log('Fetch failed, queueing for offline sync:', error)
    
    // Queue the request for later sync
    await queue.queueRequest(url, options, queueType)
    
    // Return a response indicating the request was queued
    return new Response(
      JSON.stringify({ 
        success: false, 
        queued: true, 
        message: 'Request queued for sync when online' 
      }),
      {
        status: 202,
        statusText: 'Accepted - Queued for Sync',
        headers: { 'Content-Type': 'application/json' }
      }
    )
  }
}

// Initialize offline queue
export const offlineQueue = OfflineQueue.getInstance()

// Cleanup expired data on startup
OfflineDataManager.cleanupExpiredData().catch(console.error)
