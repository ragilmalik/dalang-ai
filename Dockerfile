# One container: FastAPI backend (port 8000, internal) + Next.js website (port 3000, public).
FROM node:22-bookworm-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ api/
COPY scripts/ scripts/
COPY assets/ assets/
COPY content/ content/
COPY --from=web /app/web /app/web
ENV DATA_DIR=/data PORT=3000
VOLUME /data
EXPOSE 3000
CMD ["sh", "-c", "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 & cd web && npx next start -p ${PORT}"]
