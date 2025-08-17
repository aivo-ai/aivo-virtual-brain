interface AlertProps {
  children: React.ReactNode
  variant?: 'default' | 'destructive'
  className?: string
}

interface AlertDescriptionProps {
  children: React.ReactNode
  className?: string
}

export function Alert({
  children,
  variant = 'default',
  className = '',
}: AlertProps) {
  const variantClasses = {
    default: 'bg-blue-50 border-blue-200 text-blue-800',
    destructive: 'bg-red-50 border-red-200 text-red-800',
  }

  return (
    <div
      className={`flex p-4 rounded-lg border ${variantClasses[variant]} ${className}`}
    >
      {children}
    </div>
  )
}

export function AlertDescription({
  children,
  className = '',
}: AlertDescriptionProps) {
  return <div className={`ml-3 text-sm ${className}`}>{children}</div>
}
