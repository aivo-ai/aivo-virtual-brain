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
        brand: 'AIVO',
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
        parent_description: "Support your child's unique learning needs",
        teacher_description: 'Empower special needs education with AI',
        district_admin_description:
          'Advanced tools for inclusive education programs',
      },
      auth: {
        sign_in_title: 'Welcome back to AIVO',
        register_title: 'Join the AIVO Community',
        sign_in: 'Sign In',
        get_started: 'Get Started',
      },
      dashboard: {
        welcome_back: 'Welcome back, {{name}}!',
        parent_description: "Track your children's progress and achievements",
        teacher_description: 'Manage your classes and student progress',
        district_admin_description:
          'Oversee district performance and analytics',
      },
      onboarding: {
        title: 'Welcome to AIVO',
      },
      landing: {
        hero: {
          title_line1: 'Empowering Every Child',
          title_line2: 'with AI-Driven Learning',
          description:
            'AIVO is an innovative agentic AI platform designed to help children with Autism and special needs learn, grow, and thrive through personalized, adaptive educational experiences.',
          cta_primary: 'Start Your Journey',
          cta_secondary: 'Learn More',
          trust_indicator:
            'Trusted by educators, therapists, and families worldwide',
        },
        features: {
          title: 'How AIVO Makes a Difference',
          subtitle:
            'Comprehensive AI-powered tools designed specifically for special needs education',
          feature1: {
            title: 'Personalized Learning Paths',
            description:
              "AI agents create custom learning experiences tailored to each child's unique needs, abilities, and learning style.",
          },
          feature2: {
            title: 'Adaptive Assessments',
            description:
              'Continuous, gentle assessments that adapt in real-time to support progress without causing stress or anxiety.',
          },
          feature3: {
            title: 'Progress Insights',
            description:
              'Detailed analytics and insights for parents, teachers, and therapists to track growth and adjust support strategies.',
          },
        },
        testimonials: {
          title: 'Success Stories from Our Community',
        },
        final_cta: {
          title: 'Ready to Transform Learning?',
          subtitle:
            "Join thousands of families and educators using AIVO to unlock every child's potential.",
          button: 'Get Started Today',
        },
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
          title: 'AIVO - Agentic AI for Special Needs',
          subtitle:
            'Empowering children with Autism and special needs through personalized AI-driven learning experiences',
          cta: 'Get Started',
          features: {
            title: 'How AIVO Helps',
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
