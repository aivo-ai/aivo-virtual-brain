import React from 'react'
import { motion } from 'framer-motion'
import { AnimatedCounter, FadeInWhenVisible } from './Animations'

interface MetricCardProps {
  icon: string
  value: number
  suffix?: string
  prefix?: string
  label: string
  delay?: number
}

export const MetricCard: React.FC<MetricCardProps> = ({
  icon,
  value,
  suffix = '',
  prefix = '',
  label,
  delay = 0,
}) => {
  return (
    <FadeInWhenVisible delay={delay}>
      <motion.div
        className="text-center p-6"
        initial={{ scale: 0.8, opacity: 0 }}
        whileInView={{ scale: 1, opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay }}
        whileHover={{ scale: 1.05 }}
      >
        <div className="text-6xl mb-4 filter drop-shadow-lg">
          <span className="mr-2">{icon}</span>
          <AnimatedCounter
            value={value}
            prefix={prefix}
            suffix={suffix}
            className="text-4xl md:text-5xl font-bold text-white"
            duration={2 + delay}
          />
        </div>
        <p className="text-blue-100 text-lg font-medium leading-relaxed">
          {label}
        </p>
      </motion.div>
    </FadeInWhenVisible>
  )
}
