import React from 'react'

export interface CheckboxProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  className?: string
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        type="checkbox"
        className={`h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded ${className || ''}`}
        ref={ref}
        {...props}
      />
    )
  }
)

Checkbox.displayName = 'Checkbox'
