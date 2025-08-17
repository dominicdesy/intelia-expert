/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,

  // 🔧 Configuration pour DigitalOcean
  trailingSlash: true,

  // ✅ CONFIGURATION SIMPLIFIÉE - Suppression des options obsolètes
  experimental: {
    // ❌ Supprimé: appDir, isrMemoryCacheSize (obsolètes dans Next.js 14+)
    
    // ✅ Configuration minimale pour Supabase
    serverComponentsExternalPackages: [
      '@supabase/supabase-js'
    ]
  },
  
  // ✅ Générer un build ID simple
  generateBuildId: async () => {
    return 'intelia-expert-build'
  },

  // Configuration images
  images: {
    domains: [
      'cdrmjshmkdfwwtsfdvbl.supabase.co',
      'avatars.githubusercontent.com'
    ],
    formats: ['image/webp', 'image/avif'],
    unoptimized: process.env.NODE_ENV === 'production',
  },

  // Variables d'environnement
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

  // Headers de sécurité
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate'
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          }
        ]
      }
    ]
  },

  // ✅ CONFIGURATION WEBPACK SIMPLIFIÉE - Résout juste les incompatibilités critiques
  webpack: (config, { isServer }) => {
    // Désactiver la minification pour debug
    if (!isServer && process.env.NODE_ENV === 'production') {
      config.optimization.minimize = false
    }
    
    // ✅ CORRECTION MINIMALE pour Supabase - Seulement les polyfills nécessaires
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false,
        process: false, // ✅ Résout process.versions dans Supabase Realtime
      }
    }
    
    // ❌ SUPPRIMÉ: config.externals qui causait l'erreur
    // ❌ SUPPRIMÉ: config.resolve.alias qui causait des conflits
    
    return config
  }
}

module.exports = nextConfig