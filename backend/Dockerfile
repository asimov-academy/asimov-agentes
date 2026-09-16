FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYDANTIC_AI_NO_BANNER=1
WORKDIR /app
# Provedores escolhidos no setup, separados por espaço: "openai gemini".
ARG PROVEDORES="openai"

FROM base AS producao
COPY pyproject.toml uv.lock ./
RUN extras=""; for p in $PROVEDORES; do extras="$extras --extra $p"; done; \
    uv sync --frozen --no-dev --no-install-project $extras
COPY . .
# O volume de mídia nasce com o dono desta pasta; sem isso a API (uid 1000) não grava.
RUN useradd --system --uid 1000 app && mkdir -p /app/prompts /var/lib/asimov/midia \
    && chown -R app /app /var/lib/asimov
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

FROM base AS teste
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-extras --no-install-project
COPY . .
CMD ["pytest", "-q"]
