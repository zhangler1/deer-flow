##### DEPENDENCIES

FROM node:20-bookworm AS deps
# 使用 apt-get 而不是 apk (bookworm 是 Debian 系统)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Install dependencies based on the preferred package manager

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml\* ./

RUN \
    if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    elif [ -f pnpm-lock.yaml ]; then \
        npm install -g pnpm && \
        pnpm config set registry https://registry.npmmirror.com/ && \
        pnpm i --frozen-lockfile; \
    else echo "Lockfile not found." && exit 1; \
    fi

##### BUILDER

FROM node:20-bookworm AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_BASE_PATH
ENV NEXT_PUBLIC_BASE_PATH=$NEXT_PUBLIC_BASE_PATH
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN \
    if [ -f yarn.lock ]; then SKIP_ENV_VALIDATION=1 yarn build; \
    elif [ -f package-lock.json ]; then SKIP_ENV_VALIDATION=1 npm run build; \
    elif [ -f pnpm-lock.yaml ]; then \
        npm install -g pnpm && \
        pnpm config set registry https://registry.npmmirror.com/ && \
        SKIP_ENV_VALIDATION=1 pnpm run build; \
    else echo "Lockfile not found." && exit 1; \
    fi

##### RUNNER

FROM gcr.io/distroless/nodejs20-debian12 AS runner
WORKDIR /app

ENV NODE_ENV=production

ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT=3000

# 健康探测说明：
# distroless 镜像不包含 shell / curl / wget，但包含 node。
# scripts/health-monitor.sh 对本容器采用 `docker exec ... node -e "..."` 探测，
# 绕开对 curl 的依赖。若需用 HEALTHCHECK 指令，可写：
#   HEALTHCHECK CMD ["node", "-e", "require('http').get('http://localhost:3000/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"]

CMD ["server.js"]


# docker build . -t deer-flow-front.prd:latest --build-arg NEXT_PUBLIC_API_URL=http://192.168.0.112:8000/api  
# 子路径部署示例：--build-arg NEXT_PUBLIC_BASE_PATH=/deep-research-deerflow