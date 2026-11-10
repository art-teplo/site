# Next standalone для сервера: CI публикует образ в GHCR, на сервере это сервис web
# в root/docker-compose.yaml. Адрес бэка — имя сервиса в сети compose.

ARG NODE_VERSION=22.22-alpine

FROM node:${NODE_VERSION} AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:${NODE_VERSION} AS build
WORKDIR /app
# При сборке бэк не нужен (страницы собираются на демо, см. src/data/api.ts), но адрес нужен:
# по нему next.config.ts строит rewrites /api/ и /media/ и выключает имитацию формы
ARG API_URL=http://backend:8000
ENV NEXT_TELEMETRY_DISABLED=1 \
    API_URL=${API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:${NODE_VERSION} AS runtime
WORKDIR /app
ARG API_URL=http://backend:8000

LABEL org.opencontainers.image.title="art-teplo web" \
      org.opencontainers.image.source="https://github.com/art-teplo/site"

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    API_URL=${API_URL}

COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000

CMD ["node", "server.js"]
