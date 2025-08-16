import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ROUTES } from '@/types/routes'
import { useAuth } from '@/app/providers/AuthProvider'
import { authClient, AuthAPIError } from '@/api/authClient'
import { EmailField } from '@/components/forms/EmailField'
import { PasswordField } from '@/components/forms/PasswordField'
import { OtpInput } from '@/components/forms/OtpInput'

// Validation schemas
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
})

const twoFactorSchema = z.object({
  code: z
    .string()
    .min(6, 'Code must be 6 digits')
    .max(6, 'Code must be 6 digits')
    .regex(/^\d{6}$/, 'Code must contain only digits'),
})

type LoginFormData = z.infer<typeof loginSchema>
type TwoFactorFormData = z.infer<typeof twoFactorSchema>

export default function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()

  const [isLoading, setIsLoading] = useState(false)
  const [showTwoFactor, setShowTwoFactor] = useState(false)
  const [twoFactorToken, setTwoFactorToken] = useState('')
  const [authError, setAuthError] = useState('')

  const redirectTo = searchParams.get('redirect') || ROUTES.DASHBOARD

  // Login form
  const {
    register: registerLogin,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })

  // 2FA form
  const {
    register: register2FA,
    handleSubmit: handle2FASubmit,
    formState: { errors: twoFactorErrors },
    setError: set2FAError,
    reset: reset2FA,
  } = useForm<TwoFactorFormData>({
    resolver: zodResolver(twoFactorSchema),
    defaultValues: {
      code: '',
    },
  })

  const onLoginSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    setAuthError('')

    try {
      const response = await authClient.login({
        email: data.email,
        password: data.password,
      })

      if (response.requires2FA) {
        // Show 2FA form - for mock, we'll use a mock token
        setTwoFactorToken('mock_2fa_token')
        setShowTwoFactor(true)
      } else {
        // Complete login
        await login(data.email, data.password)
        navigate(redirectTo, { replace: true })
      }
    } catch (error) {
      if (error instanceof AuthAPIError) {
        switch (error.code) {
          case 'INVALID_CREDENTIALS':
            setAuthError(t('auth.errors.invalid_credentials'))
            break
          case 'ACCOUNT_LOCKED':
            setAuthError(t('auth.errors.account_locked'))
            break
          case 'EMAIL_NOT_VERIFIED':
            setAuthError(t('auth.errors.email_not_verified'))
            break
          default:
            setAuthError(error.message)
        }
      } else {
        setAuthError(t('auth.errors.network_error'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const on2FASubmit = async (data: TwoFactorFormData) => {
    if (!twoFactorToken) return

    setIsLoading(true)
    setAuthError('')

    try {
      const response = await authClient.verify2FA(twoFactorToken, data.code)

      // Complete login with 2FA verified user
      // Note: In a real implementation, we'd use the response.user data
      await login(response.user.email, 'verified')
      navigate(redirectTo, { replace: true })
    } catch (error) {
      if (error instanceof AuthAPIError) {
        switch (error.code) {
          case 'INVALID_2FA_CODE':
            set2FAError('code', { message: t('auth.errors.invalid_2fa_code') })
            break
          case 'EXPIRED_TOKEN':
            setAuthError(t('auth.errors.expired_token'))
            setShowTwoFactor(false)
            break
          default:
            setAuthError(error.message)
        }
      } else {
        setAuthError(t('auth.errors.network_error'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleBackToLogin = () => {
    setShowTwoFactor(false)
    setTwoFactorToken('')
    setAuthError('')
    reset2FA()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <Link to={ROUTES.HOME} className="inline-block">
            <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center mx-auto">
              <svg
                className="w-7 h-7 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M12 2L3 7l9 5 9-5-9-5zM3 17l9 5 9-5M3 12l9 5 9-5" />
              </svg>
            </div>
          </Link>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900 dark:text-white">
            {showTwoFactor
              ? t('auth.verify_2fa_title')
              : t('auth.sign_in_title')}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            {showTwoFactor ? (
              t('auth.verify_2fa_subtitle')
            ) : (
              <>
                {t('auth.sign_in_subtitle')}{' '}
                <Link
                  to={ROUTES.REGISTER}
                  className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                  data-testid="register-link"
                >
                  {t('auth.sign_up_link')}
                </Link>
              </>
            )}
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow-lg rounded-lg">
          {!showTwoFactor ? (
            <form
              onSubmit={handleLoginSubmit(onLoginSubmit)}
              className="space-y-6"
            >
              <EmailField
                label={t('auth.email_label')}
                placeholder={t('auth.email_placeholder')}
                required
                error={loginErrors.email?.message}
                registration={registerLogin('email')}
                data-testid="login-email"
              />

              <PasswordField
                label={t('auth.password_label')}
                placeholder={t('auth.password_placeholder')}
                required
                autoComplete="current-password"
                error={loginErrors.password?.message}
                registration={registerLogin('password')}
                data-testid="login-password"
              />

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    name="remember-me"
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-800"
                    data-testid="remember-me"
                  />
                  <label
                    htmlFor="remember-me"
                    className="ml-2 block text-sm text-gray-900 dark:text-gray-300"
                  >
                    {t('auth.remember_me')}
                  </label>
                </div>

                <div className="text-sm">
                  <Link
                    to="/reset-password"
                    className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                    data-testid="forgot-password-link"
                  >
                    {t('auth.forgot_password')}
                  </Link>
                </div>
              </div>

              {authError && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
                  <p
                    className="text-sm text-red-700 dark:text-red-400"
                    role="alert"
                  >
                    {authError}
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800 transition-colors"
                data-testid="login-submit"
              >
                {isLoading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    {t('auth.signing_in')}
                  </>
                ) : (
                  t('auth.sign_in')
                )}
              </button>

              {/* Social Login Placeholders */}
              <div className="mt-6">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-300 dark:border-gray-600" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                      {t('auth.or_continue_with')}
                    </span>
                  </div>
                </div>

                <div className="mt-6 grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    disabled
                    className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="google-login"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path
                        fill="currentColor"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="currentColor"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="currentColor"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      />
                      <path
                        fill="currentColor"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                    <span className="ml-2">Google</span>
                  </button>

                  <button
                    type="button"
                    disabled
                    className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="apple-login"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path
                        fill="currentColor"
                        d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"
                      />
                    </svg>
                    <span className="ml-2">Apple</span>
                  </button>
                </div>
              </div>
            </form>
          ) : (
            /* 2FA Form */
            <form onSubmit={handle2FASubmit(on2FASubmit)} className="space-y-6">
              <OtpInput
                label={t('auth.2fa_code_label')}
                required
                error={twoFactorErrors.code?.message}
                registration={register2FA('code')}
                data-testid="2fa-code"
                onComplete={code => {
                  // Submit 2FA form with the completed code
                  handle2FASubmit(on2FASubmit)({ code } as any)
                }}
              />

              {authError && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
                  <p
                    className="text-sm text-red-700 dark:text-red-400"
                    role="alert"
                  >
                    {authError}
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800 transition-colors"
                  data-testid="2fa-submit"
                >
                  {isLoading ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      {t('auth.verifying')}
                    </>
                  ) : (
                    t('auth.verify_2fa')
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleBackToLogin}
                  disabled={isLoading}
                  className="w-full flex justify-center py-2 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  data-testid="back-to-login"
                >
                  {t('auth.back_to_login')}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
