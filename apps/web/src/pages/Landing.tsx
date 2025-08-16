import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '@/app/providers/AuthProvider'
import { ROUTES } from '@/types/routes'
import { SEO } from '@/components/SEO'
import { Button } from '@/components/ui/Button'
import { FeatureCard } from '@/components/ui/FeatureCard'
import { MetricCard } from '@/components/ui/MetricCard'
import { AudienceCard } from '@/components/ui/AudienceCard'
import { PricingCard } from '@/components/ui/PricingCard'
import {
  FadeInWhenVisible,
  SlideInFromLeft,
  SlideInFromRight,
} from '@/components/ui/Animations'
import { useEffect } from 'react'

export default function Landing() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate(ROUTES.DASHBOARD)
    }
  }, [isAuthenticated, navigate])

  // Smooth scroll handler
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <>
      <SEO />
      <div className="min-h-screen bg-white dark:bg-gray-900 overflow-x-hidden">
        {/* Hero Section */}
        <section className="relative min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 overflow-hidden">
          {/* Background Elements */}
          <div className="absolute inset-0">
            {/* Classroom background image overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 to-indigo-600/10" />

            {/* Animated background shapes */}
            <motion.div
              className="absolute top-20 left-10 w-72 h-72 bg-blue-100 rounded-full mix-blend-multiply filter blur-xl opacity-30"
              animate={{
                scale: [1, 1.2, 1],
                rotate: [0, 90, 0],
              }}
              transition={{
                duration: 20,
                repeat: Infinity,
                ease: 'linear',
              }}
            />
            <motion.div
              className="absolute top-40 right-10 w-72 h-72 bg-accent-100 rounded-full mix-blend-multiply filter blur-xl opacity-30"
              animate={{
                scale: [1.2, 1, 1.2],
                rotate: [90, 0, 90],
              }}
              transition={{
                duration: 20,
                repeat: Infinity,
                ease: 'linear',
              }}
            />
            <motion.div
              className="absolute -bottom-32 left-1/2 transform -translate-x-1/2 w-96 h-96 bg-purple-100 rounded-full mix-blend-multiply filter blur-xl opacity-20"
              animate={{
                scale: [1, 1.3, 1],
                y: [0, -50, 0],
              }}
              transition={{
                duration: 15,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          </div>

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <FadeInWhenVisible>
              <motion.h1
                className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-gray-900 dark:text-white leading-tight mb-8"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
              >
                <motion.span
                  className="block"
                  initial={{ opacity: 0, x: -50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                >
                  Smarter IEPs.
                </motion.span>
                <motion.span
                  className="block bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent"
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                >
                  Happier Learners.
                </motion.span>
              </motion.h1>
            </FadeInWhenVisible>

            <FadeInWhenVisible delay={0.6}>
              <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 max-w-4xl mx-auto leading-relaxed mb-12">
                AIVO AI unites real‑time IEP management, adaptive learning, and
                inclusive enrichment in one safe, FERPA‑ready platform — built
                to serve every child, starting with those who need us most.
              </p>
            </FadeInWhenVisible>

            <FadeInWhenVisible delay={0.8}>
              <div className="flex flex-col items-center gap-6">
                <Button
                  size="xl"
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-12 py-4 text-xl font-bold shadow-2xl"
                  onClick={() => navigate(ROUTES.REGISTER)}
                >
                  Start Your Free 30‑Day Premium Trial
                </Button>

                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                  No credit card required. Keep every IEP, lesson, and progress
                  record — even if you don&apos;t upgrade.
                </p>

                <motion.button
                  onClick={() => scrollToSection('features')}
                  className="flex items-center text-blue-600 hover:text-blue-700 font-medium transition-colors"
                  whileHover={{ y: -2 }}
                  whileTap={{ y: 0 }}
                >
                  Learn More
                  <motion.svg
                    className="w-5 h-5 ml-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    animate={{ y: [0, 5, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 14l-7 7m0 0l-7-7m7 7V3"
                    />
                  </motion.svg>
                </motion.button>
              </div>
            </FadeInWhenVisible>
          </div>

          {/* Dashboard overlay showcase */}
          <motion.div
            className="absolute bottom-10 right-10 w-80 h-48 bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20 p-4 hidden lg:block"
            initial={{ opacity: 0, x: 100, y: 100 }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            transition={{ duration: 1, delay: 1.2 }}
          >
            <div className="text-white/80 text-xs mb-2">
              AIVO Dashboard Preview
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-blue-400/60 rounded-full w-3/4" />
              <div className="h-3 bg-accent-400/60 rounded-full w-1/2" />
              <div className="h-3 bg-green-400/60 rounded-full w-5/6" />
              <div className="grid grid-cols-3 gap-2 mt-4">
                <div className="h-8 bg-white/20 rounded-lg" />
                <div className="h-8 bg-white/20 rounded-lg" />
                <div className="h-8 bg-white/20 rounded-lg" />
              </div>
            </div>
          </motion.div>
        </section>

        {/* Challenge Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-800">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <SlideInFromLeft>
                <div>
                  <p className="text-xl text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">
                    Every delayed IEP review means lost learning time. Every
                    generic lesson risks leaving a child behind.
                  </p>
                  <h2 className="text-4xl font-bold text-gray-900 dark:text-white mb-8">
                    AIVO AI closes the gaps that hurt growth and compliance:
                  </h2>
                </div>
              </SlideInFromLeft>

              <SlideInFromRight>
                <div className="space-y-6">
                  {[
                    {
                      icon: '⏳',
                      text: 'Months‑late IEP reviews costing districts funding and students progress',
                      color: 'red',
                    },
                    {
                      icon: '🧩',
                      text: 'Fragmented tools forcing teachers into endless data re‑entry',
                      color: 'orange',
                    },
                    {
                      icon: '😔',
                      text: 'Disengaged learners facing one‑size‑fits‑all content',
                      color: 'yellow',
                    },
                    {
                      icon: '💸',
                      text: 'Per‑subject fees pushing families and districts beyond budget',
                      color: 'red',
                    },
                  ].map((item, index) => (
                    <FadeInWhenVisible key={index} delay={index * 0.2}>
                      <motion.div
                        className="flex items-start space-x-4 p-4 rounded-xl bg-white dark:bg-gray-700 shadow-md"
                        whileHover={{ scale: 1.02, x: 10 }}
                        transition={{ type: 'spring', stiffness: 300 }}
                      >
                        <div
                          className={`flex-shrink-0 w-14 h-14 bg-${item.color}-100 dark:bg-${item.color}-900 rounded-lg flex items-center justify-center`}
                        >
                          <span className="text-2xl">{item.icon}</span>
                        </div>
                        <p className="text-gray-600 dark:text-gray-300 flex-1 leading-relaxed">
                          {item.text}
                        </p>
                      </motion.div>
                    </FadeInWhenVisible>
                  ))}
                </div>
              </SlideInFromRight>
            </div>
          </div>
        </section>

        {/* Solution Section */}
        <section
          id="features"
          className="py-20 px-4 sm:px-6 lg:px-8 bg-white dark:bg-gray-900"
        >
          <div className="max-w-7xl mx-auto">
            <FadeInWhenVisible>
              <div className="text-center mb-16">
                <h2 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-6">
                  A single, integrated platform where compliance, instruction,
                  and engagement work in sync
                </h2>
                <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
                  So teachers teach, parents participate, and learners thrive.
                </p>
              </div>
            </FadeInWhenVisible>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-8">
              <FeatureCard
                icon={
                  <svg
                    className="w-8 h-8 text-blue-600 dark:text-blue-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                }
                title="Dynamic IEP Engine"
                description="Automatic deadline alerts, dual e‑signatures, immutable audit logs"
                screenshot="IEP Dashboard"
                delay={0}
              />

              <FeatureCard
                icon={
                  <svg
                    className="w-8 h-8 text-purple-600 dark:text-purple-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364-.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                }
                title="Adaptive AI Tutors"
                description="'Main Brain' coordinates subject‑specific learning from ELA to SEL, Science, Math, Languages, and more"
                screenshot="AI Tutor Interface"
                delay={0.1}
              />

              <FeatureCard
                icon={
                  <svg
                    className="w-8 h-8 text-green-600 dark:text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                }
                title="Real‑Time Dashboards"
                description="Track progress, mastery, and compliance from district level to individual learner"
                screenshot="Analytics Dashboard"
                delay={0.2}
              />

              <FeatureCard
                icon={
                  <svg
                    className="w-8 h-8 text-yellow-600 dark:text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15M9 10v4a2 2 0 002 2h2a2 2 0 002-2v-4M9 10H7a2 2 0 00-2 2v4a2 2 0 002 2h2m0-6h6m0 0v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6z"
                    />
                  </svg>
                }
                title="Engaging Enrichment"
                description="Games, videos, and activities tailored to each learner's pace and preferences"
                screenshot="Learning Games"
                delay={0.3}
              />

              <FeatureCard
                icon={
                  <svg
                    className="w-8 h-8 text-indigo-600 dark:text-indigo-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                }
                title="Safe, Role‑Based Chat"
                description="Moderated parent–teacher–learner communication"
                screenshot="Chat Interface"
                delay={0.4}
              />
            </div>
          </div>
        </section>

        {/* Metrics Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-600 to-indigo-600">
          <div className="max-w-7xl mx-auto">
            <FadeInWhenVisible>
              <h2 className="text-4xl font-bold text-white text-center mb-16">
                Proven Results That Matter
              </h2>
            </FadeInWhenVisible>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
              <MetricCard
                icon="📈"
                value={90}
                suffix="%+"
                label="on‑time IEP reviews (up from 62%)"
                delay={0}
              />
              <MetricCard
                icon="🎯"
                value={1}
                suffix="+"
                label="grade‑level gain in just 12 weeks"
                delay={0.2}
              />
              <MetricCard
                icon="❤️"
                prefix="NPS "
                value={65}
                suffix="+"
                label="Parent satisfaction score"
                delay={0.4}
              />
              <MetricCard
                icon="🕒"
                value={7}
                suffix=" days"
                prefix="≤"
                label="Median IEP revision time"
                delay={0.6}
              />
            </div>
          </div>
        </section>

        {/* Audience-Specific Value Blocks */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-800">
          <div className="max-w-7xl mx-auto">
            <FadeInWhenVisible>
              <h2 className="text-4xl font-bold text-gray-900 dark:text-white text-center mb-16">
                Built for Everyone in the Educational Journey
              </h2>
            </FadeInWhenVisible>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <AudienceCard
                title="For Parents"
                description="Live IEP status, teacher chat, and enrichment that makes learning fun."
                icon={
                  <svg
                    className="w-8 h-8 text-blue-600 dark:text-blue-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                    />
                  </svg>
                }
                imageUrl="/assets/images/parent-child-reading.jpg"
                delay={0}
              />

              <AudienceCard
                title="For Teachers"
                description="One dashboard for alerts, interventions, and student progress — less admin, more teaching."
                icon={
                  <svg
                    className="w-8 h-8 text-green-600 dark:text-green-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    />
                  </svg>
                }
                imageUrl="/assets/images/teacher-classroom.jpg"
                delay={0.2}
              />

              <AudienceCard
                title="For Districts"
                description="Unlock IDEA funding and ensure seat utilization with clear, actionable data."
                icon={
                  <svg
                    className="w-8 h-8 text-purple-600 dark:text-purple-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                    />
                  </svg>
                }
                imageUrl="/assets/images/district-admin-analytics.jpg"
                delay={0.4}
              />
            </div>
          </div>
        </section>

        {/* Parent Voice Testimonial */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white dark:bg-gray-900 relative overflow-hidden">
          {/* Background pattern */}
          <div className="absolute inset-0 opacity-5">
            <div
              className="absolute inset-0"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='4'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
              }}
            />
          </div>

          <div className="max-w-4xl mx-auto text-center relative z-10">
            <FadeInWhenVisible>
              <div className="relative">
                <motion.div
                  className="text-8xl text-blue-200 dark:text-blue-800 absolute -top-4 -left-4"
                  initial={{ scale: 0, rotate: -45 }}
                  whileInView={{ scale: 1, rotate: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8, type: 'spring' }}
                >
                  &ldquo;
                </motion.div>

                <blockquote className="text-2xl md:text-3xl text-gray-600 dark:text-gray-300 italic mb-8 relative z-10 leading-relaxed">
                  I spend more time chasing signatures than helping my son read.
                </blockquote>

                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center mr-4">
                    <span className="text-2xl">👩‍💼</span>
                  </div>
                  <div className="text-left">
                    <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                      — Sarah M., Parent
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      Coon Rapids, MN
                    </p>
                  </div>
                </div>

                <motion.p
                  className="text-xl text-blue-600 dark:text-blue-400 font-semibold"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.5 }}
                >
                  Now, she spends that time celebrating his progress.
                </motion.p>
              </div>
            </FadeInWhenVisible>
          </div>
        </section>

        {/* Pricing Section */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-800">
          <div className="max-w-7xl mx-auto">
            <FadeInWhenVisible>
              <div className="text-center mb-16">
                <h2 className="text-4xl font-bold text-gray-900 dark:text-white mb-6">
                  Family‑friendly and district‑smart.
                </h2>
                <p className="text-xl text-gray-600 dark:text-gray-300 mb-4">
                  Transparent family pricing designed for households and
                  districts, with discounts for multiple learners.
                </p>
                <p className="text-lg text-gray-600 dark:text-gray-300">
                  Every new family starts with a{' '}
                  <strong>30-day Premium free trial</strong> (no credit card
                  required).
                </p>
              </div>
            </FadeInWhenVisible>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto mb-16">
              <PricingCard
                title="Basic"
                price="Starting at $19"
                period="/mo"
                features={[
                  'Foundational Reading & Mathematics',
                  'Full IEP workflows',
                  'Limited enrichment content',
                  'Covers first learner',
                  'Monthly IEP and progress reports',
                  'Eligible for sibling & term discounts',
                ]}
                ctaText="Start Free Trial"
                onCtaClick={() => navigate(ROUTES.REGISTER)}
                delay={0}
              />

              <PricingCard
                title="Plus"
                price="Starting at $39"
                period="/mo"
                isPopular={true}
                features={[
                  'All Basic subjects plus:',
                  'Advanced ELA, Extended Math, Science',
                  'Social Studies, SEL, Speech Therapy',
                  'Expanded enrichment & AI insights',
                  'Teacher/parent chat',
                  'Weekly progress reports',
                  'Priority support',
                ]}
                ctaText="Start Free Trial"
                onCtaClick={() => navigate(ROUTES.REGISTER)}
                delay={0.2}
              />

              <PricingCard
                title="Premium"
                price="Starting at $59"
                period="/mo"
                features={[
                  'All Plus subjects plus:',
                  'Computer Science, World Languages',
                  'Creative Arts, Music, Health & PE',
                  'Unlimited enrichment',
                  'Advanced analytics & custom AI',
                  'District-level dashboards',
                  '24/7 dedicated support',
                ]}
                ctaText="Start Free Trial"
                onCtaClick={() => navigate(ROUTES.REGISTER)}
                delay={0.4}
              />
            </div>

            {/* Pricing Details */}
            <FadeInWhenVisible delay={0.6}>
              <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg p-8 mb-12">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 text-center">
                  Pricing Structure & Discounts
                </h3>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Base Fee Structure */}
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      💰 Base Fee Structure
                    </h4>
                    <div className="space-y-3">
                      <p className="text-gray-600 dark:text-gray-300">
                        <strong>Base Fee:</strong> Covers the first learner
                      </p>
                      <p className="text-gray-600 dark:text-gray-300">
                        <strong>Additional Learners:</strong> 10% off each
                        (stackable with term discounts)
                      </p>
                    </div>
                  </div>

                  {/* Term Discounts */}
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      🎯 Term Discounts
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-300">
                          3 months
                        </span>
                        <span className="font-semibold text-green-600">
                          20% off
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-300">
                          6 months
                        </span>
                        <span className="font-semibold text-green-600">
                          30% off
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-300">
                          12 months
                        </span>
                        <span className="font-semibold text-green-600">
                          50% off
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </FadeInWhenVisible>

            {/* Trial Transition Notice */}
            <FadeInWhenVisible delay={0.8}>
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6 text-center">
                <div className="flex items-center justify-center mb-4">
                  <div className="w-12 h-12 bg-blue-100 dark:bg-blue-800 rounded-full flex items-center justify-center mr-3">
                    <svg
                      className="w-6 h-6 text-blue-600 dark:text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <h4 className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                    Trial Transition
                  </h4>
                </div>
                <p className="text-blue-800 dark:text-blue-200">
                  After 30 days, non-upgraded accounts automatically fall back
                  to Basic tier.
                  <strong> All learner data and IEPs remain intact</strong> —
                  you never lose your progress.
                </p>
              </div>
            </FadeInWhenVisible>
          </div>
        </section>

        {/* Closing CTA */}
        <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-600 to-indigo-600 relative overflow-hidden">
          {/* Background elements */}
          <div className="absolute inset-0">
            <motion.div
              className="absolute top-10 left-10 w-40 h-40 bg-white/10 rounded-full"
              animate={{ scale: [1, 1.2, 1], rotate: [0, 180, 360] }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            />
            <motion.div
              className="absolute bottom-10 right-10 w-32 h-32 bg-white/10 rounded-full"
              animate={{ scale: [1.2, 1, 1.2], rotate: [360, 180, 0] }}
              transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
            />
          </div>

          <div className="max-w-4xl mx-auto text-center relative z-10">
            <FadeInWhenVisible>
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-8 leading-tight">
                Ready to close the IEP timeliness gap and re‑ignite learning?
              </h2>

              <div className="flex flex-col items-center gap-6">
                <Button
                  size="xl"
                  className="bg-white hover:bg-gray-100 text-blue-600 px-12 py-4 text-xl font-bold shadow-2xl"
                  onClick={() => navigate(ROUTES.REGISTER)}
                >
                  Get Started — Free 30‑Day Premium Access
                </Button>

                <p className="text-blue-100 text-lg">
                  No credit card required. Keep your data, always.
                </p>
              </div>
            </FadeInWhenVisible>
          </div>
        </section>

        {/* Footer CTA Repeat */}
        <footer className="bg-gray-900 text-white py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <div className="mb-8">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-white text-white hover:bg-white hover:text-gray-900"
                  onClick={() => navigate(ROUTES.REGISTER)}
                >
                  Start Your Free Trial Today
                </Button>
              </div>

              <p className="text-gray-400 mb-4">
                © {new Date().getFullYear()} AIVO AI. All rights reserved.
              </p>

              <div className="flex justify-center space-x-6 text-sm">
                <Link
                  to="/privacy"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  Privacy Policy
                </Link>
                <Link
                  to="/terms"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  Terms of Service
                </Link>
                <Link
                  to="/support"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  Support
                </Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </>
  )
}
