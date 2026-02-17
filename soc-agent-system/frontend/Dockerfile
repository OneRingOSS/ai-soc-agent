# =============================================================================
# SOC Agent System — Frontend Dockerfile
# =============================================================================
# Multi-stage build for React + Vite application
# Stage 1: Build the React app
# Stage 2: Serve with nginx
# =============================================================================

# Stage 1: Build
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files and install dependencies (including devDependencies for build)
COPY package*.json ./
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration template and entrypoint script
COPY nginx.conf.template /etc/nginx/conf.d/nginx.conf.template
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Use custom entrypoint to substitute environment variables
ENTRYPOINT ["/docker-entrypoint.sh"]

