import { GuardianProfile } from '../hooks/useOnboarding'

// Base API URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  phone?: string
  timezone: string
  preferredLanguage: string
  role: 'parent' | 'teacher' | 'admin'
  tenantId?: string
  createdAt: string
  updatedAt: string
}

export interface CreateUserRequest {
  email: string
  firstName: string
  lastName: string
  phone?: string
  timezone: string
  preferredLanguage: string
  role: 'parent' | 'teacher' | 'admin'
  tenantId?: string
}

export interface UpdateUserRequest extends Partial<CreateUserRequest> {
  id: string
}

class UserClient {
  async createUser(userData: CreateUserRequest): Promise<User> {
    const response = await fetch(`${API_BASE}/user-svc/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(userData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create user: ${response.statusText}`)
    }

    return response.json()
  }

  async updateUser(userData: UpdateUserRequest): Promise<User> {
    const response = await fetch(`${API_BASE}/user-svc/users/${userData.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(userData),
    })

    if (!response.ok) {
      throw new Error(`Failed to update user: ${response.statusText}`)
    }

    return response.json()
  }

  async getUser(userId: string): Promise<User> {
    const response = await fetch(`${API_BASE}/user-svc/users/${userId}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to get user: ${response.statusText}`)
    }

    return response.json()
  }

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE}/user-svc/users/me`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to get current user: ${response.statusText}`)
    }

    return response.json()
  }

  async createGuardianProfile(guardianData: GuardianProfile): Promise<User> {
    return this.createUser({
      ...guardianData,
      role: 'parent',
    })
  }

  async updateGuardianProfile(
    userId: string,
    guardianData: GuardianProfile
  ): Promise<User> {
    return this.updateUser({
      id: userId,
      ...guardianData,
    })
  }
}

export const userClient = new UserClient()
