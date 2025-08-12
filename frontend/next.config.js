/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,

  // 🔧 FORCER LE MODE SPA - Désactive complètement la génération statique
  output: 'export',
  trailingSlash: true,

  // 🔧 Désactiver complètement le prérendu
  experimental: {
    appDir: true
  },

  // Configuration images - optimisée pour SPA export
  images: {
    domains: [
      'cdrmjshmkdfwwtsfdvbl.supabase.co',
      'avatars.githubusercontent.com'
    ],
    formats: ['image/webp', 'image/avif'],
    unoptimized: true, // Obligatoire pour output: 'export'
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

  // 🔧 Supprimé - Headers et rewrites incompatibles avec output: 'export'
  // En mode export, tout est statique côté client

  // ✅ MINIMAL WEBPACK - AUCUNE MODIFICATION CSS
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
  }
}

module.exports = nextConfig