import type {
  LoginBody,
  Login200,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  Setup2FAResponse,
  Verify2FAResponse,
  RefreshTokenResponse,
} from '@/types/sdk'

// Type definitions for fetch API
type RequestInit = globalThis.RequestInit

// Auth service configuration
const AUTH_BASE_URL =
  import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8001'

class AuthAPIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message)
    this.name = 'AuthAPIError'
  }
}

/**
 * Authentication client that provides methods for user authentication,
 * registration, password management, and two-factor authentication.
 *
 * Uses mock implementations during development and real API calls in production.
 */
class AuthClient {
  private baseURL: string

  constructor() {
    this.baseURL = AUTH_BASE_URL
  }

  /**
   * Make a request to the auth service
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new AuthAPIError(
        error || 'Request failed',
        response.status,
        response.headers.get('X-Error-Code') || undefined
      )
    }

    return response.json()
  }

  /**
   * Login user with email and password
   */
  async login(loginData: LoginBody): Promise<LoginResponse> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockLogin(loginData)
    }

    const response = await this.request<Login200>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(loginData),
    })

    return {
      user: response.user,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      requires2FA: response.requires2FA,
    }
  }

  /**
   * Register new user
   */
  async register(data: RegisterRequest): Promise<RegisterResponse> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockRegister(data)
    }

    return this.request<RegisterResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<{ message: string }> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockRequestPasswordReset(email)
    }

    return this.request<{ message: string }>('/auth/request-password-reset', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  /**
   * Setup 2FA for user
   */
  async setup2FA(accessToken: string): Promise<Setup2FAResponse> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockSetup2FA()
    }

    return this.request<Setup2FAResponse>('/auth/2fa/setup', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })
  }

  /**
   * Verify 2FA code during login
   */
  async verify2FA(
    twoFactorToken: string,
    code: string
  ): Promise<LoginResponse> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockVerify2FA(twoFactorToken, code)
    }

    return this.request<LoginResponse>('/auth/2fa/verify', {
      method: 'POST',
      body: JSON.stringify({
        twoFactorToken,
        code,
      }),
    })
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockRefreshToken(refreshToken)
    }

    return this.request<RefreshTokenResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refreshToken }),
    })
  }

  /**
   * Logout user
   */
  async logout(accessToken: string): Promise<{ message: string }> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockLogout()
    }

    return this.request<{ message: string }>('/auth/logout', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })
  }

  /**
   * Reset password with token
   */
  async resetPassword(
    token: string,
    newPassword: string
  ): Promise<{ message: string }> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockConfirmPasswordReset(token, newPassword)
    }

    return this.request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({
        token,
        newPassword,
      }),
    })
  }

  /**
   * Verify 2FA setup
   */
  async verify2FASetup(code: string): Promise<Verify2FAResponse> {
    // For development, use mock implementation
    if (import.meta.env.DEV) {
      return this.mockVerify2FASetup(code)
    }

    return this.request<Verify2FAResponse>('/auth/2fa/verify-setup', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
  }

  // Mock implementations for development
  private async mockLogin(data: LoginBody): Promise<LoginResponse> {
    await new Promise(resolve => setTimeout(resolve, 500)) // Simulate network delay

    // Simulate 2FA requirement for specific test accounts
    if (data.email === 'test2fa@example.com') {
      return {
        user: {
          id: '',
          email: '',
        },
        accessToken: '',
        refreshToken: '',
        requires2FA: true,
      }
    }

    return {
      user: {
        id: `user_${Date.now()}`,
        email: data.email,
        firstName: data.email.split('@')[0],
      },
      accessToken: `mock_token_${Date.now()}`,
      refreshToken: `mock_refresh_${Date.now()}`,
    }
  }

  private async mockRegister(data: RegisterRequest): Promise<RegisterResponse> {
    await new Promise(resolve => setTimeout(resolve, 800))

    return {
      user: {
        id: `user_${Date.now()}`,
        email: data.email,
        firstName: data.firstName,
        lastName: data.lastName,
      },
      accessToken: `mock_token_${Date.now()}`,
      refreshToken: `mock_refresh_${Date.now()}`,
      requiresVerification: false,
    }
  }

  private async mockRequestPasswordReset(
    email: string
  ): Promise<{ message: string }> {
    await new Promise(resolve => setTimeout(resolve, 300))

    return {
      message: `Password reset email sent to ${email}`,
    }
  }

  private async mockConfirmPasswordReset(
    _token: string,
    _newPassword: string
  ): Promise<{ message: string }> {
    await new Promise(resolve => setTimeout(resolve, 400))

    if (!_token.startsWith('mock_reset_')) {
      throw new AuthAPIError('Invalid reset token', 400, 'INVALID_TOKEN')
    }

    return {
      message: 'Password has been reset successfully',
    }
  }

  private async mockSetup2FA(): Promise<Setup2FAResponse> {
    await new Promise(resolve => setTimeout(resolve, 600))

    return {
      secret: 'JBSWY3DPEHPK3PXP',
      qrCode:
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
      backupCodes: [
        'abcd-1234',
        'efgh-5678',
        'ijkl-9012',
        'mnop-3456',
        'qrst-7890',
      ],
    }
  }

  private async mockVerify2FA(
    _token: string,
    code: string
  ): Promise<LoginResponse> {
    await new Promise(resolve => setTimeout(resolve, 400))

    if (code !== '123456') {
      throw new AuthAPIError('Invalid 2FA code', 400, 'INVALID_2FA_CODE')
    }

    return {
      user: {
        id: `user_${Date.now()}`,
        email: 'test2fa@example.com',
        firstName: 'Test',
        lastName: 'User',
      },
      accessToken: `mock_token_2fa_${Date.now()}`,
      refreshToken: `mock_refresh_2fa_${Date.now()}`,
    }
  }

  private async mockRefreshToken(
    _refreshToken: string
  ): Promise<RefreshTokenResponse> {
    await new Promise(resolve => setTimeout(resolve, 200))

    return {
      accessToken: `refreshed_token_${Date.now()}`,
      refreshToken: `refreshed_refresh_${Date.now()}`,
    }
  }

  private async mockLogout(): Promise<{ message: string }> {
    await new Promise(resolve => setTimeout(resolve, 200))

    return {
      message: 'Logged out successfully',
    }
  }

  private async mockVerify2FASetup(_code: string): Promise<Verify2FAResponse> {
    await new Promise(resolve => setTimeout(resolve, 300))

    return {
      verified: true,
      backupCodes: [
        'abcd-1234',
        'efgh-5678',
        'ijkl-9012',
        'mnop-3456',
        'qrst-7890',
      ],
    }
  }
}

// Create and export singleton instance
export const authClient = new AuthClient()

// Export for testing
export { AuthAPIError }
