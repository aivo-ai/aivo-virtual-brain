import { GraphQLClient } from 'graphql-request'

// Types
export interface IEPDraft {
  id: string
  learnerId: string
  status:
    | 'draft'
    | 'proposed'
    | 'pending_approval'
    | 'approved'
    | 'rejected'
    | 'active'
  content: {
    goals: IEPGoal[]
    accommodations: string[]
    services: IEPService[]
    placement: string
    assessments: IEPAssessment[]
  }
  metadata: {
    createdAt: string
    updatedAt: string
    createdBy: string
    proposedAt?: string
    proposedBy?: string
    submittedAt?: string
    submittedBy?: string
    reviewedAt?: string
    reviewedBy?: string
  }
  approvals: IEPApproval[]
  differences?: IEPDifference[]
}

export interface IEPGoal {
  id: string
  category: string
  description: string
  measurableOutcome: string
  timeline: string
  services: string[]
}

export interface IEPService {
  id: string
  type: string
  frequency: string
  duration: string
  location: string
  provider: string
}

export interface IEPAssessment {
  id: string
  type: string
  frequency: string
  accommodations: string[]
}

export interface IEPApproval {
  id: string
  actor: string
  actorRole: 'teacher' | 'parent' | 'admin' | 'specialist'
  status: 'pending' | 'approved' | 'rejected' | 'requested_changes'
  timestamp: string
  comments?: string
  requiredChanges?: string[]
}

export interface IEPDifference {
  section: string
  field: string
  oldValue: any
  newValue: any
  changeType: 'added' | 'removed' | 'modified'
}

export interface ProposeIEPInput {
  learnerId: string
  assistantPrompt?: string
  generateFromData?: boolean
}

export interface SubmitForApprovalInput {
  iepId: string
  approvers: Array<{
    userId: string
    role: string
    required: boolean
  }>
  comments?: string
}

// GraphQL queries and mutations
const PROPOSE_IEP_MUTATION = `
  mutation ProposeIEP($input: ProposeIEPInput!) {
    proposeIep(input: $input) {
      id
      learnerId
      status
      content {
        goals {
          id
          category
          description
          measurableOutcome
          timeline
          services
        }
        accommodations
        services {
          id
          type
          frequency
          duration
          location
          provider
        }
        placement
        assessments {
          id
          type
          frequency
          accommodations
        }
      }
      metadata {
        createdAt
        updatedAt
        createdBy
        proposedAt
        proposedBy
      }
      differences {
        section
        field
        oldValue
        newValue
        changeType
      }
    }
  }
`

const SUBMIT_IEP_FOR_APPROVAL_MUTATION = `
  mutation SubmitIEPForApproval($input: SubmitForApprovalInput!) {
    submitIepForApproval(input: $input) {
      id
      status
      approvals {
        id
        actor
        actorRole
        status
        timestamp
        comments
        requiredChanges
      }
      metadata {
        submittedAt
        submittedBy
      }
    }
  }
`

const GET_IEP_QUERY = `
  query GetIEP($learnerId: String!) {
    iep(learnerId: $learnerId) {
      id
      learnerId
      status
      content {
        goals {
          id
          category
          description
          measurableOutcome
          timeline
          services
        }
        accommodations
        services {
          id
          type
          frequency
          duration
          location
          provider
        }
        placement
        assessments {
          id
          type
          frequency
          accommodations
        }
      }
      metadata {
        createdAt
        updatedAt
        createdBy
        proposedAt
        proposedBy
        submittedAt
        submittedBy
        reviewedAt
        reviewedBy
      }
      approvals {
        id
        actor
        actorRole
        status
        timestamp
        comments
        requiredChanges
      }
      differences {
        section
        field
        oldValue
        newValue
        changeType
      }
    }
  }
`

const UPDATE_APPROVAL_STATUS_MUTATION = `
  mutation UpdateApprovalStatus($approvalId: String!, $status: String!, $comments: String, $requiredChanges: [String!]) {
    updateApprovalStatus(
      approvalId: $approvalId
      status: $status
      comments: $comments
      requiredChanges: $requiredChanges
    ) {
      id
      status
      timestamp
      comments
      requiredChanges
    }
  }
`

class IEPClient {
  private client: GraphQLClient

  constructor() {
    this.client = new GraphQLClient('/api/graphql', {
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  /**
   * Propose a new IEP draft using AI assistant
   */
  async proposeIep(input: ProposeIEPInput): Promise<IEPDraft> {
    try {
      const response = await this.client.request<{ proposeIep: IEPDraft }>(
        PROPOSE_IEP_MUTATION,
        { input }
      )
      return response.proposeIep
    } catch (error) {
      console.error('Failed to propose IEP:', error)
      throw new Error('Failed to generate IEP proposal. Please try again.')
    }
  }

  /**
   * Submit IEP draft for approval workflow
   */
  async submitIepForApproval(input: SubmitForApprovalInput): Promise<IEPDraft> {
    try {
      const response = await this.client.request<{
        submitIepForApproval: IEPDraft
      }>(SUBMIT_IEP_FOR_APPROVAL_MUTATION, { input })
      return response.submitIepForApproval
    } catch (error) {
      console.error('Failed to submit IEP for approval:', error)
      throw new Error('Failed to submit IEP for approval. Please try again.')
    }
  }

  /**
   * Get IEP for a learner
   */
  async getIEP(learnerId: string): Promise<IEPDraft | null> {
    try {
      const response = await this.client.request<{ iep: IEPDraft }>(
        GET_IEP_QUERY,
        { learnerId }
      )
      return response.iep
    } catch (error) {
      console.error('Failed to fetch IEP:', error)
      return null
    }
  }

  /**
   * Update approval status
   */
  async updateApprovalStatus(
    approvalId: string,
    status: string,
    comments?: string,
    requiredChanges?: string[]
  ): Promise<IEPApproval> {
    try {
      const response = await this.client.request<{
        updateApprovalStatus: IEPApproval
      }>(UPDATE_APPROVAL_STATUS_MUTATION, {
        approvalId,
        status,
        comments,
        requiredChanges,
      })
      return response.updateApprovalStatus
    } catch (error) {
      console.error('Failed to update approval status:', error)
      throw new Error('Failed to update approval status. Please try again.')
    }
  }

  /**
   * Set authorization token
   */
  setAuthToken(token: string) {
    this.client.setHeader('Authorization', `Bearer ${token}`)
  }

  /**
   * Clear authorization token
   */
  clearAuthToken() {
    this.client.setHeader('Authorization', '')
  }
}

export const iepClient = new IEPClient()
export default iepClient
