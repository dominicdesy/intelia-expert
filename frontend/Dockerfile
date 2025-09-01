# ---------- Stage 1: deps ----------
FROM node:20-bullseye-slim AS deps
WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Robustesse réseau npm
RUN npm config set fetch-retries 5 \
 && npm config set fetch-retry-maxtimeout 120000 \
 && npm config set prefer-offline false

# Installation déterministe avec devDependencies (nécessaire pour TailwindCSS)
COPY package.json package-lock.json ./
RUN npm ci --include=dev

# ---------- Stage 2: builder ----------
FROM node:20-bullseye-slim AS builder
WORKDIR /app

# Variables d'environnement pour build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max_old_space_size=4096"

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

# Reprend node_modules installés
COPY --from=deps /app/node_modules ./node_modules

# Copy source avec .dockerignore
COPY . .

# Ensure fonts directory exists
RUN mkdir -p public/fonts

# 🎯 BUILD SIMPLE ET FIABLE: Utilise Terser au lieu de SWC
RUN echo "🚀 Building with Terser minifier (sans SWC)..." && \
    DISABLE_SWC=true npm run build

# ---------- Stage 3: runtime ----------
FROM node:20-bullseye-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8080
EXPOSE 8080

# Copie le minimum pour runtime
COPY --from=builder /app/package.json ./
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Start avec port explicite
CMD ["npm", "run", "start", "--", "-p", "8080"]