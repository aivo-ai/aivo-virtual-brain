export const AivoLogo = ({ className = 'w-[300px] h-[108px]' }) => (
  <div className="flex items-center space-x-2">
    <img
      src="/assets/logos/aivo-logo.svg"
      alt="AIVO Logo"
      className={`${className} object-contain`}
      onError={e => {
        // Fallback to PNG if SVG fails
        e.currentTarget.src = '/assets/logos/aivo-logo.png'
      }}
    />
  </div>
)

export const AivoIcon = ({ className = 'w-[108px] h-[108px]' }) => (
  <img
    src="/assets/logos/aivo-icon.svg"
    alt="AIVO Icon"
    className={className}
    onError={e => {
      // Fallback to PNG if SVG fails
      e.currentTarget.src = '/assets/logos/aivo-icon.png'
    }}
  />
)
