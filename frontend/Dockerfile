# frontend/Dockerfile - Multi-stage optimisé pour cache maximum
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files (cached layer si package.json/package-lock.json inchangés)
COPY package.json package-lock.json* ./

# Install dependencies with cache optimization
RUN \
  if [ -f package-lock.json ]; then \
    npm ci --prefer-offline --no-audit --progress=false; \
  else \
    npm install --prefer-offline --no-audit --progress=false; \
  fi

# Build stage
FROM base AS builder
WORKDIR /app

# Copy node_modules from deps stage (cached)
COPY --from=deps /app/node_modules ./node_modules

# Copy source code (this changes frequently)
COPY . .

# Disable telemetry
ENV NEXT_TELEMETRY_DISABLED 1

# Build application with standalone output
RUN npm run build

# Production stage - minimal
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create nextjs user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public

# Set correct permissions for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Copy standalone build (optimized by Next.js)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Use server.js from standalone build
CMD ["node", "server.js"]