# ── Build Stage ───────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_API_URL=http://localhost:8001
ENV VITE_API_URL=${VITE_API_URL}

# Install dependencies
COPY package.json .
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# ── Production Stage ──────────────────────────────────────
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config for SPA routing
RUN echo 'server { \
    listen 5173; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://backend:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
