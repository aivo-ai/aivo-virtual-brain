import React from 'react'
import { motion } from 'framer-motion'

interface AnimatedCounterProps {
  value: number
  suffix?: string
  prefix?: string
  duration?: number
  className?: string
}

export const AnimatedCounter: React.FC<AnimatedCounterProps> = ({
  value,
  suffix = '',
  prefix = '',
  duration = 2,
  className = '',
}) => {
  return (
    <motion.span
      className={className}
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
    >
      <motion.span
        initial={{ scale: 0.5 }}
        whileInView={{ scale: 1 }}
        viewport={{ once: true }}
        transition={{
          type: 'spring',
          stiffness: 100,
          damping: 10,
          duration,
        }}
      >
        {prefix}
        <motion.span
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration, delay: 0.2 }}
        >
          {value}
        </motion.span>
        {suffix}
      </motion.span>
    </motion.span>
  )
}

interface FadeInWhenVisibleProps {
  children: React.ReactNode
  delay?: number
  duration?: number
  className?: string
}

export const FadeInWhenVisible: React.FC<FadeInWhenVisibleProps> = ({
  children,
  delay = 0,
  duration = 0.6,
  className = '',
}) => {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration, delay }}
    >
      {children}
    </motion.div>
  )
}

interface SlideInFromLeftProps {
  children: React.ReactNode
  delay?: number
  className?: string
}

export const SlideInFromLeft: React.FC<SlideInFromLeftProps> = ({
  children,
  delay = 0,
  className = '',
}) => {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, x: -100 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, delay }}
    >
      {children}
    </motion.div>
  )
}

interface SlideInFromRightProps {
  children: React.ReactNode
  delay?: number
  className?: string
}

export const SlideInFromRight: React.FC<SlideInFromRightProps> = ({
  children,
  delay = 0,
  className = '',
}) => {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, x: 100 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, delay }}
    >
      {children}
    </motion.div>
  )
}

interface ScaleOnHoverProps {
  children: React.ReactNode
  scale?: number
  className?: string
}

export const ScaleOnHover: React.FC<ScaleOnHoverProps> = ({
  children,
  scale = 1.05,
  className = '',
}) => {
  return (
    <motion.div
      className={className}
      whileHover={{ scale }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      {children}
    </motion.div>
  )
}
