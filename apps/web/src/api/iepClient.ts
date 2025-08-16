/**
 * S3-11 IEP GraphQL Client
 * Provides hooks and types for IEP operations with CRDT support
 */

import { useState, useEffect, useCallback } from 'react'

// Base GraphQL configuration
const IEP_GRAPHQL_URL =
  import.meta.env.VITE_IEP_GRAPHQL_URL || 'http://localhost:8005/graphql'

// TypeScript types based on GraphQL schema
export interface IEP {
  id: string
  studentId: string
  tenantId: string
  schoolDistrict: string
  schoolName: string
  title: string
  academicYear: string
  gradeLevel: string
  status: IEPStatus
  version: number
  isCurrent: boolean
  effectiveDate?: string
  expirationDate?: string
  crdtState: Record<string, any>
  signatureRequiredRoles: string[]
  createdBy: string
  createdAt: string
  updatedBy: string
  updatedAt: string
  sections: IEPSection[]
  signatures: ESignature[]
  evidenceAttachments: EvidenceAttachment[]
}

export interface IEPSection {
  id: string
  sectionType: IEPSectionType
  title: string
  orderIndex: number
  content: string
  operationCounter: number
  isRequired: boolean
  isLocked: boolean
  validationRules: Record<string, any>
  createdAt: string
  updatedAt: string
}

export interface ESignature {
  id: string
  signerUserId: string
  signerRole: string
  signerName: string
  signerEmail: string
  status: ESignatureStatus
  requestedAt: string
  signedAt?: string
  signatureData?: string
  signatureIpAddress?: string
  signatureUserAgent?: string
  metadata: Record<string, any>
}

export interface EvidenceAttachment {
  id: string
  filename: string
  originalFilename: string
  contentType: string
  fileSize: number
  evidenceType: string
  description?: string
  tags: string[]
  isConfidential: boolean
  accessLevel: string
  uploadedBy: string
  uploadedAt: string
  signedUrl?: string
}

export enum IEPStatus {
  DRAFT = 'DRAFT',
  IN_REVIEW = 'IN_REVIEW',
  ACTIVE = 'ACTIVE',
  ARCHIVED = 'ARCHIVED',
  DELETED = 'DELETED',
}

export enum IEPSectionType {
  STUDENT_INFO = 'STUDENT_INFO',
  PRESENT_LEVELS = 'PRESENT_LEVELS',
  ANNUAL_GOALS = 'ANNUAL_GOALS',
  SERVICES = 'SERVICES',
  SUPPLEMENTARY_AIDS = 'SUPPLEMENTARY_AIDS',
  PROGRAM_MODIFICATIONS = 'PROGRAM_MODIFICATIONS',
  ASSESSMENT_ACCOMMODATIONS = 'ASSESSMENT_ACCOMMODATIONS',
  TRANSITION_SERVICES = 'TRANSITION_SERVICES',
  BEHAVIOR_PLAN = 'BEHAVIOR_PLAN',
  ESY_SERVICES = 'ESY_SERVICES',
  ADDITIONAL_CONSIDERATIONS = 'ADDITIONAL_CONSIDERATIONS',
}

export enum ESignatureStatus {
  PENDING = 'PENDING',
  SENT = 'SENT',
  VIEWED = 'VIEWED',
  SIGNED = 'SIGNED',
  DECLINED = 'DECLINED',
  EXPIRED = 'EXPIRED',
}

// GraphQL operation types
export interface IEPCreateInput {
  studentId: string
  tenantId: string
  schoolDistrict: string
  schoolName: string
  title: string
  academicYear: string
  gradeLevel: string
  effectiveDate?: string
  expirationDate?: string
  signatureRequiredRoles: string[]
}

export interface IEPSectionUpsertInput {
  iepId: string
  sectionId?: string
  sectionType: IEPSectionType
  title: string
  content: string
  orderIndex: number
  operationCounter: number
}

export interface EvidenceAttachmentInput {
  iepId: string
  filename: string
  originalFilename: string
  contentType: string
  fileSize: number
  evidenceType: string
  description?: string
  tags: string[]
  isConfidential: boolean
  accessLevel: string
}

export interface SignatureRequestInput {
  iepId: string
  signerUserId: string
  signerRole: string
  signerEmail: string
}

