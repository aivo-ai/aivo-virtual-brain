import React from 'react'
import { motion } from 'framer-motion'
import { Button } from './Button'
import { FadeInWhenVisible } from './Animations'

interface PricingCardProps {
  title: string
  price: string
  period?: string
  features?: string[]
  isPopular?: boolean
  ctaText?: string
  onCtaClick?: () => void
  delay?: number
}

export const PricingCard: React.FC<PricingCardProps> = ({
  title,
  price,
  period = '/mo',
  features = [],
  isPopular = false,
  ctaText = 'Start Free Trial',
  onCtaClick,
  delay = 0,
}) => {
  return (
    <FadeInWhenVisible delay={delay}>
      <motion.div
        className={`relative bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 transition-all duration-300 ${
          isPopular
            ? 'border-2 border-blue-500 scale-105 shadow-2xl'
            : 'border border-gray-200 dark:border-gray-700 hover:shadow-xl'
        }`}
        whileHover={{ y: isPopular ? 0 : -5 }}
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay }}
      >
        {/* Popular badge */}
        {isPopular && (
          <motion.div
            className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-6 py-2 rounded-full text-sm font-semibold shadow-lg"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: delay + 0.3, type: 'spring', stiffness: 200 }}
          >
            Most Popular
          </motion.div>
        )}

        <div className="text-center">
          {/* Plan name */}
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            {title}
          </h3>

          {/* Price */}
          <div className="mb-6">
            <span className="text-5xl font-bold text-blue-600 dark:text-blue-400">
              {price}
            </span>
            {period && (
              <span className="text-gray-500 dark:text-gray-400 text-lg ml-1">
                {period}
              </span>
            )}
          </div>

          {/* Features */}
          {features.length > 0 && (
            <ul className="space-y-3 mb-8 text-left">
              {features.map((feature, index) => (
                <motion.li
                  key={index}
                  className="flex items-start"
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: delay + 0.1 * index }}
                >
                  <svg
                    className="w-5 h-5 text-green-500 mr-3 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span className="text-gray-600 dark:text-gray-300">
                    {feature}
                  </span>
                </motion.li>
              ))}
            </ul>
          )}

          {/* CTA Button */}
          <Button
            variant={isPopular ? 'primary' : 'outline'}
            size="lg"
            className="w-full"
            onClick={onCtaClick}
          >
            {ctaText}
          </Button>
        </div>
      </motion.div>
    </FadeInWhenVisible>
  )
}
