/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Configuration sécurité
  poweredByHeader: false,
  
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