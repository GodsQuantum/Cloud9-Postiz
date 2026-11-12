# syntax=docker/dockerfile:1.7
# Only official upstream application code enters this image.
FROM node:22-bookworm-slim AS build
WORKDIR /build/server
COPY postiz-agent/server/package.json postiz-agent/server/pnpm-lock.yaml ./
RUN npm install -g pnpm@8 && pnpm install --no-frozen-lockfile && pnpm add node-fetch@2.7.0 && pnpm add -D @types/node-fetch@2
COPY postiz-agent/server/index.ts postiz-agent/server/tsconfig.json ./
RUN pnpm run build && test -s dist/index.js && pnpm prune --prod

FROM node:22-bookworm-slim
WORKDIR /app/server
ENV NODE_ENV=production PORT=3111
COPY --from=build /build/server/dist ./dist
COPY --from=build /build/server/node_modules ./node_modules
COPY --from=build /build/server/package.json ./package.json
USER node
EXPOSE 3111
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD node -e 'require("http").get("http://127.0.0.1:3111/health",r=>process.exit(r.statusCode===200?0:1)).on("error",()=>process.exit(1))'
CMD ["node","dist/index.js"]
