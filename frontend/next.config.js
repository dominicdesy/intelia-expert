/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Configuration sécurité
  poweredByHeader: false,
  
  // Headers de sécurité globaux
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

  // Optimisation bundle
  experimental: {
    optimizePackageImports: ['lucide-react', '@heroicons/react'],
  },
}

module.exports = nextConfig