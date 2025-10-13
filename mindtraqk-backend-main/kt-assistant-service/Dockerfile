# other-service/Dockerfile

# 1) Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json tsconfig.json ./
RUN npm ci
COPY src ./src
# COPY prisma ./prisma   # <- uncomment if you use prisma or other build assets
RUN npm run build

# 2) Runtime stage
FROM node:18-alpine
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8181

# Only prod deps in the final image
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

# App code (built JS)
COPY --from=builder /app/dist ./dist
# COPY --from=builder /app/prisma ./prisma  # <- if needed at runtime

# Drop privileges
USER node

EXPOSE 8181
CMD ["node", "dist/app.js"]