FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM frontend AS frontend-checks
RUN npm test
RUN npm run lint
RUN npm run typecheck

FROM mcr.microsoft.com/playwright:v1.61.0-noble AS browser-smoke
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
CMD ["npm", "run", "test:browser"]

FROM python:3.14-slim AS application

COPY --from=ghcr.io/astral-sh/uv:0.10.3 /uv /uvx /bin/
WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends --yes git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
RUN uv tool install --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp

COPY src ./src
COPY --from=frontend /frontend/dist ./src/strava_dashboard/api/static/app
COPY scripts ./scripts
RUN uv sync --frozen --no-dev
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"
ENV HOME="/root"
ENV GARMIN_TOKEN_DIR="/root/.garminconnect"
