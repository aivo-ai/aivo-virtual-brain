import React from 'react'
import { motion } from 'framer-motion'
import { FadeInWhenVisible } from './Animations'

interface AudienceCardProps {
  title: string
  description: string
  icon: React.ReactNode
  imagePlaceholder?: string
  imageUrl?: string
  delay?: number
}

export const AudienceCard: React.FC<AudienceCardProps> = ({
  title,
  description,
  icon,
  imagePlaceholder,
  imageUrl,
  delay = 0,
}) => {
  return (
    <FadeInWhenVisible delay={delay}>
      <motion.div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden hover:shadow-2xl transition-all duration-300 group"
        whileHover={{ y: -5 }}
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay }}
      >
        {/* Image or placeholder */}
        <div className="h-48 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 flex items-center justify-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={title}
              className="w-full h-full object-cover"
            />
          ) : (
            <span className="text-gray-500 dark:text-gray-400 text-sm font-medium z-10">
              {imagePlaceholder}
            </span>
          )}
          <motion.div
            className="absolute inset-0 bg-blue-500/10"
            initial={{ opacity: 0 }}
            whileHover={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          />
        </div>

        <div className="p-8">
          <div className="flex items-center mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-800 dark:to-indigo-800 rounded-lg flex items-center justify-center mr-4 group-hover:scale-110 transition-transform duration-300">
              {icon}
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300">
              {title}
            </h3>
          </div>

          <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
            {description}
          </p>
        </div>
      </motion.div>
    </FadeInWhenVisible>
  )
}
