import { forwardRef, useState } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'

export interface PasswordFieldProps {
  label?: string
  placeholder?: string
  error?: string
  disabled?: boolean
  required?: boolean
  autoComplete?: string
  className?: string
  showStrengthIndicator?: boolean
  registration: UseFormRegisterReturn
  'data-testid'?: string
}

export interface PasswordStrength {
  score: number // 0-4
  label: string
  color: string
}

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(
  (
    {
      label,
      placeholder = 'Enter your password',
      error,
      disabled = false,
      required = false,
      autoComplete = 'current-password',
      className = '',
      showStrengthIndicator = false,
      registration,
      'data-testid': testId,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false)
    const [isFocused, setIsFocused] = useState(false)

    const inputId = `password-${Math.random().toString(36).substring(7)}`
    const errorId = error ? `${inputId}-error` : undefined

    // Get password value for strength calculation
    const passwordValue = registration.name
      ? (ref as any)?.current?.value || ''
      : ''

    const getPasswordStrength = (password: string): PasswordStrength => {
      if (!password) {
        return { score: 0, label: '', color: 'transparent' }
      }

      let score = 0

      // Length check
      if (password.length >= 8) score++
      if (password.length >= 12) score++

      // Character variety checks
      if (/[a-z]/.test(password)) score++
      if (/[A-Z]/.test(password)) score++
      if (/[0-9]/.test(password)) score++
      if (/[^A-Za-z0-9]/.test(password)) score++

      // Reduce score for common patterns
      if (/(.)\1{2,}/.test(password)) score-- // Repeated characters
      if (/123|abc|qwe/i.test(password)) score-- // Sequential patterns

      // Normalize score to 0-4
      score = Math.max(0, Math.min(4, score))

      const strengthMap = {
        0: { score: 0, label: 'Very Weak', color: 'bg-red-500' },
        1: { score: 1, label: 'Weak', color: 'bg-orange-500' },
        2: { score: 2, label: 'Fair', color: 'bg-yellow-500' },
        3: { score: 3, label: 'Good', color: 'bg-blue-500' },
        4: { score: 4, label: 'Strong', color: 'bg-green-500' },
      }

      return strengthMap[score as keyof typeof strengthMap]
    }

    const strength = showStrengthIndicator
      ? getPasswordStrength(passwordValue)
      : null

    return (
      <div className={`space-y-1 ${className}`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {label}
            {required && (
              <span className="text-red-500 ml-1" aria-label="required">
                *
              </span>
            )}
          </label>
        )}

        <div className="relative">
          <input
            {...registration}
            {...props}
            ref={ref}
            id={inputId}
            type={showPassword ? 'text' : 'password'}
            autoComplete={autoComplete}
            placeholder={placeholder}
            disabled={disabled}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={errorId}
            data-testid={testId}
            className={`
              block w-full px-3 py-2 pr-10 border rounded-md shadow-sm
              placeholder-gray-400 dark:placeholder-gray-500
              focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500
              disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed
              dark:bg-gray-800 dark:border-gray-600 dark:text-white
              transition-colors duration-200
              ${
                error
                  ? 'border-red-300 dark:border-red-600 text-red-900 dark:text-red-100 focus:ring-red-500 focus:border-red-500'
                  : 'border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white'
              }
              ${isFocused ? 'ring-2 ring-primary-500 border-primary-500' : ''}
            `}
          />

          {/* Toggle password visibility button */}
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            disabled={disabled}
            className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 dark:hover:text-gray-300 disabled:cursor-not-allowed"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            data-testid={`${testId}-toggle`}
          >
            {showPassword ? (
              <svg
                className="h-5 w-5 text-gray-400 dark:text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L12 12m-2.122-2.122L7.757 7.757M12 12l2.122 2.122m0 0L16.243 16.243M12 12l3.121 3.121M4.929 4.929l15.142 15.142"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5 text-gray-400 dark:text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            )}
          </button>
        </div>

        {/* Password strength indicator */}
        {showStrengthIndicator && passwordValue && (
          <div className="space-y-2">
            <div className="flex space-x-1">
              {Array.from({ length: 4 }, (_, i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                    i < (strength?.score || 0)
                      ? strength?.color || 'bg-gray-200'
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              ))}
            </div>
            {strength && strength.score > 0 && (
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Password strength: {strength.label}
              </p>
            )}
          </div>
        )}

        {error && (
          <p
            id={errorId}
            className="text-sm text-red-600 dark:text-red-400"
            role="alert"
            aria-live="polite"
          >
            {error}
          </p>
        )}
      </div>
    )
  }
)

PasswordField.displayName = 'PasswordField'
