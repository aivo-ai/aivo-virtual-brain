import React from 'react'
import { motion } from 'framer-motion'
import { FadeInWhenVisible } from './Animations'

interface FeatureCardProps {
  icon: React.ReactNode
  title: string
  description: string
  screenshot?: string
  delay?: number
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  icon,
  title,
  description,
  screenshot,
  delay = 0,
}) => {
  return (
    <FadeInWhenVisible delay={delay}>
      <motion.div
        className="group relative bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 hover:shadow-2xl transition-all duration-300"
        whileHover={{ y: -8 }}
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay }}
      >
        {/* Background gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        <div className="relative z-10">
          {/* Icon */}
          <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-800 dark:to-indigo-800 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
            {icon}
          </div>

          {/* Content */}
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300">
            {title}
          </h3>

          <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed mb-4">
            {description}
          </p>

          {/* Screenshot placeholder */}
          {screenshot && (
            <div className="w-full h-20 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center text-xs text-gray-500 dark:text-gray-400">
              UI Screenshot: {screenshot}
            </div>
          )}

          {/* Hover tooltip */}
          <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-3 py-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none whitespace-nowrap">
            Learn more about {title}
          </div>
        </div>
      </motion.div>
    </FadeInWhenVisible>
  )
}
