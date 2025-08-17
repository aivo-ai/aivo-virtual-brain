interface RadioGroupProps {
  children: React.ReactNode
  value?: string
  onValueChange?: (value: string) => void
  className?: string
}

interface RadioGroupItemProps {
  value: string
  id?: string
  className?: string
}

export function RadioGroup({
  children,
  value,
  onValueChange: _onValueChange,
  className = '',
}: RadioGroupProps) {
  return (
    <div
      className={`grid gap-2 ${className}`}
      role="radiogroup"
      data-value={value}
    >
      {children}
    </div>
  )
}

export function RadioGroupItem({
  value,
  id,
  className = '',
}: RadioGroupItemProps) {
  return (
    <input
      type="radio"
      value={value}
      id={id}
      className={`aspect-square h-4 w-4 rounded-full border border-gray-300 text-blue-600 ring-offset-white focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    />
  )
}
