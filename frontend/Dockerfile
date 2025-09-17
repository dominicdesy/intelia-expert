# ---------- Stage 1: deps ----------
FROM node:20-bullseye-slim AS deps
WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Configuration npm plus conservative
RUN npm config set fetch-retries 3 \
 && npm config set fetch-retry-maxtimeout 60000

# Installation des dépendances
COPY package.json package-lock.json* ./
RUN npm ci --include=dev --silent

# ---------- Stage 2: builder ----------
FROM node:20-bullseye-slim AS builder
WORKDIR /app

# Variables d'environnement pour build
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max_old_space_size=1024"

# Arguments de build (essentiels uniquement)
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY

# Copier les dépendances installées
COPY --from=deps /app/node_modules ./node_modules

# Copier le code source
COPY . .

# Build Next.js avec gestion d'erreur
RUN npm run build 2>&1 | tee build.log || (echo "Build failed:" && cat build.log && exit 1)

# ---------- Stage 3: runtime ----------
FROM node:20-bullseye-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8080
ENV NEXT_TELEMETRY_DISABLED=1

# Copier seulement ce qui est nécessaire
COPY --from=builder /app/package.json ./
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 8080

CMD ["npm", "run", "start", "--", "-p", "8080"]