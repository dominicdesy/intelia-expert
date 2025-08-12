/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,

  // 🔧 Configuration pour DigitalOcean - CORRECTION MODE STANDALONE
  // ❌ output: 'standalone', // DÉSACTIVÉ temporairement - cause des conflits avec next start
  trailingSlash: true,

  // ✅ CONFIGURATION CORRIGÉE - Suppression des options obsolètes
  experimental: {
    // ❌ appDir: true, // SUPPRIMÉ - obsolète dans Next.js 14+ (app directory est maintenant stable)
    // ❌ isrMemoryCacheSize: 0, // SUPPRIMÉ - obsolète et remplacé par d'autres options
    
    // ✅ NOUVELLES OPTIONS pour résoudre Supabase Edge Runtime
    serverComponentsExternalPackages: [
      '@supabase/supabase-js',
      '@supabase/realtime-js',
      '@supabase/auth-helpers-nextjs'
    ],
    
    // ✅ Configuration moderne pour les performances
    optimizeCss: true,
    scrollRestoration: true
  },
  
  // ✅ Générer un build ID stable
  generateBuildId: async () => {
    return process.env.VERCEL_GIT_COMMIT_SHA || 'standalone-build'
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

  // ✅ Headers optimisés pour la sécurité et les performances
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
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin'
          },
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          }
        ]
      }
    ]
  },

  // ✅ CONFIGURATION WEBPACK CORRIGÉE pour Supabase Edge Runtime
  webpack: (config, { isServer, dev }) => {
    // Désactiver la minification pour debug en développement
    if (!isServer && process.env.NODE_ENV === 'production') {
      config.optimization.minimize = false
    }
    
    // ✅ CORRECTION PRINCIPALE: Résolution des incompatibilités Supabase
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false,
        url: false,
        zlib: false,
        http: false,
        https: false,
        assert: false,
        os: false,
        path: false,
        util: false,
        process: false, // ✅ AJOUTÉ pour résoudre process.versions dans Supabase
        buffer: false,
        events: false
      }
      
      // ✅ Configuration spéciale pour Supabase Realtime
      config.resolve.alias = {
        ...config.resolve.alias,
        // Évite les conflits avec les modules Node.js dans le navigateur
        'encoding': false,
      }
    }
    
    // ✅ Optimisation pour les modules externes
    config.externals = config.externals || []
    if (isServer) {
      config.externals.push({
        '@supabase/supabase-js': '@supabase/supabase-js',
        '@supabase/realtime-js': '@supabase/realtime-js'
      })
    }
    
    return config
  },

  // ✅ Configuration pour éviter les erreurs de build en production
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },

  // ✅ SCRIPT DE DÉMARRAGE pour Digital Ocean
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [
        {
          source: '/:path*',
          destination: '/:path*',
        },
      ],
    }
  },
}

module.exports = nextConfig