export interface School {
  id: string
  name: string
  address: string
  phone?: string
  email?: string
  principalName?: string
  principalEmail?: string
  studentCapacity?: number
  grades?: string[]
  totalSeats: number
  usedSeats: number
  status: 'active' | 'inactive' | 'pending'
  createdAt: string
  updatedAt: string
}

export interface SeatAllocation {
  id: string
  schoolId: string
  schoolName: string
  totalSeats: number
  usedSeats: number
  availableSeats: number
  purchaseDate: string
  expiryDate: string
  status: 'active' | 'expired' | 'suspended'
}

export interface RosterUser {
  id?: string
  firstName: string
  lastName: string
  email: string
  role: 'teacher' | 'student' | 'parent'
  schoolId: string
  gradeLevel?: string
  classroomId?: string
  parentEmail?: string
  dateOfBirth?: string
  status: 'pending' | 'active' | 'inactive'
}

export interface RosterImportResult {
  id: string
  fileName: string
  totalRecords: number
  successfulImports: number
  failedImports: number
  errors: Array<{
    row: number
    field: string
    message: string
  }>
  status: 'processing' | 'completed' | 'failed'
  importDate: string
  createdAt: string
}

export interface DistrictStats {
  totalSchools: number
  activeSchools: number
  totalSeats: number
  usedSeats: number
  totalUsers: number
  activeUsers: number
  pendingRosterImports: number
}

class TenantClient {
  private baseURL: string

  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001'
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = localStorage.getItem('authToken')

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`)
    }

    return response.json()
  }

  // District Stats
  async getDistrictStats(): Promise<DistrictStats> {
    return this.request<DistrictStats>('/api/v1/district/stats')
  }

  // School Management
  async getSchools(): Promise<School[]> {
    return this.request<School[]>('/api/v1/district/schools')
  }

  async getSchool(schoolId: string): Promise<School> {
    return this.request<School>(`/api/v1/district/schools/${schoolId}`)
  }

  async createSchool(
    schoolData: Omit<School, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<School> {
    return this.request<School>('/api/v1/district/schools', {
      method: 'POST',
      body: JSON.stringify(schoolData),
    })
  }

  async updateSchool(
    schoolId: string,
    schoolData: Partial<School>
  ): Promise<School> {
    return this.request<School>(`/api/v1/district/schools/${schoolId}`, {
      method: 'PUT',
      body: JSON.stringify(schoolData),
    })
  }

  async deleteSchool(schoolId: string): Promise<void> {
    return this.request<void>(`/api/v1/district/schools/${schoolId}`, {
      method: 'DELETE',
    })
  }

  // Seat Management
  async getSeatAllocations(): Promise<SeatAllocation[]> {
    return this.request<SeatAllocation[]>('/api/v1/district/seats')
  }

  async purchaseSeats(purchaseData: {
    schoolId: string
    seatCount: number
    duration: number
  }): Promise<SeatAllocation> {
    return this.request<SeatAllocation>('/api/v1/district/seats/purchase', {
      method: 'POST',
      body: JSON.stringify(purchaseData),
    })
  }

  async allocateSeats(
    schoolId: string,
    seats: number
  ): Promise<SeatAllocation> {
    return this.request<SeatAllocation>(
      `/api/v1/district/seats/${schoolId}/allocate`,
      {
        method: 'POST',
        body: JSON.stringify({ seats }),
      }
    )
  }

  async reassignSeats(
    allocationId: string,
    reassignData: {
      fromSchoolId: string
      toSchoolId: string
      seatCount: number
    }
  ): Promise<SeatAllocation> {
    return this.request<SeatAllocation>(
      `/api/v1/district/seats/${allocationId}/reassign`,
      {
        method: 'POST',
        body: JSON.stringify(reassignData),
      }
    )
  }

  async deallocateSeats(
    schoolId: string,
    seats: number
  ): Promise<SeatAllocation> {
    return this.request<SeatAllocation>(
      `/api/v1/district/seats/${schoolId}/deallocate`,
      {
        method: 'POST',
        body: JSON.stringify({ seats }),
      }
    )
  }

  // Roster Import
  async uploadRosterFile(
    file: File,
    schoolId: string
  ): Promise<RosterImportResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('schoolId', schoolId)

    const response = await fetch(
      `${this.baseURL}/api/v1/district/roster/upload`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('authToken')}`,
        },
        body: formData,
      }
    )

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`)
    }

    return response.json()
  }

  async previewRoster(uploadId: string): Promise<RosterUser[]> {
    return this.request<RosterUser[]>(
      `/api/v1/district/roster/preview/${uploadId}`
    )
  }

  async importRoster(
    uploadId: string,
    schoolId: string
  ): Promise<RosterImportResult> {
    return this.request<RosterImportResult>('/api/v1/district/roster/import', {
      method: 'POST',
      body: JSON.stringify({ uploadId, schoolId }),
    })
  }

  async getRosterImports(): Promise<RosterImportResult[]> {
    return this.request<RosterImportResult[]>('/api/v1/district/roster/imports')
  }

  // Alias for getRosterImports for consistency
  async getRosterImportHistory(): Promise<RosterImportResult[]> {
    return this.getRosterImports()
  }

  async getRosterImport(importId: string): Promise<RosterImportResult> {
    return this.request<RosterImportResult>(
      `/api/v1/district/roster/imports/${importId}`
    )
  }

  // SCIM Endpoints (stubs)
  async createSCIMUser(userData: Partial<RosterUser>): Promise<RosterUser> {
    return this.request<RosterUser>('/api/v1/scim/Users', {
      method: 'POST',
      body: JSON.stringify({
        schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
        userName: userData.email,
        name: {
          givenName: userData.firstName,
          familyName: userData.lastName,
        },
        emails: [
          {
            value: userData.email,
            primary: true,
          },
        ],
        active: true,
        meta: {
          resourceType: 'User',
        },
      }),
    })
  }

  async updateSCIMUser(
    userId: string,
    userData: Partial<RosterUser>
  ): Promise<RosterUser> {
    return this.request<RosterUser>(`/api/v1/scim/Users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({
        schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
        id: userId,
        userName: userData.email,
        name: {
          givenName: userData.firstName,
          familyName: userData.lastName,
        },
        emails: [
          {
            value: userData.email,
            primary: true,
          },
        ],
        active: userData.status === 'active',
      }),
    })
  }

  async deleteSCIMUser(userId: string): Promise<void> {
    return this.request<void>(`/api/v1/scim/Users/${userId}`, {
      method: 'DELETE',
    })
  }

  // District Settings
  async getDistrictSettings(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/api/v1/district/settings')
  }

  async updateDistrictSettings(
    settings: Record<string, any>
  ): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/api/v1/district/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }
}

export const tenantClient = new TenantClient()