// CRDT operation types
export interface CRDTOperation {
  type: 'insert' | 'delete' | 'retain'
  position: number
  content?: string
  length?: number
  operationId: string
  timestamp: number
  userId: string
}

export interface IEPUpdateEvent {
  iepId: string
  operationType:
    | 'SECTION_UPDATED'
    | 'STATUS_CHANGED'
    | 'SIGNATURE_ADDED'
    | 'EVIDENCE_ATTACHED'
  sectionId?: string
  userId: string
  timestamp: string
  crdtOperations?: CRDTOperation[]
  metadata?: Record<string, any>
}

// GraphQL client class
class IEPGraphQLClient {
  private baseURL: string
  private subscriptions: Map<string, WebSocket> = new Map()

  constructor() {
    this.baseURL = IEP_GRAPHQL_URL
  }

  private async request<T>(
    query: string,
    variables?: Record<string, any>
  ): Promise<T> {
    const response = await fetch(this.baseURL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
      },
      body: JSON.stringify({
        query,
        variables,
      }),
    })

    if (!response.ok) {
      throw new Error(`GraphQL request failed: ${response.statusText}`)
    }

    const result = await response.json()
    if (result.errors) {
      throw new Error(
        `GraphQL errors: ${result.errors.map((e: any) => e.message).join(', ')}`
      )
    }

    return result.data
  }

  async createIEP(
    input: IEPCreateInput
  ): Promise<{ createIep: { iep: IEP; success: boolean } }> {
    const query = `
      mutation CreateIEP($input: IEPCreateInput!) {
        createIep(input: $input) {
          iep {
            id
            studentId
            tenantId
            title
            status
            version
            sections {
              id
              sectionType
              title
              content
              orderIndex
            }
          }
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async getIEP(id: string): Promise<{ iep: IEP }> {
    const query = `
      query GetIEP($id: ID!) {
        iep(id: $id) {
          id
          studentId
          tenantId
          schoolDistrict
          schoolName
          title
          academicYear
          gradeLevel
          status
          version
          isCurrent
          effectiveDate
          expirationDate
          crdtState
          signatureRequiredRoles
          createdBy
          createdAt
          updatedBy
          updatedAt
          sections {
            id
            sectionType
            title
            orderIndex
            content
            operationCounter
            isRequired
            isLocked
            validationRules
            createdAt
            updatedAt
          }
          signatures {
            id
            signerUserId
            signerRole
            signerName
            signerEmail
            status
            requestedAt
            signedAt
            metadata
          }
          evidenceAttachments {
            id
            filename
            originalFilename
            contentType
            fileSize
            evidenceType
            description
            tags
            isConfidential
            accessLevel
            uploadedBy
            uploadedAt
          }
        }
      }
    `
    return this.request(query, { id })
  }

  async upsertSection(
    input: IEPSectionUpsertInput
  ): Promise<{ upsertSection: { section: IEPSection; success: boolean } }> {
    const query = `
      mutation UpsertSection($input: IEPSectionUpsertInput!) {
        upsertSection(input: $input) {
          section {
            id
            sectionType
            title
            content
            orderIndex
            operationCounter
            updatedAt
          }
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async attachEvidence(
    input: EvidenceAttachmentInput
  ): Promise<{
    attachEvidence: {
      attachment: EvidenceAttachment
      signedUrl: string
      success: boolean
    }
  }> {
    const query = `
      mutation AttachEvidence($input: EvidenceAttachmentInput!) {
        attachEvidence(input: $input) {
          attachment {
            id
            filename
            originalFilename
            contentType
            fileSize
            evidenceType
            description
            tags
            uploadedAt
          }
          signedUrl
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async requestSignature(
    input: SignatureRequestInput
  ): Promise<{
    requestSignature: { signature: ESignature; success: boolean }
  }> {
    const query = `
      mutation RequestSignature($input: SignatureRequestInput!) {
        requestSignature(input: $input) {
          signature {
            id
            signerUserId
            signerRole
            signerEmail
            status
            requestedAt
          }
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async setIEPStatus(
    iepId: string,
    status: IEPStatus
  ): Promise<{ setIepStatus: { iep: IEP; success: boolean } }> {
    const query = `
      mutation SetIEPStatus($iepId: String!, $status: IEPStatus!) {
        setIepStatus(iepId: $iepId, status: $status) {
          iep {
            id
            status
            updatedAt
          }
          success
        }
      }
    `
    return this.request(query, { iepId, status })
  }

  subscribeToIEPUpdates(
    iepId: string,
    onUpdate: (event: IEPUpdateEvent) => void
  ): () => void {
    const wsUrl = this.baseURL
      .replace('http', 'ws')
      .replace('/graphql', '/graphql-ws')
    const ws = new WebSocket(wsUrl, 'graphql-ws')

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          type: 'connection_init',
          payload: {
            Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
          },
        })
      )
    }

    ws.onmessage = event => {
      const message = JSON.parse(event.data)
      if (message.type === 'data' && message.payload?.data?.iepUpdated) {
        onUpdate(message.payload.data.iepUpdated)
      }
    }

    this.subscriptions.set(iepId, ws)

    // Send subscription
    setTimeout(() => {
      ws.send(
        JSON.stringify({
          id: iepId,
          type: 'start',
          payload: {
            query: `
            subscription IEPUpdated($iepId: String!) {
              iepUpdated(iepId: $iepId) {
                iepId
                operationType
                sectionId
                userId
                timestamp
                crdtOperations {
                  type
                  position
                  content
                  length
                  operationId
                  timestamp
                  userId
                }
                metadata
              }
            }
          `,
            variables: { iepId },
          },
        })
      )
    }, 1000)

    // Return cleanup function
    return () => {
      ws.close()
      this.subscriptions.delete(iepId)
    }
  }
}

export const iepClient = new IEPGraphQLClient()

// React hooks for IEP operations
export function useIEP(id: string) {
  const [iep, setIEP] = useState<IEP | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchIEP = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const { iep } = await iepClient.getIEP(id)
      setIEP(iep)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch IEP')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchIEP()
  }, [fetchIEP])

  const refresh = useCallback(() => {
    fetchIEP()
  }, [fetchIEP])

  return { iep, loading, error, refresh }
}

