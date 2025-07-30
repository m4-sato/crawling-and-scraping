##### 1️⃣ LOCK ステージ #####
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS lock
WORKDIR /app
COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv lock

##### 2️⃣ RUNTIME ステージ #####
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

COPY --from=lock /app/uv.lock uv.lock
COPY pyproject.toml .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT []
CMD ["python", "intra_crawler.py"]
