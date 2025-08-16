import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { ROUTES } from '@/types/routes'
import { useAuth } from '@/app/providers/AuthProvider'
import { useEffect } from 'react'
import { AivoLogo } from '@/components/ui/AivoLogo'

export default function Landing() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate(ROUTES.DASHBOARD)
    }
  }, [isAuthenticated, navigate])

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Navigation */}
      <nav className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <AivoLogo className="w-10 h-10" />
          <div className="flex items-center space-x-4">
            <Link
              to={ROUTES.LOGIN}
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
              data-testid="nav-login-link"
            >
              {t('auth.sign_in')}
            </Link>
            <Link
              to={ROUTES.REGISTER}
              className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              data-testid="nav-register-link"
            >
              {t('auth.get_started')}
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section - Impact on arrival */}
      <section className="relative bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
        {/* Background classroom image overlay */}
        <div className="absolute inset-0 opacity-10">
          <div className="w-full h-full bg-gradient-to-r from-blue-600/20 to-indigo-600/20"></div>
        </div>

        <div className="relative max-w-7xl mx-auto text-center">
          {/* Hero headline */}
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white sm:text-5xl md:text-6xl leading-tight">
            <span className="block">Smarter IEPs.</span>
            <span className="block text-primary-600 dark:text-primary-400">
              Happier Learners.
            </span>
          </h1>

          {/* Hero description */}
          <p className="mt-6 text-xl text-gray-600 dark:text-gray-300 max-w-4xl mx-auto leading-relaxed">
            AIVO AI unites real‑time IEP management, adaptive learning, and
            inclusive enrichment in one safe, FERPA‑ready platform — built to
            serve every child, starting with those who need us most.
          </p>

          {/* Primary CTA */}
          <div className="mt-10 flex flex-col items-center gap-4">
            <Link
              to={ROUTES.REGISTER}
              className="bg-primary-600 hover:bg-primary-700 text-white px-12 py-4 rounded-lg text-xl font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 shadow-lg hover:shadow-xl transform hover:-translate-y-1 hover:scale-105"
              data-testid="hero-cta-register"
            >
              Start Your Free 30‑Day Premium Trial
            </Link>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No credit card required. Keep every IEP, lesson, and progress
              record — even if you don't upgrade.
            </p>
          </div>
        </div>
      </section>

      {/* Challenge Section - Make them feel understood */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-800">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-lg text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">
                Every delayed IEP review means lost learning time. Every generic
                lesson risks leaving a child behind.
              </p>
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
                AIVO AI closes the gaps that hurt growth and compliance:
              </h2>
            </div>

            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-12 h-12 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center">
                  <span className="text-2xl">⏳</span>
                </div>
                <p className="text-gray-600 dark:text-gray-300 flex-1">
                  Months‑late IEP reviews costing districts funding and students
                  progress
                </p>
              </div>

              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-12 h-12 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
                  <span className="text-2xl">🧩</span>
                </div>
                <p className="text-gray-600 dark:text-gray-300 flex-1">
                  Fragmented tools forcing teachers into endless data re‑entry
                </p>
              </div>

              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-12 h-12 bg-yellow-100 dark:bg-yellow-900 rounded-lg flex items-center justify-center">
                  <span className="text-2xl">😔</span>
                </div>
                <p className="text-gray-600 dark:text-gray-300 flex-1">
                  Disengaged learners facing one‑size‑fits‑all content
                </p>
              </div>

              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-12 h-12 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center">
                  <span className="text-2xl">💸</span>
                </div>
                <p className="text-gray-600 dark:text-gray-300 flex-1">
                  Per‑subject fees pushing families and districts beyond budget
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Section - Show the transformation */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white dark:bg-gray-900">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
            A single, integrated platform where compliance, instruction, and
            engagement work in sync
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-16">
            So teachers teach, parents participate, and learners thrive.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-8">
            {/* Dynamic IEP Engine */}
            <div className="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mx-auto mb-4">
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
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Dynamic IEP Engine
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Automatic deadline alerts, dual e‑signatures, immutable audit
                logs
              </p>
            </div>

            {/* Adaptive AI Tutors */}
            <div className="bg-purple-50 dark:bg-purple-900/20 p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center mx-auto mb-4">
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
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Adaptive AI Tutors
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                "Main Brain" coordinates subject‑specific learning from ELA to
                SEL, Science, Math, Languages, and more
              </p>
            </div>

            {/* Real-Time Dashboards */}
            <div className="bg-green-50 dark:bg-green-900/20 p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center mx-auto mb-4">
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
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Real‑Time Dashboards
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Track progress, mastery, and compliance from district level to
                individual learner
              </p>
            </div>

            {/* Engaging Enrichment */}
            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-yellow-100 dark:bg-yellow-900 rounded-lg flex items-center justify-center mx-auto mb-4">
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
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Engaging Enrichment
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Games, videos, and activities tailored to each learner's pace
                and preferences
              </p>
            </div>

            {/* Safe, Role-Based Chat */}
            <div className="bg-indigo-50 dark:bg-indigo-900/20 p-6 rounded-xl hover:shadow-lg transition-shadow">
              <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900 rounded-lg flex items-center justify-center mx-auto mb-4">
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
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Safe, Role‑Based Chat
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Moderated parent–teacher–learner communication
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Metrics Section - Back it with proof */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-primary-600 dark:bg-primary-700">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 text-center">
            <div className="text-white">
              <div className="text-4xl font-bold mb-2">📈 90%+</div>
              <p className="text-primary-100">
                on‑time IEP reviews (up from 62%)
              </p>
            </div>
            <div className="text-white">
              <div className="text-4xl font-bold mb-2">🎯 1+</div>
              <p className="text-primary-100">
                grade‑level gain in just 12 weeks
              </p>
            </div>
            <div className="text-white">
              <div className="text-4xl font-bold mb-2">❤️ NPS 65+</div>
              <p className="text-primary-100">Parent satisfaction score</p>
            </div>
            <div className="text-white">
              <div className="text-4xl font-bold mb-2">🕒 ≤7 days</div>
              <p className="text-primary-100">Median IEP revision time</p>
            </div>
          </div>
        </div>
      </section>

      {/* Audience-Specific Value Blocks */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-800">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* For Parents */}
            <div className="bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
              <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mb-6">
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
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                For Parents
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Live IEP status, teacher chat, and enrichment that makes
                learning fun.
              </p>
            </div>

            {/* For Teachers */}
            <div className="bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center mb-6">
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
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                For Teachers
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                One dashboard for alerts, interventions, and student progress —
                less admin, more teaching.
              </p>
            </div>

            {/* For Districts */}
            <div className="bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
              <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center mb-6">
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
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                For Districts
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Unlock IDEA funding and ensure seat utilization with clear,
                actionable data.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Parent Voice - Humanize it */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white dark:bg-gray-900">
        <div className="max-w-4xl mx-auto text-center">
          <div className="relative">
            <div className="text-6xl text-primary-200 dark:text-primary-800 absolute -top-4 -left-4">
              "
            </div>
            <blockquote className="text-2xl text-gray-600 dark:text-gray-300 italic mb-8 relative z-10">
              I spend more time chasing signatures than helping my son read.
            </blockquote>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              — Parent, Coon Rapids, MN
            </p>
            <p className="text-lg text-primary-600 dark:text-primary-400 font-medium">
              Now, she spends that time celebrating his progress.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing Snapshot */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-800">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Family‑friendly and district‑smart.
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-12">
            Transparent plans, sibling discounts, and an always‑free Basic tier
            after your trial.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Basic Plan */}
            <div className="bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg border-2 border-gray-200 dark:border-gray-700">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Basic
              </h3>
              <div className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
                Free
              </div>
              <Link
                to={ROUTES.REGISTER}
                className="block w-full bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                Start Free Trial
              </Link>
            </div>

            {/* Plus Plan */}
            <div className="bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg border-2 border-primary-500 relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-primary-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                Most Popular
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Plus
              </h3>
              <div className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
                $29/mo
              </div>
              <Link
                to={ROUTES.REGISTER}
                className="block w-full bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                Start Free Trial
              </Link>
            </div>

            {/* Premium Plan */}
            <div className="bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg border-2 border-gray-200 dark:border-gray-700">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Premium
              </h3>
              <div className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
                $49/mo
              </div>
              <Link
                to={ROUTES.REGISTER}
                className="block w-full bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                Start Free Trial
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-primary-600 dark:bg-primary-700">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-8">
            Ready to close the IEP timeliness gap and re‑ignite learning?
          </h2>

          <div className="flex flex-col items-center gap-4">
            <Link
              to={ROUTES.REGISTER}
              className="bg-white hover:bg-gray-100 text-primary-600 px-12 py-4 rounded-lg text-xl font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 shadow-lg hover:shadow-xl transform hover:-translate-y-1"
              data-testid="closing-cta-register"
            >
              Get Started — Free 30‑Day Premium Access
            </Link>
            <p className="text-primary-100 text-sm">
              No credit card required. Keep your data, always.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <p className="text-gray-400">
              © {new Date().getFullYear()} AIVO AI. All rights reserved.
            </p>
            <div className="mt-4 space-x-6">
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
  )
}
