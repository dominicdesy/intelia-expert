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
  
  // ⚡ Configuration expérimentale - MISE À JOUR pour SSE
  experimental: {
    serverComponentsExternalPackages: [
      '@supabase/supabase-js'
    ],
    // Support amélioré pour les API routes avec streaming
    appDir: true,
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

  // 🌐 Variables d'environnement - AJOUTS pour streaming
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
    // Nouvelles variables pour le streaming
    NEXT_PUBLIC_CHAT_DEBUG_MODE: process.env.NEXT_PUBLIC_CHAT_DEBUG_MODE,
    NEXT_PUBLIC_STREAM_TIMEOUT: process.env.NEXT_PUBLIC_STREAM_TIMEOUT,
    NEXT_PUBLIC_FALLBACK_TO_LEGACY: process.env.NEXT_PUBLIC_FALLBACK_TO_LEGACY,
  },

  // 🔍 Configuration TypeScript
  typescript: {
    ignoreBuildErrors: false,
  },

  // 🔍 Configuration ESLint
  eslint: {
    ignoreDuringBuilds: false,
  },

  // Configuration pour les timeouts de streaming - NOUVEAU
  serverRuntimeConfig: {
    // Timeout pour les API routes (30 secondes)
    maxDuration: 30,
  },

  // 🔒 Headers de sécurité - MISE À JOUR pour SSE
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
              // 🔧 MISE À JOUR: Ajout LLM backend pour streaming
              "connect-src 'self' https://*.supabase.co https://expert.intelia.com https://llm.intelia.ai https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com https://restcountries.com"
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
      },
      // NOUVEAU: Headers spéciaux pour le streaming SSE
      {
        source: '/api/chat/stream',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Connection',
            value: 'keep-alive',
          },
          {
            key: 'Content-Type',
            value: 'text/event-stream',
          },
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'POST, OPTIONS',
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'Content-Type',
          },
        ],
      },
    ]
  },

  // ⚙️ Configuration Webpack simplifiée et robuste - MISE À JOUR pour SSE
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
    
    // 🌐 Fallbacks pour le navigateur - MISE À JOUR pour streaming
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false, // Important pour SSE
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
        buffer: false, // Important pour SSE
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

  // ✨ Rewrites - MISE À JOUR: Distinction entre API legacy et streaming
  async rewrites() {
    return [
      // NOUVEAU: Route spéciale pour le streaming (pas de rewrite)
      // /api/chat/stream reste en local pour gérer le proxy SSE
      
      // Routes API classiques vers le backend Digital Ocean
      {
        source: '/api/expert/:path*',
        destination: 'https://expert-app-cngws.ondigitalocean.app/api/expert/:path*'
      },
      {
        source: '/api/conversations/:path*',
        destination: 'https://expert-app-cngws.ondigitalocean.app/api/conversations/:path*'
      },
      {
        source: '/api/system/:path*',
        destination: 'https://expert-app-cngws.ondigitalocean.app/api/system/:path*'
      },
      {
        source: '/api/stats-fast/:path*',
        destination: 'https://expert-app-cngws.ondigitalocean.app/api/stats-fast/:path*'
      },
      // Fallback pour les autres routes API (sauf streaming)
      {
        source: '/api/((?!chat/stream).*)',
        destination: 'https://expert-app-cngws.ondigitalocean.app/api/$1'
      }
    ]
  },
}

// 📊 Validation de la configuration - MISE À JOUR
console.log('🚀 Next.js config loaded for environment:', process.env.NODE_ENV)
console.log('🔧 SWC compilation: enabled, Terser minification: enabled')
console.log('🖼️ Image optimization:', nextConfig.images.unoptimized ? 'disabled' : 'enabled')
console.log('🔒 CSP updated with expert.intelia.com + llm.intelia.ai support')
console.log('📄 API rewrites configured:')
console.log('   • /api/expert/* → expert-app-cngws.ondigitalocean.app/api/expert/*')
console.log('   • /api/chat/stream → LOCAL (proxy SSE)')
console.log('   • Other /api/* → expert-app-cngws.ondigitalocean.app/api/*')
console.log('🔄 SSE streaming support: enabled')
console.log('⏱️ API timeout: 30 seconds')

module.exports = nextConfig