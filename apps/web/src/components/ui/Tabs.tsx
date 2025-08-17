import React, { createContext, useContext, useState } from 'react'

interface TabsContextType {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const TabsContext = createContext<TabsContextType | undefined>(undefined)

export interface TabsProps {
  children: React.ReactNode
  defaultValue: string
  className?: string
}

export const Tabs: React.FC<TabsProps> = ({
  children,
  defaultValue,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState(defaultValue)

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

export interface TabsListProps {
  children: React.ReactNode
  className?: string
}

export const TabsList: React.FC<TabsListProps> = ({
  children,
  className = '',
}) => {
  return (
    <div className={`flex border-b border-gray-200 ${className}`}>
      {children}
    </div>
  )
}

export interface TabsTriggerProps {
  children: React.ReactNode
  value: string
  className?: string
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({
  children,
  value,
  className = '',
}) => {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('TabsTrigger must be used within a Tabs component')
  }

  const { activeTab, setActiveTab } = context
  const isActive = activeTab === value

  return (
    <button
      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
        isActive
          ? 'border-blue-500 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      } ${className}`}
      onClick={() => setActiveTab(value)}
    >
      {children}
    </button>
  )
}

export interface TabsContentProps {
  children: React.ReactNode
  value: string
  className?: string
}

export const TabsContent: React.FC<TabsContentProps> = ({
  children,
  value,
  className = '',
}) => {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('TabsContent must be used within a Tabs component')
  }

  const { activeTab } = context
  if (activeTab !== value) {
    return null
  }

  return <div className={className}>{children}</div>
}

export default Tabs
