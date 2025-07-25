# 🔧 CONFIGURATION DU FRONTEND EXISTANT - INTELIA EXPERT

# ============================================================================
# 1. MISE À JOUR DU package.json
# ============================================================================

# Remplacez complètement le contenu de frontend/package.json par :
cat > package.json << 'EOF'
{
  "name": "intelia-expert-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start -p $PORT",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@supabase/auth-helpers-nextjs": "^0.8.7",
    "@supabase/supabase-js": "^2.38.0",
    "@headlessui/react": "^1.7.17",
    "@heroicons/react": "^2.0.18",
    "zustand": "^4.4.7",
    "react-hot-toast": "^2.4.1",
    "framer-motion": "^10.16.5",
    "@aws-sdk/client-s3": "^3.450.0",
    "@aws-sdk/s3-request-presigner": "^3.450.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "typescript": "^5",
    "tailwindcss": "^3.3.5",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.31",
    "@tailwindcss/forms": "^0.5.6",
    "@tailwindcss/typography": "^0.5.10",
    "eslint": "^8.51.0",
    "eslint-config-next": "14.0.0"
  },
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  }
}
EOF

# ============================================================================
# 2. MISE À JOUR DU next.config.js
# ============================================================================

cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuration pour DigitalOcean App Platform
  output: 'standalone',
  
  // Variables d'environnement publiques
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // Configuration d'images pour DigitalOcean Spaces
  images: {
    domains: [
      'intelia-expert-assets.nyc3.digitaloceanspaces.com',
      'intelia-expert-assets.nyc3.cdn.digitaloceanspaces.com'
    ],
    // Alternative pour les domaines externes
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.digitaloceanspaces.com',
        port: '',
        pathname: '/**',
      },
    ],
  },

  // Headers de sécurité
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ]
  },

  // Redirections
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
    ]
  },

  // Configuration TypeScript
  typescript: {
    ignoreBuildErrors: false,
  },

  // Configuration ESLint
  eslint: {
    ignoreDuringBuilds: false,
  },

  // Configuration expérimentale
  experimental: {
    serverComponentsExternalPackages: ['@supabase/supabase-js'],
  },
}

module.exports = nextConfig
EOF

# ============================================================================
# 3. CRÉER LES FICHIERS DE CONFIGURATION MANQUANTS
# ============================================================================

# Créer tailwind.config.js
cat > tailwind.config.js << 'EOF'
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Couleurs Intelia basées sur le logo et design Figma
        intelia: {
          blue: {
            50: '#eff6ff',
            100: '#dbeafe',
            500: '#3b82f6', // Bleu principal du logo
            600: '#2563eb',
            700: '#1d4ed8',
            900: '#1e3a8a'
          },
          green: {
            50: '#f0fdf4',
            100: '#dcfce7',
            500: '#22c55e', // Vert agricole
            600: '#16a34a',
            700: '#15803d',
            900: '#14532d'
          },
          gray: {
            50: '#f9fafb',
            100: '#f3f4f6',
            200: '#e5e7eb',
            300: '#d1d5db',
            400: '#9ca3af',
            500: '#6b7280',
            600: '#4b5563',
            700: '#374151',
            800: '#1f2937',
            900: '#111827'
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        display: ['Inter', 'ui-sans-serif', 'system-ui']
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'bounce-in': 'bounceIn 0.5s ease-out',
        'typing': 'typing 2s steps(40, end)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        bounceIn: {
          '0%': { transform: 'scale(0.3)', opacity: '0' },
          '50%': { transform: 'scale(1.05)' },
          '70%': { transform: 'scale(0.9)' },
          '100%': { transform: 'scale(1)', opacity: '1' }
        },
        typing: {
          'from': { width: '0' },
          'to': { width: '100%' }
        }
      },
      screens: {
        'xs': '475px',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}

export default config
EOF

# Créer postcss.config.js
cat > postcss.config.js << 'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

# Créer tsconfig.json (mise à jour)
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
EOF

# ============================================================================
# 4. CRÉER LA STRUCTURE DE DOSSIERS
# ============================================================================

# Créer tous les dossiers nécessaires
mkdir -p app/{auth/callback,chat,profile,admin}
mkdir -p components/{providers,ui,layout,auth,chat}
mkdir -p lib/{supabase,api,stores,digitalocean,hooks,utils}
mkdir -p types
mkdir -p public/images

# ============================================================================
# 5. CRÉER LES FICHIERS DE BASE
# ============================================================================

# Créer .env.example
cat > .env.example << 'EOF'
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Backend API Configuration  
NEXT_PUBLIC_API_URL=https://your-backend.ondigitalocean.app

# OpenAI Configuration (pour le chat)
NEXT_PUBLIC_OPENAI_API_KEY=your_openai_key_here

# DigitalOcean Spaces (optionnel)
DO_SPACES_KEY=your_spaces_access_key
DO_SPACES_SECRET=your_spaces_secret_key
DO_SPACES_ENDPOINT=nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=intelia-expert-assets

# Application Configuration
NEXT_PUBLIC_APP_NAME="Intelia Expert"
NEXT_PUBLIC_APP_VERSION="1.0.0"
NEXT_PUBLIC_ENVIRONMENT="development"
EOF

# Créer .env.local (copie de .env.example pour commencer)
cp .env.example .env.local

# Créer .gitignore mis à jour
cat > .gitignore << 'EOF'
# Dependencies
/node_modules
/.pnp
.pnp.js

# Testing
/coverage

# Next.js
/.next/
/out/

# Production
/build

# Misc
.DS_Store
*.pem

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Local env files
.env*.local
.env

# Vercel
.vercel

# TypeScript
*.tsbuildinfo
next-env.d.ts

# DigitalOcean
.do/

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF

# ============================================================================
# 6. INSTALLER TOUTES LES DÉPENDANCES
# ============================================================================

# Installer les dépendances
npm install

echo "✅ Configuration terminée ! Structure prête pour le code."
echo ""
echo "📁 Structure créée :"
echo "   ├── app/ (pages Next.js)"
echo "   ├── components/ (composants React)"  
echo "   ├── lib/ (logique métier)"
echo "   ├── types/ (types TypeScript)"
echo "   ├── public/images/ 👈 AJOUTEZ VOS ASSETS ICI"
echo "   └── .env.local 👈 CONFIGUREZ VOS VARIABLES"
echo ""
echo "🎯 Prochaines étapes :"
echo "   1. Ajoutez logo-intelia.png dans public/images/"
echo "   2. Ajoutez chicken-welcome.png dans public/images/"
echo "   3. Configurez vos variables dans .env.local"
echo "   4. Je vous donnerai ensuite tout le code à copier !"
