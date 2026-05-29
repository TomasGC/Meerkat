---
paths:
  - "**/Dockerfile"
  - "**/Dockerfile.*"
  - "**/.dockerignore"
---

# Docker Standards

Dockerfile best practices for secure, efficient container images.

---

## Multi-Stage Builds

```dockerfile
# ✅ Good - Multi-stage for small final image
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["MyApp.csproj", "./"]
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "MyApp.dll"]

# ❌ Bad - Single stage (large image)
FROM mcr.microsoft.com/dotnet/sdk:8.0
WORKDIR /app
COPY . .
RUN dotnet publish -c Release -o /out
ENTRYPOINT ["dotnet", "/out/MyApp.dll"]
```

---

## Base Image Selection

```dockerfile
# ✅ Good - Alpine for minimal size
FROM node:20-alpine
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine
FROM python:3.11-alpine

# ⚠️ Acceptable - Debian slim
FROM node:20-slim
FROM mcr.microsoft.com/dotnet/aspnet:8.0

# ❌ Bad - Full OS (large, more vulnerabilities)
FROM ubuntu:22.04
FROM node:20
```

---

## Security

### Run as Non-Root

```dockerfile
# ✅ Good - Create and use non-root user
FROM node:20-alpine

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

USER nodejs
WORKDIR /app
COPY --chown=nodejs:nodejs . .

CMD ["node", "server.js"]

# ❌ Bad - Running as root
FROM node:20-alpine
WORKDIR /app
COPY . .
CMD ["node", "server.js"]
```

### No Secrets in Image

```dockerfile
# ❌ Bad - Secrets in environment
ENV DATABASE_PASSWORD=MyP@ssw0rd
ENV API_KEY=sk_live_1234567890

# ✅ Good - Secrets via runtime
# Pass at runtime: docker run -e DATABASE_PASSWORD=$DB_PASS myapp
# Or use Docker secrets/Kubernetes secrets
```

### Scan for Vulnerabilities

```bash
# Run ORCA/Trivy scans
docker scan myapp:latest
trivy image myapp:latest
```

---

## Layer Optimization

### Order Layers by Change Frequency

```dockerfile
# ✅ Good - Dependencies first (cached), code last (changes often)
FROM node:20-alpine

WORKDIR /app

# Dependencies (rarely change)
COPY package*.json ./
RUN npm ci --only=production

# Application code (changes frequently)
COPY . .

EXPOSE 3000
CMD ["node", "server.js"]

# ❌ Bad - Code before dependencies (breaks cache)
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install
CMD ["node", "server.js"]
```

### Minimize Layers

```dockerfile
# ✅ Good - Combine related commands
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ❌ Bad - Separate RUN commands
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y ca-certificates
RUN rm -rf /var/lib/apt/lists/*
```

---

## .dockerignore

```dockerignore
# ✅ Always include
node_modules
npm-debug.log
.git
.gitignore
.env
.env.local
*.md
Dockerfile
.dockerignore

# Build artifacts
bin/
obj/
dist/
build/
*.log

# IDE
.vscode/
.idea/
*.swp
```

---

## Health Checks

```dockerfile
# ✅ Good - Health check for orchestration
FROM node:20-alpine
WORKDIR /app
COPY . .

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node healthcheck.js || exit 1

CMD ["node", "server.js"]
```

---

## ARG vs ENV

```dockerfile
# ✅ Good - ARG for build-time, ENV for runtime
ARG NODE_VERSION=20
ARG BUILD_DATE

FROM node:${NODE_VERSION}-alpine

ENV NODE_ENV=production \
    PORT=3000

LABEL build-date="${BUILD_DATE}"

WORKDIR /app
COPY . .
EXPOSE ${PORT}
CMD ["node", "server.js"]
```

---

**Build images securely and efficiently.**
