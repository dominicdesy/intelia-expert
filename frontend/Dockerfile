/** @type {import('next').NextConfig} */
const nextConfig = {
  // 🔧 Configuration de base
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,
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

  // 📝 Configuration TypeScript
  typescript: {
    ignoreBuildErrors: false,
  },

  // 📝 Configuration ESLint
  eslint: {
    ignoreDuringBuilds: false,
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
          // ✅ AJOUT DE LA CSP POUR AUTORISER RESTCOUNTRIES.COM
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

  // ⚙️ Configuration Webpack MINIMALISTE et SÉCURISÉE
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    
    // 🛠 Mode développement - configurations de debug
    if (dev) {
      config.devtool = 'cheap-module-source-map'
    }
    
    // 🏭 Mode production - optimisations
    if (!dev && !isServer) {
      // Optimisations légères pour la production
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

    // 🚫 Ignorer les warnings spécifiques
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

    // 📊 Analyse du bundle en développement
    if (dev && process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer')
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'server',
          openAnalyzer: true,
        })
      )
    }

    return config
  },

  // 📄 Redirections pour compatibilité
  async redirects() {
    return [
      // Exemple de redirection si nécessaire
      // {
      //   source: '/old-path',
      //   destination: '/new-path',
      //   permanent: true,
      // },
    ]
  },

  // ✨ Rewrites pour l'API si nécessaire
  async rewrites() {
    return [
      // Exemple de rewrite si nécessaire
      // {
      //   source: '/api/external/:path*',
      //   destination: 'https://external-api.com/:path*',
      // },
    ]
  },
}

// 📝 Validation de la configuration
console.log('🚀 Next.js config loaded for environment:', process.env.NODE_ENV)

module.exports = nextConfig