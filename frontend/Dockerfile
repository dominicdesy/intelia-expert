FROM node:20-alpine

WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Install system dependencies for compilation
RUN apk add --no-cache libc6-compat

# Copy package files first
COPY package*.json ./

# Install dependencies and pre-download SWC
RUN npm install
RUN npm install @next/swc-linux-x64-musl || true

# Set environment variables before copying source
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_APP_NAME="Intelia Expert"
ENV NEXT_PUBLIC_ENVIRONMENT="production"
ENV NEXT_PUBLIC_API_URL="https://expert.intelia.com/api"
ENV NEXT_PUBLIC_API_BASE_URL="https://expert.intelia.com/api"
ENV NEXT_PUBLIC_API_VERSION="v1"
ENV NEXT_PUBLIC_SITE_URL="https://expert.intelia.com"

# Copy source code
COPY . .

# Clear any existing build artifacts
RUN rm -rf .next

# Build with retry mechanism
RUN npm run build || (sleep 5 && npm run build) || (sleep 10 && npm run build)

# Verify build exists
RUN ls -la .next/

# Expose port
EXPOSE 8080

# Start application
CMD ["npm", "start"]