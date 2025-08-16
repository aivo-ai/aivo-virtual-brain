import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ROUTES } from '@/types/routes'
import { authClient, AuthAPIError } from '@/api/authClient'
import { EmailField } from '@/components/forms/EmailField'
import { PasswordField } from '@/components/forms/PasswordField'

// Validation schemas
const requestResetSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
})

const resetPasswordSchema = z
  .object({
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .max(128, 'Password must be less than 128 characters')
      .regex(
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
        'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character'
      ),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine(data => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type RequestResetFormData = z.infer<typeof requestResetSchema>
type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>

export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showSuccess, setShowSuccess] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  // Check if we have a reset token in the URL
  const resetToken = searchParams.get('token')
  const isResettingPassword = Boolean(resetToken)

  // Request reset form
  const {
    register: registerRequest,
    handleSubmit: handleRequestSubmit,
    formState: { errors: requestErrors },
    setError: setRequestError,
  } = useForm<RequestResetFormData>({
    resolver: zodResolver(requestResetSchema),
    defaultValues: {
      email: '',
    },
  })

  // Reset password form
  const {
    register: registerReset,
    handleSubmit: handleResetSubmit,
    formState: { errors: resetErrors },
    setError: setResetError,
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      password: '',
      confirmPassword: '',
    },
  })

  const onRequestSubmit = async (data: RequestResetFormData) => {
    setIsLoading(true)
    setError('')

    try {
      await authClient.requestPasswordReset(data.email)
      setSuccessMessage(t('auth.reset_email_sent'))
      setShowSuccess(true)
    } catch (error) {
      if (error instanceof AuthAPIError) {
        switch (error.code) {
          case 'EMAIL_NOT_FOUND':
            setRequestError('email', {
              message: t('auth.errors.email_not_found'),
            })
            break
          case 'ACCOUNT_LOCKED':
            setError(t('auth.errors.account_locked'))
            break
          default:
            setError(error.message)
        }
      } else {
        setError(t('auth.errors.network_error'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const onResetSubmit = async (data: ResetPasswordFormData) => {
    if (!resetToken) return

    setIsLoading(true)
    setError('')

    try {
      await authClient.resetPassword(resetToken, data.password)
      setSuccessMessage(t('auth.password_reset_success'))
      setShowSuccess(true)
    } catch (error) {
      if (error instanceof AuthAPIError) {
        switch (error.code) {
          case 'INVALID_TOKEN':
            setError(t('auth.errors.invalid_reset_token'))
            break
          case 'EXPIRED_TOKEN':
            setError(t('auth.errors.expired_reset_token'))
            break
          case 'WEAK_PASSWORD':
            setResetError('password', {
              message: t('auth.errors.weak_password'),
            })
            break
          default:
            setError(error.message)
        }
      } else {
        setError(t('auth.errors.network_error'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (showSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto">
              <svg
                className="w-8 h-8 text-green-600 dark:text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="mt-6 text-center text-3xl font-bold text-gray-900 dark:text-white">
              {isResettingPassword
                ? t('auth.password_updated_title')
                : t('auth.reset_email_sent_title')}
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
              {successMessage}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow-lg rounded-lg">
            <div className="text-center">
              <Link
                to={ROUTES.LOGIN}
                className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                data-testid="back-to-login"
              >
                {t('auth.back_to_login')}
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
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
            {isResettingPassword
              ? t('auth.reset_password_title')
              : t('auth.forgot_password_title')}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            {isResettingPassword
              ? t('auth.reset_password_subtitle')
              : t('auth.forgot_password_subtitle')}
          </p>
        </div>

        {/* Form */}
        <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow-lg rounded-lg">
          {!isResettingPassword ? (
            // Request reset form
            <form
              onSubmit={handleRequestSubmit(onRequestSubmit)}
              className="space-y-6"
            >
              <EmailField
                label={t('auth.email_label')}
                placeholder={t('auth.email_placeholder')}
                required
                error={requestErrors.email?.message}
                registration={registerRequest('email')}
                data-testid="reset-email"
              />

              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
                  <p
                    className="text-sm text-red-700 dark:text-red-400"
                    role="alert"
                  >
                    {error}
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800 transition-colors"
                data-testid="send-reset-email"
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
                    {t('auth.sending')}
                  </>
                ) : (
                  t('auth.send_reset_email')
                )}
              </button>

              <div className="text-center">
                <Link
                  to={ROUTES.LOGIN}
                  className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                  data-testid="back-to-login-link"
                >
                  {t('auth.back_to_login')}
                </Link>
              </div>
            </form>
          ) : (
            // Reset password form
            <form
              onSubmit={handleResetSubmit(onResetSubmit)}
              className="space-y-6"
            >
              <PasswordField
                label={t('auth.new_password_label')}
                placeholder={t('auth.new_password_placeholder')}
                required
                autoComplete="new-password"
                showStrengthIndicator
                error={resetErrors.password?.message}
                registration={registerReset('password')}
                data-testid="new-password"
              />

              <PasswordField
                label={t('auth.confirm_password_label')}
                placeholder={t('auth.confirm_password_placeholder')}
                required
                autoComplete="new-password"
                error={resetErrors.confirmPassword?.message}
                registration={registerReset('confirmPassword')}
                data-testid="confirm-new-password"
              />

              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
                  <p
                    className="text-sm text-red-700 dark:text-red-400"
                    role="alert"
                  >
                    {error}
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed dark:focus:ring-offset-gray-800 transition-colors"
                data-testid="reset-password-submit"
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
                    {t('auth.updating_password')}
                  </>
                ) : (
                  t('auth.update_password')
                )}
              </button>

              <div className="text-center">
                <Link
                  to={ROUTES.LOGIN}
                  className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
                  data-testid="back-to-login-link"
                >
                  {t('auth.back_to_login')}
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
