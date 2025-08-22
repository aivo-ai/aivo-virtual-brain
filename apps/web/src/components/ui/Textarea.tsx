import React from 'react'

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  className?: string
}

export const Textarea: React.FC<TextareaProps> = ({
  className = '',
  ...props
}) => {
  return (
    <textarea
      className={`block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm 
                 placeholder-gray-400 focus:outline-none focus:ring-blue-500 
                 focus:border-blue-500 sm:text-sm resize-vertical ${className}`}
      {...props}
    />
  )
}

export default Textarea
