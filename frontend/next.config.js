/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,

  // 🔧 Configuration pour DigitalOcean - Mode standalone
  output: 'standalone',
  trailingSlash: true,

  // 🔧 DÉSACTIVER COMPLÈTEMENT LA GÉNÉRATION STATIQUE
  experimental: {
    appDir: true,
    isrMemoryCacheSize: 0, // Désactive ISR
  },
  
  // 🔧 Générer aucune page statique
  generateBuildId: async () => {
    return 'no-static-pages'
  },

  // Configuration images - optimisée pour standalone
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

  // 🔧 Headers pour éviter le cache
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

  // ✅ MINIMAL WEBPACK - AUCUNE MODIFICATION CSS
  webpack: (config, { isServer }) => {
    // Désactiver la minification pour debug
    if (!isServer && process.env.NODE_ENV === 'production') {
      config.optimization.minimize = false
    }
    
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
      }
    }
    return config
  }
}

module.exports = nextConfig