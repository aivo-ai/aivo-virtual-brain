import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// Translation resources - simplified for now to fix immediate issue
const resources = {
  en: {
    translation: {
      common: {
        loading: "Loading...",
        error: "Error",
        success: "Success",
        cancel: "Cancel",
        save: "Save",
        submit: "Submit",
        yes: "Yes",
        no: "No"
      },
      auth: {
        login: "Sign In",
        register: "Sign Up",
        email: "Email",
        password: "Password",
        confirmPassword: "Confirm Password",
        
        remember_me: "Remember me",
        forgot_password: "Forgot password?",
        or_continue_with: "Or continue with",
        
        create_account_title: "Create Your Account",
        create_account_subtitle: "Join AIVO to personalize your learning experience",
        sign_in_link: "Sign in here",
        sign_in_title: "Welcome Back",
        sign_in_subtitle: "Don't have an account?",
        sign_up_link: "Sign up here",
        
        first_name_label: "First Name",
        first_name_placeholder: "Enter your first name",
        last_name_label: "Last Name", 
        last_name_placeholder: "Enter your last name",
        email_label: "Email Address",
        email_placeholder: "Enter your email address",
        password_label: "Password",
        password_placeholder: "Create a secure password",
        confirm_password_label: "Confirm Password",
        confirm_password_placeholder: "Confirm your password",
        
        agree_to: "I agree to the",
        terms_of_service: "Terms of Service", 
        and: "and",
        privacy_policy: "Privacy Policy",
        create_account: "Create Account",
        or_register_with: "Or sign up with",
        
        verify_2fa_title: "Two-Factor Authentication",
        verify_2fa_subtitle: "Enter the 6-digit code from your authenticator app",
        
        errors: {
          invalid_credentials: "Invalid email or password",
          network_error: "Network error. Please try again.",
          invalid_2fa_code: "Invalid verification code"
        }
      },
      navigation: {
        dashboard: "Dashboard",
        learners: "Learners", 
        analytics: "Analytics",
        assessments: "Assessments",
        settings: "Settings",
        help: "Help",
        logout: "Sign Out",
        profile: "Profile",
        login: "Login",
        home: "Home",
        search: "Search"
      },
      pages: {
        home: {
          title: "Welcome to Aivo",
          subtitle: "Advanced AI-powered virtual brain simulation platform for education and research",
          features: {
            title: "Platform Features"
          }
        }
      },
      dashboard: {
        welcome_back: "Welcome back, {{name}}!",
        teacher_description: "Manage your students, assignments, and track progress.",
        parent_description: "View your child's progress and communicate with teachers.",
        student_description: "Access your lessons, assignments, and track your learning journey.",
        admin_description: "Oversee school operations, users, and system analytics.",
        district_description: "Monitor district-wide performance and compliance metrics."
      }
    }
  }
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    debug: import.meta.env.DEV,
    
    interpolation: {
      escapeValue: false, // react already does escaping
    },
    
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    
    // Configure namespace
    defaultNS: 'translation',
    ns: ['translation'],
  })

export default i18n
