// Mock types for @aivo/sdk-web until the actual SDK is available

export interface LoginBody {
  email: string
  password: string
}

export interface Login200 {
  accessToken: string
  refreshToken: string
  user: {
    id: string
    email: string
    firstName?: string
    lastName?: string
  }
  requires2FA?: boolean
}

export interface LoginResponse extends Login200 {
  requiresVerification?: boolean
}

export interface RegisterRequest {
  email: string
  password: string
  firstName?: string
  lastName?: string
  acceptTerms: boolean
  acceptPrivacy: boolean
}

export interface RegisterResponse extends LoginResponse {}

export interface RequestPasswordResetRequest {
  email: string
}

export interface RequestPasswordResetResponse {
  message: string
}

export interface Setup2FAResponse {
  qrCode: string
  secret: string
  backupCodes: string[]
}

export interface Verify2FAResponse {
  verified: boolean
  backupCodes: string[]
}

export interface RefreshTokenResponse {
  accessToken: string
  refreshToken: string
}
