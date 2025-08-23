import React from 'react'
import { clsx } from 'clsx'

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  variant?: 'default' | 'error' | 'success' | 'warning'
  size?: 'sm' | 'md' | 'lg'
  required?: boolean
  children: React.ReactNode
}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  (
    {
      variant = 'default',
      size = 'md',
      required = false,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = clsx(
      'font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
      {
        'text-xs': size === 'sm',
        'text-sm': size === 'md',
        'text-base': size === 'lg',
        'text-gray-700': variant === 'default',
        'text-red-600': variant === 'error',
        'text-green-600': variant === 'success',
        'text-yellow-600': variant === 'warning',
      },
      className
    )

    return (
      <label ref={ref} className={baseClasses} {...props}>
        {children}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
    )
  }
)

Label.displayName = 'Label'
