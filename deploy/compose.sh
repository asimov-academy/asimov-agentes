#!/usr/bin/env bash
# Carregado por setup/instalar.sh e deploy/publicar.sh. Define `dc`, o docker compose do projeto.

RAIZ_PROJETO="${RAIZ_PROJETO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# O copiloto entra no Compose só depois de vincular a conta de IA (perfil). Sem o perfil, `dc up`
# derrubaria o que setup/lib/vinculo.sh subiu. A WAHA não tem perfil: ela é instalada com o resto
# da plataforma, senão ligar o WhatsApp pelo painel esbarra num contêiner que ninguém subiu.
dc() {
  local perfis=()
  if grep -q '^COPILOTO_ATIVO=1$' "$RAIZ_PROJETO/.env" 2>/dev/null; then
    perfis+=(--profile copiloto)
  fi
  ${SUDO:-} docker compose --project-name asimov \
    --env-file "$RAIZ_PROJETO/.env" \
    -f "$RAIZ_PROJETO/deploy/docker-compose.yml" "${perfis[@]}" "$@"
}