export function useIEPSubscription(
  iepId: string,
  onUpdate?: (event: IEPUpdateEvent) => void
) {
  useEffect(() => {
    if (!iepId) return

    const unsubscribe = iepClient.subscribeToIEPUpdates(iepId, event => {
      onUpdate?.(event)
    })

    return unsubscribe
  }, [iepId, onUpdate])
}

export function useIEPMutations() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const upsertSection = useCallback(async (input: IEPSectionUpsertInput) => {
    try {
      setLoading(true)
      setError(null)
      const result = await iepClient.upsertSection(input)
      return result.upsertSection
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update section'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const attachEvidence = useCallback(async (input: EvidenceAttachmentInput) => {
    try {
      setLoading(true)
      setError(null)
      const result = await iepClient.attachEvidence(input)
      return result.attachEvidence
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to attach evidence'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const requestSignature = useCallback(async (input: SignatureRequestInput) => {
    try {
      setLoading(true)
      setError(null)
      const result = await iepClient.requestSignature(input)
      return result.requestSignature
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to request signature'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const setStatus = useCallback(async (iepId: string, status: IEPStatus) => {
    try {
      setLoading(true)
      setError(null)
      const result = await iepClient.setIEPStatus(iepId, status)
      return result.setIepStatus
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update status'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    upsertSection,
    attachEvidence,
    requestSignature,
    setStatus,
    loading,
    error,
  }
}

// CRDT helper functions
export class CRDTHelper {
  static applyOperation(content: string, operation: CRDTOperation): string {
    switch (operation.type) {
      case 'insert':
        return (
          content.slice(0, operation.position) +
          (operation.content || '') +
          content.slice(operation.position)
        )

      case 'delete':
        return (
          content.slice(0, operation.position) +
          content.slice(operation.position + (operation.length || 0))
        )

      case 'retain':
        return content

      default:
        return content
    }
  }

  static createInsertOperation(
    position: number,
    content: string,
    userId: string
  ): CRDTOperation {
    return {
      type: 'insert',
      position,
      content,
      operationId: `${userId}-${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
      userId,
    }
  }

  static createDeleteOperation(
    position: number,
    length: number,
    userId: string
  ): CRDTOperation {
    return {
      type: 'delete',
      position,
      length,
      operationId: `${userId}-${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
      userId,
    }
  }
}
