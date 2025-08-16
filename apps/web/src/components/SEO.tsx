import React from 'react'
import { Helmet } from 'react-helmet-async'

interface SEOProps {
  title?: string
  description?: string
  keywords?: string
  image?: string
  url?: string
  type?: string
}

export const SEO: React.FC<SEOProps> = ({
  title = 'AIVO AI - Smarter IEPs, Happier Learners',
  description = 'AIVO AI unites real-time IEP management, adaptive learning, and inclusive enrichment in one safe, FERPA-ready platform — built to serve every child, starting with those who need us most.',
  keywords = 'IEP management, special education, adaptive learning, FERPA compliant, autism support, special needs education, AI tutoring',
  image = '/images/og-image.jpg',
  url = 'https://aivo.ai',
  type = 'website',
}) => {
  const structuredData = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'AIVO AI',
    description: description,
    url: url,
    logo: `${url}/images/logo.png`,
    sameAs: [
      'https://twitter.com/aivoai',
      'https://linkedin.com/company/aivo-ai',
      'https://facebook.com/aivoai',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: '+1-800-AIVO-AI',
      contactType: 'Customer Support',
      areaServed: 'US',
      availableLanguage: 'English',
    },
    address: {
      '@type': 'PostalAddress',
      streetAddress: '123 Education Blvd',
      addressLocality: 'San Francisco',
      addressRegion: 'CA',
      postalCode: '94102',
      addressCountry: 'US',
    },
    product: {
      '@type': 'SoftwareApplication',
      name: 'AIVO AI Platform',
      description:
        'Comprehensive IEP management and adaptive learning platform',
      applicationCategory: 'EducationalApplication',
      operatingSystem: 'Web-based',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
        priceValidUntil: '2025-12-31',
        availability: 'https://schema.org/InStock',
      },
    },
  }

  return (
    <Helmet>
      {/* Basic meta tags */}
      <title>{title}</title>
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      <meta name="author" content="AIVO AI" />
      <meta name="robots" content="index, follow" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />

      {/* Open Graph tags */}
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />
      <meta property="og:url" content={url} />
      <meta property="og:type" content={type} />
      <meta property="og:site_name" content="AIVO AI" />
      <meta property="og:locale" content="en_US" />

      {/* Twitter Card tags */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />
      <meta name="twitter:site" content="@aivoai" />
      <meta name="twitter:creator" content="@aivoai" />

      {/* Additional meta tags */}
      <meta name="theme-color" content="#2563eb" />
      <meta name="apple-mobile-web-app-capable" content="yes" />
      <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      <meta name="apple-mobile-web-app-title" content="AIVO AI" />

      {/* Canonical URL */}
      <link rel="canonical" href={url} />

      {/* Favicon and app icons */}
      <link rel="icon" type="image/x-icon" href="/favicon.ico" />
      <link
        rel="apple-touch-icon"
        sizes="180x180"
        href="/apple-touch-icon.png"
      />
      <link
        rel="icon"
        type="image/png"
        sizes="32x32"
        href="/favicon-32x32.png"
      />
      <link
        rel="icon"
        type="image/png"
        sizes="16x16"
        href="/favicon-16x16.png"
      />
      <link rel="manifest" href="/site.webmanifest" />

      {/* Preconnect to external domains */}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossOrigin="anonymous"
      />

      {/* Google Fonts */}
      <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap"
        rel="stylesheet"
      />

      {/* Structured data */}
      <script type="application/ld+json">
        {JSON.stringify(structuredData)}
      </script>
    </Helmet>
  )
}
