/** @type {import('next').NextConfig} */
const nextConfig = {
  // ✅ Déjà optimisé pour Docker
  output: 'standalone',
  
  // ✅ Configuration sécurité
  poweredByHeader: false,
  
  // ✅ Optimisation compilation - NOUVELLES OPTIMISATIONS
  swcMinify: true, // SWC plus rapide que Terser
  compress: true,  // Compression gzip intégrée
  
  // ✅ HEADERS SIMPLIFIÉS avec optimisations performance
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          // Cache agressif pour les assets statiques
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      // Cache spécifique pour les pages
      {
        source: '/((?!api).*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
        ],
      },
    ]
  },

  // ✅ Configuration images optimisées avec performance
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
    // Optimisations build performance
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 60 * 60 * 24 * 365, // 1 an de cache
  },

  // ✅ Variables d'environnement exposées
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
  },

  // ✅ Configuration TypeScript avec optimisations
  typescript: {
    ignoreBuildErrors: false,
    // Optimisation: type checking en parallèle
    tsconfigPath: './tsconfig.json',
  },

  // ✅ Configuration ESLint optimisée
  eslint: {
    ignoreDuringBuilds: false,
    // Optimisation: ESLint en parallèle
    dirs: ['src', 'app', 'components', 'lib'],
  },

  // ✅ NOUVELLES OPTIMISATIONS EXPERIMENTALES pour build
  experimental: {
    // Imports optimisés
    optimizePackageImports: ['lucide-react', '@heroicons/react', '@supabase/supabase-js'],
    serverComponentsExternalPackages: ['@supabase/supabase-js'],
    
    // Nouvelles optimisations build performance
    swcTraceProfiling: true,        // Profiling SWC pour debug perfs
    optimizeCss: true,              // Optimisation CSS
    esmExternals: true,             // ESM external modules
    turbotrace: {                   // Optimisation trace dependencies
      logLevel: 'error',
      logAll: false,
    },
    
    // Cache compilation
    incrementalCacheHandlerPath: require.resolve('./cache-handler.js'),
  },

  // ✅ Configuration webpack OPTIMISÉE pour build rapide
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

    // NOUVELLES OPTIMISATIONS WEBPACK
    if (!dev) {
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
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              priority: 5,
            },
          },
        },
      }

      // Optimisation resolution pour build plus rapide
      config.resolve.modules = ['node_modules']
      config.resolve.symlinks = false
      
      // Cache webpack
      config.cache = {
        type: 'filesystem',
        buildDependencies: {
          config: [__filename],
        },
      }
    }

    // Optimisation parallélisation
    config.parallelism = require('os').cpus().length

    return config
  },

  // ✅ NOUVELLES configurations pour optimiser le build
  onDemandEntries: {
    // Temps avant suppression pages en dev
    maxInactiveAge: 60 * 1000, // 1 minute
    // Pages gardées simultanément
    pagesBufferLength: 5,
  },

  // Optimisation compilation
  compiler: {
    // Suppression console.log en production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },

  // Configuration tracing pour debug performance
  ...(process.env.ANALYZE === 'true' && {
    experimental: {
      ...nextConfig.experimental,
      webpackBuildWorker: true, // Build en worker séparé
    }
  }),
}

module.exports = nextConfig