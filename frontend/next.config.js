/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuration de base
  poweredByHeader: false,
  reactStrictMode: true,

  // ✅ CORRECTION CRITIQUE: Activer SWC pour minification (swcMinify: false causait l'erreur)
  swcMinify: true,

  trailingSlash: true,
  output: "standalone",
  compress: true,

  // Configuration expérimentale corrigée
  experimental: {
    serverComponentsExternalPackages: ["@supabase/supabase-js"],
    // ✅ SUPPRESSION: appDir (obsolète dans Next.js 13+)
  },

  // Build ID simple
  generateBuildId: async () => {
    return `intelia-expert-${Date.now()}`;
  },

  // Images - configuration stable
  images: {
    domains: [
      "cdrmjshmkdfwwtsfdvbl.supabase.co",
      "avatars.githubusercontent.com",
    ],
    formats: ["image/webp", "image/avif"],
    unoptimized: false,
  },

  // Variables d'environnement - AJOUT de la variable manquante
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
    NEXT_PUBLIC_API_BASE_URL:
      process.env.NEXT_PUBLIC_API_BASE_URL || "https://expert.intelia.com/api",
  },

  // TypeScript et ESLint - garder strict pour détecter les erreurs
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },

  // Headers de sécurité - version simplifiée qui fonctionne
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
        ],
      },
      {
        source: "/api/(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "no-cache, no-store, must-revalidate",
          },
        ],
      },
    ];
  },

  // ✅ WEBPACK CONFIGURATION SIMPLIFIÉE - Évite les erreurs de build
  webpack: (config, { buildId, dev, isServer }) => {
    // Mode développement - source maps simplifiées
    if (dev) {
      config.devtool = "cheap-module-source-map";
    }

    // Mode production - optimisations de base seulement
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        minimize: true, // SWC se charge de la minification
        splitChunks: {
          chunks: "all",
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: "vendors",
              chunks: "all",
            },
          },
        },
      };
    }

    // ✅ FALLBACKS SIMPLIFIÉS - Seulement les essentiels
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false,
        path: false,
      };
    }

    // ✅ SUPPRESSION DES CONFIGURATIONS WEBPACK COMPLEXES qui causaient des erreurs

    // Ignorer les warnings - configuration minimale
    config.ignoreWarnings = [
      {
        module: /node_modules/,
        message: /Critical dependency/,
      },
    ];

    return config;
  },

  // Redirections
  async redirects() {
    return [];
  },

  // Rewrites - URLs corrigées vers expert.intelia.com
  async rewrites() {
    return [
      {
        source: "/api/expert/:path*",
        destination: "https://expert.intelia.com/api/expert/:path*",
      },
      {
        source: "/api/:path*",
        destination: "https://expert.intelia.com/api/:path*",
      },
    ];
  },
};

// Log simplifié
console.log("🚀 Next.js config loaded:", process.env.NODE_ENV);

module.exports = nextConfig;
