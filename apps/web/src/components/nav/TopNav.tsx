import React from 'react'

interface TopNavProps {
  className?: string
}

export const TopNav: React.FC<TopNavProps> = ({ className }) => {
  return (
    <nav className={`top-nav ${className || ''}`}>
      <div className="nav-content">
        <h1>AIVO Platform</h1>
        {/* Navigation items will be added here */}
      </div>
    </nav>
  )
}

export default TopNav
