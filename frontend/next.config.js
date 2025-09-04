// next.config

/** @type {import('next').NextConfig} */
const nextConfig = {
  // 🔧 Configuration de base
  poweredByHeader: false,
  reactStrictMode: true,
  
  // 🎯 Terser pour minification (SWC reste pour compilation)
  swcMinify: false,
  
  trailingSlash: true,

  // 🐳 Configuration Docker
  output: 'standalone',

  // 🚀 Optimisations pour Digital Ocean
  compress: true,
  
  // ⚡ Configuration expérimentale minimale
  experimental: {
    serverComponentsExternalPackages: [
      '@supabase/supabase-js'
    ]
  },
  
  // 🏷️ Build ID simple et prévisible
  generateBuildId: async () => {
    return `intelia-expert-${Date.now()}`
  },

  // 🖼️ Configuration des images - CORRECTION IMPORTANTE
  images: {
    domains: [
      'cdrmjshmkdfwwtsfdvbl.supabase.co',
      'avatars.githubusercontent.com'
    ],
    formats: ['image/webp', 'image/avif'],
    // 🔧 CORRECTION: Garder l'optimisation d'images en production
    unoptimized: false, // Était: process.env.NODE_ENV === 'production'
  },

  // 🌍 Variables d'environnement
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
  },

  // 📝 Configuration TypeScript
  typescript: {
    ignoreBuildErrors: false,
  },

  // 📝 Configuration ESLint
  eslint: {
    ignoreDuringBuilds: false,
  },

  // 🔐 Headers de sécurité
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
              // 🔧 CORRECTION: Ajout de https://expert.intelia.com
              "connect-src 'self' https://*.supabase.co https://expert.intelia.com https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com https://restcountries.com"

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

  // ⚙️ Configuration Webpack simplifiée et robuste
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    
    // 🛠 Mode développement
    if (dev) {
      config.devtool = 'cheap-module-source-map'
    }
    
    // 🏭 Mode production - optimisations avec Terser
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        minimize: true, // Utilise Terser (swcMinify: false)
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
    
    // 🌐 Fallbacks pour le navigateur
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

    // 🚫 Ignorer les warnings
    config.ignoreWarnings = [
      {
        module: /node_modules/,
        message: /Critical dependency/,
      },
      {
        module: /node_modules/,
        message: /Can't resolve/,
      }
    ]

    return config
  },

  // 📄 Redirections
  async redirects() {
    return []
  },

  // ✨ Rewrites - NOUVEAU: Redirection API vers backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://expert-app-cngws.ondigitalocean.app/api/:path*'
      }
    ]
  },
}

// 📊 Validation de la configuration
console.log('🚀 Next.js config loaded for environment:', process.env.NODE_ENV)
console.log('🔧 SWC compilation: enabled, Terser minification: enabled')
console.log('🖼️ Image optimization:', nextConfig.images.unoptimized ? 'disabled' : 'enabled')
console.log('🔐 CSP updated with expert.intelia.com support')
console.log('🔄 API rewrites configured: /api/* → expert-app-cngws.ondigitalocean.app/api/*')

module.exports = nextConfig