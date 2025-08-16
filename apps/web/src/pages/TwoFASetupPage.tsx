import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ROUTES } from '@/types/routes'
import { useAuth } from '@/app/providers/AuthProvider'
import { authClient, AuthAPIError } from '@/api/authClient'
import { OtpInput } from '@/components/forms/OtpInput'

// Validation schema
const verifySchema = z.object({
  code: z
    .string()
    .min(6, 'Code must be 6 digits')
    .max(6, 'Code must be 6 digits')
    .regex(/^\d{6}$/, 'Code must contain only digits'),
})

type VerifyFormData = z.infer<typeof verifySchema>

interface TwoFactorSetupData {
  qrCode: string
  secret: string
  backupCodes: string[]
}

export default function TwoFASetupPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [isLoading, setIsLoading] = useState(false)
  const [setupData, setSetupData] = useState<TwoFactorSetupData | null>(null)
  const [error, setError] = useState('')
  const [showSuccess, setShowSuccess] = useState(false)
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [step, setStep] = useState<'setup' | 'verify' | 'backup'>('setup')

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError: setFormError,
    reset,
  } = useForm<VerifyFormData>({
    resolver: zodResolver(verifySchema),
    defaultValues: {
      code: '',
    },
  })

  // Load 2FA setup data on component mount
  useEffect(() => {
    const setup2FA = async () => {
      if (!user) {
        navigate(ROUTES.LOGIN)
        return
      }

      setIsLoading(true)
      try {
        const data = await authClient.setup2FA('mock_access_token')
        setSetupData(data)
      } catch (error) {
        if (error instanceof AuthAPIError) {
          setError(error.message)
        } else {
          setError(t('auth.errors.network_error'))
        }
      } finally {
        setIsLoading(false)
      }
    }

    setup2FA()
  }, [user, navigate, t])

  const onVerifySubmit = async (data: VerifyFormData) => {
    if (!setupData) return

    setIsLoading(true)
    setError('')

    try {
      const response = await authClient.verify2FASetup(data.code)
      setBackupCodes(response.backupCodes)
      setStep('backup')
    } catch (error) {
      if (error instanceof AuthAPIError) {
        switch (error.code) {
          case 'INVALID_2FA_CODE':
            setFormError('code', { message: t('auth.errors.invalid_2fa_code') })
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

  const handleComplete = () => {
    setShowSuccess(true)
    setTimeout(() => {
      navigate(ROUTES.DASHBOARD)
    }, 2000)
  }

  const handleSkip = () => {
    navigate(ROUTES.DASHBOARD)
  }

  const copyBackupCodes = () => {
    const codesText = backupCodes.join('\n')
    navigator.clipboard.writeText(codesText)
  }

  const downloadBackupCodes = () => {
    const codesText = backupCodes.join('\n')
    const blob = new Blob([codesText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'aivo-backup-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
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
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <h2 className="mt-6 text-center text-3xl font-bold text-gray-900 dark:text-white">
              {t('auth.2fa_setup_complete')}
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
              {t('auth.2fa_setup_complete_subtitle')}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading && !setupData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <svg
            className="animate-spin h-12 w-12 text-primary-600 mx-auto"
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
          <p className="mt-4 text-gray-600 dark:text-gray-400">
            {t('auth.setting_up_2fa')}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center mx-auto">
            <svg
              className="w-7 h-7 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900 dark:text-white">
            {step === 'setup' && t('auth.setup_2fa_title')}
            {step === 'verify' && t('auth.verify_2fa_setup_title')}
            {step === 'backup' && t('auth.backup_codes_title')}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            {step === 'setup' && t('auth.setup_2fa_subtitle')}
            {step === 'verify' && t('auth.verify_2fa_setup_subtitle')}
            {step === 'backup' && t('auth.backup_codes_subtitle')}
          </p>
        </div>

        {/* Content */}
        <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow-lg rounded-lg">
          {step === 'setup' && setupData && (
            <div className="space-y-6">
              {/* QR Code */}
              <div className="text-center">
                <div className="inline-block p-4 bg-white rounded-lg">
                  <img
                    src={setupData.qrCode}
                    alt="2FA QR Code"
                    className="w-48 h-48 mx-auto"
                    data-testid="qr-code"
                  />
                </div>
              </div>

              {/* Manual Setup */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  {t('auth.manual_setup_title')}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  {t('auth.manual_setup_description')}
                </p>
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <code className="text-sm font-mono text-gray-900 dark:text-gray-100 break-all">
                    {setupData.secret}
                  </code>
                  <button
                    type="button"
                    onClick={() =>
                      navigator.clipboard.writeText(setupData.secret)
                    }
                    className="ml-2 text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 text-sm"
                    data-testid="copy-secret"
                  >
                    {t('common.copy')}
                  </button>
                </div>
              </div>

              {/* Instructions */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  {t('auth.setup_instructions_title')}
                </h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li>{t('auth.setup_instruction_1')}</li>
                  <li>{t('auth.setup_instruction_2')}</li>
                  <li>{t('auth.setup_instruction_3')}</li>
                </ol>
              </div>

              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setStep('verify')}
                  className="flex-1 py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                  data-testid="continue-setup"
                >
                  {t('auth.continue_setup')}
                </button>
                <button
                  type="button"
                  onClick={handleSkip}
                  className="flex-1 py-3 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                  data-testid="skip-setup"
                >
                  {t('auth.skip_for_now')}
                </button>
              </div>
            </div>
          )}

          {step === 'verify' && (
            <form onSubmit={handleSubmit(onVerifySubmit)} className="space-y-6">
              <OtpInput
                label={t('auth.verification_code_label')}
                required
                error={errors.code?.message}
                registration={register('code')}
                data-testid="verification-code"
                onComplete={code => {
                  // Auto-submit when code is complete
                  handleSubmit(onVerifySubmit)({ code } as any)
                }}
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

              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  data-testid="verify-code"
                >
                  {isLoading ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline"
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
                    t('auth.verify_code')
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep('setup')
                    setError('')
                    reset()
                  }}
                  disabled={isLoading}
                  className="flex-1 py-3 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  data-testid="back-to-setup"
                >
                  {t('common.back')}
                </button>
              </div>
            </form>
          )}

          {step === 'backup' && (
            <div className="space-y-6">
              {/* Warning */}
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-amber-400"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
                      {t('auth.backup_codes_warning_title')}
                    </h3>
                    <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                      {t('auth.backup_codes_warning')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Backup Codes */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  {t('auth.your_backup_codes')}
                </h3>
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md">
                  <div className="grid grid-cols-2 gap-2">
                    {backupCodes.map((code, index) => (
                      <div
                        key={index}
                        className="font-mono text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 p-2 rounded border"
                        data-testid={`backup-code-${index}`}
                      >
                        {code}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={copyBackupCodes}
                  className="flex-1 py-2 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                  data-testid="copy-codes"
                >
                  {t('auth.copy_codes')}
                </button>
                <button
                  type="button"
                  onClick={downloadBackupCodes}
                  className="flex-1 py-2 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                  data-testid="download-codes"
                >
                  {t('auth.download_codes')}
                </button>
              </div>

              <button
                type="button"
                onClick={handleComplete}
                className="w-full py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
                data-testid="complete-setup"
              >
                {t('auth.complete_setup')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
