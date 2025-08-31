FROM node:20-slim

WORKDIR /app

# Build arguments
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Set environment variables
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

# Disable SWC minification to avoid download issues
ENV NEXT_SWCMINIFY=false

# Copy source code
COPY . .

# Clean any existing build
RUN rm -rf .next

# Build with Babel fallback instead of SWC
RUN npm run build

# Verify build
RUN ls -la .next/

# Expose port
EXPOSE 8080

# Start application
CMD ["npm", "start"]