FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY frontend ./frontend

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "anki-api"]
