# Multi-stage: `dev` preserves the exact pre-Phase-18 behavior (used by
# docker-compose.yml's `web` service via `target: dev`, hot-reloading
# against the bind-mounted source) — untouched by this phase. The default
# (final) stage is a real production build, used only for the Phase 18
# Docker smoke test (`docker build .` with no --target, or
# `--target runner`), never by local dev.

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM deps AS dev
WORKDIR /app
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM deps AS builder
WORKDIR /app
COPY . .
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./
EXPOSE 3000
CMD ["npm", "run", "start"]
