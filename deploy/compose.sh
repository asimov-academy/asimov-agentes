#!/usr/bin/env bash
# Carregado por setup/instalar.sh e deploy/publicar.sh. Define `dc`, o docker compose do projeto.

RAIZ_PROJETO="${RAIZ_PROJETO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# A WAHA só entra no Compose depois que o operador cria o primeiro agente dela (perfil `waha`).
# Sem isso, `dc up` derrubaria o contêiner que setup/lib/waha.sh subiu.
dc() {
  local perfis=()
  if grep -q '^WAHA_ATIVA=1$' "$RAIZ_PROJETO/.env" 2>/dev/null; then
    perfis=(--profile waha)
  fi
  ${SUDO:-} docker compose --project-name asimov \
    --env-file "$RAIZ_PROJETO/.env" \
    -f "$RAIZ_PROJETO/deploy/docker-compose.yml" "${perfis[@]}" "$@"
}
