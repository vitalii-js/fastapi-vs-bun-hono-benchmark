FROM oven/bun:1.4-slim
WORKDIR /app
COPY hono_app/package.json hono_app/bun.lock ./
RUN bun install --production --frozen-lockfile
COPY hono_app/src ./src
COPY data ./data
ENV WORKERS=1 NODE_ENV=production
EXPOSE 3000
CMD ["bun", "src/cluster.ts"]
