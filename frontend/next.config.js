/** @type {import('next').NextConfig} */
const nextConfig = {
  // 🔧 Configuration de base
  poweredByHeader: false,
  reactStrictMode: true,
  
  // 🚨 SOLUTION: SWC avec fallback gracieux
  swcMinify: process.env.DISABLE_SWC !== 'true', // Peut être désactivé via env
  
  trailingSlash: true,

  // 🐳 Configuration Docker
  output: 'standalone',

  // 🚀 Optimisations pour Digital Ocean
  compress: true,
  
  // ⚡ Configuration expérimentale minimale avec SWC options
  experimental: {
    serverComponentsExternalPackages: [
      '@supabase/supabase-js'
    ],
    // 🔧 Options SWC spécifiques pour Docker
    swcPlugins: [], // Pas de plugins SWC custom
    forceSwcTransforms: false, // Laisse Next.js décider
  },
  
  // 🏷️ Build ID simple et prévisible
  generateBuildId: async () => {
    return `intelia-expert-${Date.now()}`
  },

  // 🖼️ Configuration des images
  images: {
    domains: [
      'cdrmjshmkdfwwtsfdvbl.supabase.co',
      'avatars.githubusercontent.com'
    ],
    formats: ['image/webp', 'image/avif'],
    unoptimized: process.env.NODE_ENV === 'production',
  },

  // 🌍 Variables d'environnement
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
  },

  // 📝 Configuration TypeScript - Plus permissive en cas de problème
  typescript: {
    ignoreBuildErrors: process.env.IGNORE_TS_ERRORS === 'true',
  },

  // 📝 Configuration ESLint - Plus permissive en cas de problème
  eslint: {
    ignoreDuringBuilds: process.env.IGNORE_ESLINT === 'true',
  },

  // 🔒 Headers de sécurité
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
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
          },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "connect-src 'self' https://*.supabase.co https://expert-app-cngws.ondigitalocean.app https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com https://restcountries.com"
            ].join('; ')
          }
        ]
      },
      {
        source: '/api/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate'
          }
        ]
      }
    ]
  },

  // ⚙️ Configuration Webpack ROBUSTE avec fallback
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    
    // 🛠 Mode développement - configurations de debug
    if (dev) {
      config.devtool = 'cheap-module-source-map'
    }
    
    // 🏭 Mode production - optimisations avec fallback Babel si SWC fail
    if (!dev && !isServer) {
      // 🔄 Fallback Babel si SWC indisponible
      if (process.env.DISABLE_SWC === 'true') {
        config.module.rules.push({
          test: /\.(js|jsx|ts|tsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: ['next/babel'],
              cacheDirectory: true,
            },
          },
        })
      }
      
      config.optimization = {
        ...config.optimization,
        minimize: true,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
            },
          },
        },
      }
    }
    
    // 🌍 Fallbacks pour le navigateur (Supabase uniquement)
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false,
        process: false,
        path: false,
        os: false,
        url: false,
        util: false,
        querystring: false,
        punycode: false,
        http: false,
        https: false,
        zlib: false,
        assert: false,
        buffer: false,
        constants: false,
      }
    }

    // 📦 Alias pour optimiser les imports
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, './'),
    }

    // 🔧 Règles de modules pour la compatibilité
    config.module.rules.push({
      test: /\.m?js$/,
      type: 'javascript/auto',
      resolve: {
        fullySpecified: false,
      },
    })

    // 🚫 Ignorer les warnings spécifiques + SWC warnings
    config.ignoreWarnings = [
      {
        module: /node_modules/,
        message: /Critical dependency/,
      },
      {
        module: /node_modules/,
        message: /Can't resolve/,
      },
      // 🚨 Ignorer les erreurs SWC qui ne bloquent pas le build
      {
        message: /SWC.*failed/,
      },
      {
        message: /TAR_ABORT/,
      }
    ]

    // 📊 Analyse du bundle en développement
    if (dev && process.env.ANALYZE === 'true') {
      try {
        const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer')
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'server',
            openAnalyzer: true,
          })
        )
      } catch (e) {
        console.warn('Bundle analyzer not available:', e.message)
      }
    }

    return config
  },

  // 🚨 Configuration de compilation avec retry logic
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },

  // 📄 Redirections pour compatibilité
  async redirects() {
    return []
  },

  // ✨ Rewrites pour l'API si nécessaire
  async rewrites() {
    return []
  },
}

// 🔍 Validation de la configuration
console.log('🚀 Next.js config loaded for environment:', process.env.NODE_ENV)
console.log('🔧 SWC enabled:', nextConfig.swcMinify)

module.exports = nextConfig