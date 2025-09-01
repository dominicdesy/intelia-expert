# ---------- Stage 1: deps ----------
FROM node:20-bullseye-slim AS deps
WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# 🌐 Réseau npm plus robuste
RUN npm config set fetch-retries 5 \
 && npm config set fetch-retry-maxtimeout 120000 \
 && npm config set prefer-offline false

# Installation des dépendances
COPY package.json package-lock.json ./
RUN npm ci --include=dev

# ---------- Stage 2: builder ----------
FROM node:20-bullseye-slim AS builder
WORKDIR /app

# 🔍 Vérif glibc (debug) - doit afficher glibc, pas musl
RUN ldd --version 2>/dev/null | head -n1 || true

# Variables d'environnement pour build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max_old_space_size=2048"

# Cache buster pour forcer rebuild propre (optionnel)
ARG CACHE_BUST
ENV CACHE_BUST=$CACHE_BUST

# Arguments de build
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_APP_NAME="Intelia Expert"
ENV NEXT_PUBLIC_ENVIRONMENT="production"
ENV NEXT_PUBLIC_API_URL="https://expert.intelia.com/api"
ENV NEXT_PUBLIC_API_BASE_URL="https://expert.intelia.com/api"
ENV NEXT_PUBLIC_API_VERSION="v1"
ENV NEXT_PUBLIC_SITE_URL="https://expert.intelia.com"

# Copier les dépendances installées
COPY --from=deps /app/node_modules ./node_modules

# Copier le code source
COPY . .

# Ensure directories exist
RUN mkdir -p public/fonts

# 🧹 Purge complète des caches/binaire musl - CRUCIAL !
RUN rm -rf /root/.cache/next-swc node_modules/next/next-swc-fallback

# 🚀 Build Next.js (SWC pour compilation, Terser pour minification)
RUN npm run build

# ---------- Stage 3: runtime ----------
FROM node:20-bullseye-slim AS runner
WORKDIR /app

# Configuration runtime
ENV NODE_ENV=production
ENV PORT=8080
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 8080

# Copier seulement ce qui est nécessaire
COPY --from=builder /app/package.json ./
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Démarrage
CMD ["npm", "run", "start", "--", "-p", "8080"]