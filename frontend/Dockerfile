FROM node:20-slim

WORKDIR /app

# `npm ci` installs exactly what package-lock.json pins (reproducible);
# `npm install` can silently drift to newer versions.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 5173

# Development server with hot reload; /api and /ws are proxied to the
# backend service (see vite.config.ts and BACKEND_HOST in docker-compose.yml).
CMD ["npm", "run", "dev", "--", "--host"]
