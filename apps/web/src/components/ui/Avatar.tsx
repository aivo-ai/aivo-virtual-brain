import React, { useState } from 'react'

export interface AvatarProps {
  children: React.ReactNode
  className?: string
}

export const Avatar: React.FC<AvatarProps> = ({ children, className = '' }) => {
  return (
    <div
      className={`relative overflow-hidden rounded-full bg-gray-100 ${className}`}
    >
      {children}
    </div>
  )
}

export interface AvatarImageProps {
  src?: string
  alt?: string
  className?: string
}

export const AvatarImage: React.FC<AvatarImageProps> = ({
  src,
  alt,
  className = '',
}) => {
  const [imageError, setImageError] = useState(false)

  if (!src || imageError) {
    return null
  }

  return (
    <img
      src={src}
      alt={alt}
      className={`w-full h-full object-cover ${className}`}
      onError={() => setImageError(true)}
    />
  )
}

export interface AvatarFallbackProps {
  children: React.ReactNode
  className?: string
}

export const AvatarFallback: React.FC<AvatarFallbackProps> = ({
  children,
  className = '',
}) => {
  return (
    <div
      className={`flex items-center justify-center w-full h-full bg-gray-200 text-gray-600 font-medium ${className}`}
    >
      {children}
    </div>
  )
}

export default Avatar
