FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
# Bake production URLs at build time (Render Docker doesn't pass runtime vars as build args).
ARG NEXT_PUBLIC_API_URL=https://fiissa-api.onrender.com
ARG NEXT_PUBLIC_APP_URL=https://fiissa-frontend.onrender.com
ARG NEXT_PUBLIC_APP_NAME=Fiissa
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=10000
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/next.config.js ./next.config.js
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules
USER nextjs
EXPOSE 10000
CMD ["node_modules/.bin/next", "start", "-p", "10000"]
