/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Configuration sécurité
  poweredByHeader: false,
  
  // Headers simplifiés
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Accept-CH',
            value: 'Sec-CH-Prefers-Color-Scheme'
          }
        ],
      },
    ]
  },

  // Configuration images optimisées
  images: {
    domains: [
      'cdrmjshmkdfwwtsfdvbl.supabase.co',
      'avatars.githubusercontent.com',
      'salesiq.zohopublic.com',
      'zohostatic.com',
      'zohocdn.com'
    ],
    formats: ['image/webp', 'image/avif'],
  },

  // Variables d'environnement exposées
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
  },

  // Configuration TypeScript
  typescript: {
    ignoreBuildErrors: false,
  },

  // Configuration ESLint
  eslint: {
    ignoreDuringBuilds: false,
  },

  // Configuration experimentale optimisée
  experimental: {
    optimizePackageImports: ['lucide-react', '@heroicons/react'],
    serverComponentsExternalPackages: ['@supabase/supabase-js'],
    optimizeCss: true,
    scrollRestoration: true
  },

  // ✅ WEBPACK SIMPLIFIÉ - SANS REDÉFINITION CSS
  webpack: (config, { isServer }) => {
    // Résolution des modules pour Supabase et autres packages
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
      }
    }

    // ✅ PAS DE REDÉFINITION DES RÈGLES CSS - Next.js gère PostCSS automatiquement
    // La configuration PostCSS est prise depuis postcss.config.js

    return config
  },

  // Configuration production
  ...(process.env.NODE_ENV === 'production' && {
    compress: true,
    generateEtags: false,
    distDir: '.next'
  })
}

module.exports = nextConfig