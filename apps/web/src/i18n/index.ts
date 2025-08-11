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
      },
      nav: {
        home: 'Home',
        health: 'Health Check',
        dev_mocks: 'Dev Mocks',
      },
      pages: {
        home: {
          title: 'Aivo Virtual Brains',
          subtitle: 'AI-powered platform for virtual brain simulations',
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
