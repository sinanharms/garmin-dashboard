FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.3 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
RUN uv tool install --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp
RUN uv tool install --python 3.14 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth

COPY src ./src
RUN uv sync --frozen --no-dev
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"
ENV HOME="/root"
ENV GARMIN_TOKEN_DIR="/root/.garminconnect"
