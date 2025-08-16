import { forwardRef, useState } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'

export interface EmailFieldProps {
  label?: string
  placeholder?: string
  error?: string
  disabled?: boolean
  required?: boolean
  autoComplete?: string
  className?: string
  registration: UseFormRegisterReturn
  'data-testid'?: string
}

export const EmailField = forwardRef<HTMLInputElement, EmailFieldProps>(
  (
    {
      label,
      placeholder = 'Enter your email address',
      error,
      disabled = false,
      required = false,
      autoComplete = 'email',
      className = '',
      registration,
      'data-testid': testId,
      ...props
    },
    ref
  ) => {
    const [isFocused, setIsFocused] = useState(false)

    const inputId = `email-${Math.random().toString(36).substring(7)}`
    const errorId = error ? `${inputId}-error` : undefined

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
            type="email"
            autoComplete={autoComplete}
            placeholder={placeholder}
            disabled={disabled}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={errorId}
            data-testid={testId}
            className={`
              block w-full px-3 py-2 border rounded-md shadow-sm
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

          {/* Email icon */}
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <svg
              className={`h-5 w-5 ${
                error ? 'text-red-400' : 'text-gray-400 dark:text-gray-500'
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
        </div>

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

EmailField.displayName = 'EmailField'
