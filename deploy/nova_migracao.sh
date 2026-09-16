#!/usr/bin/env bash
# Gera uma migração a partir das mudanças nos modelos: ./deploy/nova_migracao.sh "adiciona campo x"
set -euo pipefail

[ -n "${1:-}" ] || { echo "Uso: ./deploy/nova_migracao.sh \"descrição curta\""; exit 1; }
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"
# shellcheck source=deploy/compose.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/compose.sh"

dc up -d --wait postgres redis
dc run --rm --user 0 -v "$RAIZ_PROJETO/backend:/app" api alembic upgrade head
dc run --rm --user 0 -v "$RAIZ_PROJETO/backend:/app" api alembic revision --autogenerate -m "$1"
${SUDO} chown -R "$(id -u):$(id -g)" "$RAIZ_PROJETO/backend/migrations/versions"
echo "Migração criada em backend/migrations/versions. Revise o arquivo antes de publicar."
