FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
# Render doesn't forward runtime env vars as Docker build args,
# so use the production Render URLs as defaults so they're baked into the bundle.
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

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Render injects PORT=10000 by default for Docker web services.
EXPOSE 10000
ENV PORT=10000

CMD ["node", "server.js"]
