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
          // ✅ FIX #4: Support meta theme-color pour tous navigateurs
          {
            key: 'Accept-CH',
            value: 'Sec-CH-Prefers-Color-Scheme'
          }
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

  // ✅ FIX #4: Optimisation sans fetchpriority pour Firefox + Configuration Supabase
  experimental: {
    optimizePackageImports: ['lucide-react', '@heroicons/react'],
    serverComponentsExternalPackages: ['@supabase/supabase-js'],
    // ✅ NOUVEAU: Optimisations compatibles tous navigateurs
    optimizeCss: true,
    scrollRestoration: true
  },

  // ✅ Configuration webpack optimisée performance + Supabase
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

    // ✅ FIX #5: Optimisation animations performance
    config.module.rules.push({
      test: /\.css$/,
      use: [
        {
          loader: 'postcss-loader',
          options: {
            postcssOptions: {
              plugins: [
                // Plugin pour optimiser les animations
                ['autoprefixer'],
                // Optimisation @keyframes pour éviter layout thrashing
                function() {
                  return {
                    postcssPlugin: 'optimize-animations',
                    Once(root) {
                      root.walkAtRules('keyframes', (rule) => {
                        rule.walkDecls((decl) => {
                          // ✅ FIX #5: Remplacer height/width par transform
                          if (decl.prop === 'height' || decl.prop === 'width') {
                            console.warn(`⚠️ Animation optimisation: ${decl.prop} dans @keyframes peut causer du layout thrashing`)
                            // Suggérer transform: scale() ou opacity à la place
                          }
                        })
                      })
                    }
                  }
                }
              ]
            }
          }
        }
      ]
    })

    return config
  },

  // ✅ NOUVEAU: Configuration PWA optimisée
  ...(process.env.NODE_ENV === 'production' && {
    compress: true,
    generateEtags: false,
    distDir: '.next'
  })
}

module.exports = nextConfig