/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Configuration sécurité
  poweredByHeader: false,
  
  // Headers de sécurité globaux + CSP pour Zoho SalesIQ
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
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin'
          },
          // ✅ CSP pour autoriser Zoho SalesIQ
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://salesiq.zohopublic.com https://salesiq.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
              "style-src 'self' 'unsafe-inline' https://salesiq.zohopublic.com https://*.zohostatic.com https://*.zohocdn.com",
              "img-src 'self' data: https: blob: https://salesiq.zohopublic.com https://*.zohostatic.com https://*.zohocdn.com",
              "connect-src 'self' https://salesiq.zohopublic.com https://salesiq.zoho.com https://*.zoho.com wss://*.zoho.com https://*.zohostatic.com",
              "frame-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
              "child-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
              "worker-src 'self' blob:",
              "font-src 'self' data: https://*.zohostatic.com https://*.zohocdn.com"
            ].join('; ')
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
      // Domaines Zoho pour les images
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

  // Optimisation bundle + Configuration Supabase
  experimental: {
    optimizePackageImports: ['lucide-react', '@heroicons/react'],
    serverComponentsExternalPackages: ['@supabase/supabase-js']
  },

  // Configuration webpack pour Supabase
  webpack: (config, { isServer }) => {
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
  },
}

module.exports = nextConfig