#!/usr/bin/env bash
# Carregado por setup/instalar.sh e deploy/publicar.sh. Define `dc`, o docker compose do projeto.

RAIZ_PROJETO="${RAIZ_PROJETO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Dois contêineres entram no Compose só quando o operador escolhe (perfis). A WAHA, depois do
# primeiro agente dela; o copiloto, depois de vincular a conta de IA. Sem os perfis, `dc up`
# derrubaria o que setup/lib/waha.sh e setup/lib/vinculo.sh subiram.
dc() {
  local perfis=()
  if grep -q '^WAHA_ATIVA=1$' "$RAIZ_PROJETO/.env" 2>/dev/null; then
    perfis=(--profile waha)
  fi
  if grep -q '^COPILOTO_ATIVO=1$' "$RAIZ_PROJETO/.env" 2>/dev/null; then
    perfis+=(--profile copiloto)
  fi
  ${SUDO:-} docker compose --project-name asimov \
    --env-file "$RAIZ_PROJETO/.env" \
    -f "$RAIZ_PROJETO/deploy/docker-compose.yml" "${perfis[@]}" "$@"
}
