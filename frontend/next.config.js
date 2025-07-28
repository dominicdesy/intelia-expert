/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Configuration sécurité
  poweredByHeader: false,
  
  // ✅ Optimisations de build ajoutées
  swcMinify: true,
  compress: true,
  
  // ✅ HEADERS SIMPLIFIÉS - CSP maintenant gérée par middleware.ts
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          // CSP supprimée - maintenant gérée par middleware.ts
          // Autres headers de sécurité conservés mais optionnels (redondant avec middleware)
        ],
      },
    ]
  },

  // Configuration images optimisées
  images: {
    domains: [
      'cdrmjshmkdfwwtsfdvbl.supabase.co',
      'avatars.githubusercontent.com',
      // Domaines Zoho pour les images
      'salesiq.zohopublic.com',
      'zohostatic.com',
      'zohocdn.com'
    ],
    formats: ['image/webp', 'image/avif'],
    // Optimisations performance
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
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

  // Optimisation bundle + Configuration Supabase
  experimental: {
    optimizePackageImports: ['lucide-react', '@heroicons/react'],
    serverComponentsExternalPackages: ['@supabase/supabase-js'],
    // ✅ Nouvelles optimisations
    swcTraceProfiling: true,
    optimizeCss: true,
    esmExternals: true,
    // ❌ LIGNE PROBLÉMATIQUE SUPPRIMÉE
    // incrementalCacheHandlerPath: require.resolve('./cache-handler.js'),
  },

  // Configuration webpack pour Supabase + optimisations
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Configuration Supabase existante
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
      }
    }

    // ✅ Optimisations webpack ajoutées
    if (!dev) {
      // Cache webpack pour builds plus rapides
      config.cache = {
        type: 'filesystem',
        buildDependencies: {
          config: [__filename],
        },
      }

      // Optimisation bundle splitting
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          minSize: 20000,
          maxSize: 244000,
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
              priority: 10,
            },
            supabase: {
              test: /[\\/]node_modules[\\/]@supabase[\\/]/,
              name: 'supabase',
              chunks: 'all',
              priority: 20,
            },
          },
        },
      }

      // Optimisation résolution
      config.resolve.modules = ['node_modules']
      config.resolve.symlinks = false
    }

    // Utiliser tous les CPU cores
    config.parallelism = require('os').cpus().length

    return config
  },

  // ✅ Optimisation compilation
  compiler: {
    // Suppression console.log en production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },
}

module.exports = nextConfig