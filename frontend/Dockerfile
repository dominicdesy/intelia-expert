# ---------- Stage 1: deps ----------
FROM node:20-bullseye AS deps
WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Robustesse réseau npm avec timeout plus long
RUN npm config set fetch-retries 10 \
 && npm config set fetch-retry-maxtimeout 300000 \
 && npm config set prefer-offline false \
 && npm config set registry https://registry.npmjs.org/

# Installation déterministe avec devDependencies
COPY package.json package-lock.json ./
RUN npm ci --include=dev --verbose

# ---------- Stage 2: builder ----------
FROM node:20-bullseye AS builder
WORKDIR /app

# Variables d'environnement pour build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max_old_space_size=4096"
ENV NEXT_SWC_PATH=""

# Arguments pour build
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

# Ensure directories exist
RUN mkdir -p public/fonts .next/cache

# Clean SWC cache et téléchargements corrompus
RUN rm -rf /root/.cache/next-swc ~/.npm/_cacache/tmp

# Force la réinstallation des binaires SWC
RUN npm rebuild @next/swc-linux-x64-gnu || true
RUN npm rebuild @next/swc-linux-x64-musl || true

# Build Next avec fallback multi-étapes
RUN echo "🚀 Tentative de build avec SWC..." && \
    npm run build || \
    (echo "❌ SWC failed, trying without SWC..." && \
     DISABLE_SWC=true IGNORE_TS_ERRORS=true npm run build) || \
    (echo "❌ Build failed, trying with legacy Node options..." && \
     NODE_OPTIONS="--max_old_space_size=2048 --openssl-legacy-provider" DISABLE_SWC=true npm run build)

# ---------- Stage 3: runtime ----------
FROM node:20-bullseye-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8080
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 8080

# Copie le minimum pour runtime
COPY --from=builder /app/package.json ./
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Start avec port explicite
CMD ["npm", "run", "start", "--", "-p", "8080"]