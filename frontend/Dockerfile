# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Configuration npm optimisée
RUN npm config set fetch-retries 3 \
    && npm config set fetch-retry-maxtimeout 60000

# Installation de TOUTES les dépendances (dev incluses pour le build)
COPY package.json package-lock.json* ./
RUN npm ci --silent

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Variables d'environnement pour build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max_old_space_size=1024"

# Arguments de build
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_API_URL

ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copier les dépendances du stage précédent
COPY --from=deps /app/node_modules ./node_modules

# Copier le code source
COPY . .

# Build Next.js
RUN npm run build

# Stage 3: Runtime (ultra-léger)
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8080
ENV NEXT_TELEMETRY_DISABLED=1

# Créer utilisateur non-root
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copier seulement les fichiers nécessaires
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

CMD ["node", "server.js"]