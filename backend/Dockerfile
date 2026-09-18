# O contexto do build é a raiz do repositório, não `backend/`: o painel web mora em `frontend/` e
# precisa entrar na mesma imagem. O `.dockerignore` da raiz é quem segura o que não vai junto,
# `.env` à frente de tudo.

# Painel web. Construído aqui para a VPS não precisar de node instalado: ela já constrói a imagem.
FROM node:22-alpine AS front
WORKDIR /front
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

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
COPY backend/pyproject.toml backend/uv.lock ./
RUN extras=""; for p in $PROVEDORES; do extras="$extras --extra $p"; done; \
    uv sync --frozen --no-dev --no-install-project $extras
COPY backend/ .
COPY --from=front /front/dist ./app/painel/estaticos/app
# O volume de mídia nasce com o dono desta pasta; sem isso a API (uid 1000) não grava.
RUN useradd --system --uid 1000 app && mkdir -p /app/prompts /var/lib/asimov/midia \
    && chown -R app /app /var/lib/asimov
USER app
# Sem access log: ele registra a URL inteira, e o token do webhook mora nela (auditoria de
# 2026-09-18, A14). Todo webhook já registra o próprio desfecho em `webhook_aceito`/`webhook_ignorado`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]

# Contêiner do copiloto do painel: a mesma imagem da API mais o CLI de código que o operador
# escolheu. Só ele leva o CLI, e só ele recebe a pasta de credencial montada (quem monta é o
# Compose). A API segue enxuta e sem nada disso por perto.
FROM producao AS copiloto
USER root
ARG AGENTE_CODIGO=claude_code
ARG PROVEDORES="openai"
ENV HOME=/home/app \
    PATH=/home/app/.local/bin:/opt/venv/bin:$PATH
# O SDK do MCP entra só aqui: é este contêiner que serve as ferramentas ao CLI. Os provedores vêm
# junto de novo porque `uv sync` deixa o ambiente exatamente com o que a linha pediu.
RUN extras="--extra copiloto"; for p in $PROVEDORES; do extras="$extras --extra $p"; done; \
    uv sync --frozen --no-dev --no-install-project $extras && chown -R app /opt/venv
# A home existe por causa do CLI: é nela que ele guarda o login e é ela que o Compose monta.
RUN mkdir -p /home/app && chown -R app /home/app \
    && apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && if [ "$AGENTE_CODIGO" = codex ]; then \
         curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
         && apt-get install -y --no-install-recommends nodejs \
         && npm install -g @openai/codex; \
       fi \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER app
# O instalador oficial do Claude Code dispensa o Node e deixa o binário em ~/.local/bin, que já
# está no PATH acima. Instalado como `app`, e não como root, para o CLI mandar na própria pasta.
RUN if [ "$AGENTE_CODIGO" != codex ]; then curl -fsSL https://claude.ai/install.sh | bash; fi
CMD ["arq", "app.copiloto.worker.Configuracao"]

# Os testes não precisam do front: o `conftest.py` monta uma cópia mínima com a mesma forma.
FROM base AS teste
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --all-extras --no-install-project
COPY backend/ .
CMD ["pytest", "-q"]
