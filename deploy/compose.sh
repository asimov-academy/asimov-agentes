#!/usr/bin/env bash
# Carregado por setup/instalar.sh e deploy/publicar.sh. Define `dc`, o docker compose do projeto.

RAIZ_PROJETO="${RAIZ_PROJETO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

dc() {
  ${SUDO:-} docker compose --project-name asimov \
    --env-file "$RAIZ_PROJETO/.env" \
    -f "$RAIZ_PROJETO/deploy/docker-compose.yml" "$@"
}
