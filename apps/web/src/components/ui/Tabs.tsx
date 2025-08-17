interface TabsProps {
  children: React.ReactNode
  defaultValue?: string
  className?: string
}

interface TabsListProps {
  children: React.ReactNode
  className?: string
}

interface TabsTriggerProps {
  children: React.ReactNode
  value: string
  className?: string
}

interface TabsContentProps {
  children: React.ReactNode
  value: string
  className?: string
}

export function Tabs({ children, defaultValue, className = '' }: TabsProps) {
  return (
    <div className={`${className}`} data-default-value={defaultValue}>
      {children}
    </div>
  )
}

export function TabsList({ children, className = '' }: TabsListProps) {
  return (
    <div
      className={`inline-flex h-10 items-center justify-center rounded-md bg-gray-100 p-1 text-gray-500 ${className}`}
    >
      {children}
    </div>
  )
}

export function TabsTrigger({
  children,
  value,
  className = '',
}: TabsTriggerProps) {
  return (
    <button
      className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-white data-[state=active]:text-gray-950 data-[state=active]:shadow-sm ${className}`}
      data-value={value}
    >
      {children}
    </button>
  )
}

export function TabsContent({
  children,
  value,
  className = '',
}: TabsContentProps) {
  return (
    <div
      className={`mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${className}`}
      data-value={value}
    >
      {children}
    </div>
  )
}
