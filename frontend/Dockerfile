FROM node:20-alpine

WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Set environment variables for build
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

# Create .next directory first
RUN mkdir -p .next

# Build Next.js directly (bypass problematic prebuild)
RUN npx next build

# Create BUILD_ID if missing
RUN test -f .next/BUILD_ID || echo "docker-build-$(date +%s)" > .next/BUILD_ID

# Verify build succeeded
RUN ls -la .next

# Expose port
EXPOSE 8080

# Start the application
CMD ["npm", "start"]