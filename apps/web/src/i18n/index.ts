import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

const resources = {
  en: {
    translation: {
      common: {
        loading: 'Loading...',
        error: 'An error occurred',
        retry: 'Retry',
        skip_to_content: 'Skip to main content',
        back_to_home: 'Back to Home',
      },
      nav: {
        brand: 'Aivo',
        home: 'Home',
        dashboard: 'Dashboard',
        search: 'Search',
        profile: 'Profile',
        settings: 'Settings',
        logout: 'Logout',
        login: 'Sign In',
        register: 'Sign Up',
        toggle_theme: 'Toggle theme',
        toggle_menu: 'Toggle menu',
        health: 'Health Check',
        dev_mocks: 'Dev Mocks',
        learners: 'My Learners',
        teacher_section: 'Teaching',
        my_classes: 'My Classes',
        students: 'Students',
        assignments: 'Assignments',
        reports: 'Reports',
        district_section: 'District',
        overview: 'Overview',
        schools: 'Schools',
        teachers: 'Teachers',
        district_reports: 'Reports',
        district_settings: 'Settings',
        version: 'Version',
        parent_context: 'Parent Dashboard',
        teacher_context: 'Teacher Dashboard',
        district_context: 'District Dashboard',
        parent_description: "Manage your children's learning journey",
        teacher_description: 'Teach and track student progress',
        district_admin_description:
          'Oversee district-wide educational programs',
      },
      auth: {
        sign_in_title: 'Sign in to your account',
        register_title: 'Create your account',
      },
      dashboard: {
        welcome_back: 'Welcome back, {{name}}!',
        parent_description: "Track your children's progress and achievements",
        teacher_description: 'Manage your classes and student progress',
        district_admin_description:
          'Oversee district performance and analytics',
      },
      onboarding: {
        title: 'Welcome to Aivo',
      },
      learners: {
        title: 'My Learners',
      },
      learner: {
        detail_title: 'Learner Details ({{id}})',
      },
      search: {
        title: 'Search',
      },
      teacher: {
        title: 'Teaching Dashboard',
      },
      district: {
        title: 'District Administration',
      },
      pages: {
        home: {
          title: 'Aivo Virtual Brains',
          subtitle: 'AI-powered platform for personalized learning',
          cta: 'Get Started',
          features: {
            title: 'Key Features',
          },
        },
        health: {
          title: 'Health Check',
          description: 'System health and status information',
        },
        dev_mocks: {
          title: 'Development Mocks',
          description: 'Mock data and testing utilities for development',
        },
        not_found: {
          title: '404 - Page Not Found',
          description: 'The page you are looking for does not exist.',
          go_home: 'Go Home',
        },
      },
    },
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    debug: import.meta.env.DEV,

    interpolation: {
      escapeValue: false, // React already does escaping
    },

    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  })

export default i18n
