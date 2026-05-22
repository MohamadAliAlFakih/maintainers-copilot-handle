# Multi-stage: build the React bundle, then serve it with nginx + cache headers.
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set fetch-timeout 600000 \
  && npm config set fetch-retries 5 \
  && npm config set fetch-retry-mintimeout 20000 \
  && npm config set fetch-retry-maxtimeout 120000 \
  && npm config set registry https://registry.npmjs.org/
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY tsconfig.json vite.config.ts tailwind.config.js postcss.config.js ./
COPY index.html ./
COPY src ./src
RUN npm run build

# ---- runtime ----
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx conf: long cache for hashed assets, no-cache for the HTML shell.
RUN cat > /etc/nginx/conf.d/default.conf <<'NGINX'
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;

  location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    try_files $uri =404;
  }

  location / {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    try_files $uri $uri/ /index.html;
  }
}
NGINX

EXPOSE 80
