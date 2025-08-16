import { forwardRef, useRef, useEffect, useState, KeyboardEvent } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'

export interface OtpInputProps {
  label?: string
  error?: string
  disabled?: boolean
  required?: boolean
  className?: string
  length?: number
  autoComplete?: string
  registration: UseFormRegisterReturn
  'data-testid'?: string
  onComplete?: (otp: string) => void
}

export const OtpInput = forwardRef<HTMLInputElement, OtpInputProps>(
  (
    {
      label,
      error,
      disabled = false,
      required = false,
      className = '',
      length = 6,
      autoComplete = 'one-time-code',
      registration,
      'data-testid': testId,
      onComplete,
    },
    ref
  ) => {
    const [values, setValues] = useState<string[]>(Array(length).fill(''))
    const [focusedIndex, setFocusedIndex] = useState<number>(0)
    const inputRefs = useRef<(HTMLInputElement | null)[]>([])

    const inputId = `otp-${Math.random().toString(36).substring(7)}`
    const errorId = error ? `${inputId}-error` : undefined

    // Initialize refs array
    useEffect(() => {
      inputRefs.current = inputRefs.current.slice(0, length)
    }, [length])

    // Focus first input on mount
    useEffect(() => {
      if (inputRefs.current[0] && !disabled) {
        inputRefs.current[0].focus()
      }
    }, [disabled])

    // Handle input changes
    const handleChange = (index: number, value: string) => {
      // Only allow single digits
      const sanitizedValue = value.replace(/[^0-9]/g, '').slice(-1)

      const newValues = [...values]
      newValues[index] = sanitizedValue
      setValues(newValues)

      // Update the form registration value
      const otpString = newValues.join('')
      if (registration.onChange) {
        registration.onChange({
          target: {
            name: registration.name,
            value: otpString,
          },
        } as any)
      }

      // Move to next input if current one is filled
      if (sanitizedValue && index < length - 1) {
        const nextInput = inputRefs.current[index + 1]
        if (nextInput) {
          nextInput.focus()
          setFocusedIndex(index + 1)
        }
      }

      // Call onComplete if all digits are filled
      if (otpString.length === length && onComplete) {
        onComplete(otpString)
      }
    }

    // Handle key down events
    const handleKeyDown = (
      index: number,
      e: KeyboardEvent<HTMLInputElement>
    ) => {
      if (e.key === 'Backspace') {
        e.preventDefault()

        const newValues = [...values]

        if (values[index]) {
          // Clear current input if it has a value
          newValues[index] = ''
          setValues(newValues)
        } else if (index > 0) {
          // Move to previous input and clear it
          newValues[index - 1] = ''
          setValues(newValues)
          const prevInput = inputRefs.current[index - 1]
          if (prevInput) {
            prevInput.focus()
            setFocusedIndex(index - 1)
          }
        }

        // Update form value
        const otpString = newValues.join('')
        if (registration.onChange) {
          registration.onChange({
            target: {
              name: registration.name,
              value: otpString,
            },
          } as any)
        }
      } else if (e.key === 'ArrowLeft' && index > 0) {
        e.preventDefault()
        const prevInput = inputRefs.current[index - 1]
        if (prevInput) {
          prevInput.focus()
          setFocusedIndex(index - 1)
        }
      } else if (e.key === 'ArrowRight' && index < length - 1) {
        e.preventDefault()
        const nextInput = inputRefs.current[index + 1]
        if (nextInput) {
          nextInput.focus()
          setFocusedIndex(index + 1)
        }
      }
    }

    // Handle paste events
    const handlePaste = (e: React.ClipboardEvent) => {
      e.preventDefault()

      const pastedData = e.clipboardData.getData('text/plain')
      const digits = pastedData.replace(/[^0-9]/g, '').slice(0, length)

      if (digits.length > 0) {
        const newValues = Array(length).fill('')
        for (let i = 0; i < digits.length; i++) {
          newValues[i] = digits[i]
        }
        setValues(newValues)

        // Update form value
        const otpString = newValues.join('')
        if (registration.onChange) {
          registration.onChange({
            target: {
              name: registration.name,
              value: otpString,
            },
          } as any)
        }

        // Focus the next empty input or the last input
        const nextIndex = Math.min(digits.length, length - 1)
        const targetInput = inputRefs.current[nextIndex]
        if (targetInput) {
          targetInput.focus()
          setFocusedIndex(nextIndex)
        }

        // Call onComplete if all digits are filled
        if (otpString.length === length && onComplete) {
          onComplete(otpString)
        }
      }
    }

    return (
      <div className={`space-y-3 ${className}`}>
        {label && (
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {label}
            {required && (
              <span className="text-red-500 ml-1" aria-label="required">
                *
              </span>
            )}
          </label>
        )}

        <div className="flex space-x-2 justify-center" onPaste={handlePaste}>
          {Array.from({ length }, (_, index) => (
            <input
              key={index}
              ref={el => {
                inputRefs.current[index] = el
                // Forward ref to the first input for form integration
                if (index === 0 && ref) {
                  if (typeof ref === 'function') {
                    ref(el)
                  } else {
                    ref.current = el
                  }
                }
              }}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={1}
              value={values[index] || ''}
              disabled={disabled}
              autoComplete={index === 0 ? autoComplete : 'off'}
              onChange={e => handleChange(index, e.target.value)}
              onKeyDown={e => handleKeyDown(index, e)}
              onFocus={() => setFocusedIndex(index)}
              aria-invalid={error ? 'true' : 'false'}
              aria-describedby={errorId}
              data-testid={testId ? `${testId}-${index}` : undefined}
              className={`
                w-12 h-12 text-center text-lg font-medium
                border rounded-lg shadow-sm
                focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500
                disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed
                dark:bg-gray-800 dark:border-gray-600 dark:text-white
                transition-all duration-200
                ${
                  error
                    ? 'border-red-300 dark:border-red-600 text-red-900 dark:text-red-100'
                    : 'border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white'
                }
                ${
                  focusedIndex === index && !disabled
                    ? 'ring-2 ring-primary-500 border-primary-500 transform scale-105'
                    : ''
                }
                ${
                  values[index]
                    ? 'bg-primary-50 dark:bg-primary-900/20'
                    : 'bg-white dark:bg-gray-800'
                }
              `}
            />
          ))}
        </div>

        {/* Hidden input for form integration */}
        <input {...registration} type="hidden" value={values.join('')} />

        {/* Instructions */}
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
          Enter the {length}-digit code from your authenticator app
        </p>

        {error && (
          <p
            id={errorId}
            className="text-sm text-red-600 dark:text-red-400 text-center"
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

OtpInput.displayName = 'OtpInput'
