#!/usr/bin/env bash
# Setup Asimov Academy: prepara uma VPS Ubuntu 24.04 vazia e sobe a plataforma de agentes.
# Pode ser rodado de novo a qualquer momento: continua de onde parou.
set -Eeuo pipefail

VERSAO="0.1.3"
RAIZ_PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR_ESTADO="$HOME/.asimov"
ARQ_ESTADO="$DIR_ESTADO/estado"
ARQ_ENV="$RAIZ_PROJETO/.env"
LOG="$DIR_ESTADO/setup.log"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "Rode como root ou com um usuário que tenha sudo."
    exit 1
  fi
  SUDO="sudo"
fi

DIR_LIB="$RAIZ_PROJETO/setup/lib"
# shellcheck source=setup/lib/ui.sh
source "$DIR_LIB/ui.sh"
# shellcheck source=setup/lib/estado.sh
source "$DIR_LIB/estado.sh"
# shellcheck source=setup/lib/sistema.sh
source "$DIR_LIB/sistema.sh"
# shellcheck source=setup/lib/dados.sh
source "$DIR_LIB/dados.sh"
# shellcheck source=setup/lib/dns.sh
source "$DIR_LIB/dns.sh"
# shellcheck source=setup/lib/instalacao.sh
source "$DIR_LIB/instalacao.sh"
# shellcheck source=setup/lib/agente.sh
source "$DIR_LIB/agente.sh"
# shellcheck source=setup/lib/final.sh
source "$DIR_LIB/final.sh"
# shellcheck source=deploy/compose.sh
source "$RAIZ_PROJETO/deploy/compose.sh"

# Nenhuma queda silenciosa: qualquer erro não tratado mostra onde parou e o caminho do log.
erro_inesperado() {
  local codigo=$? linha=$1 arquivo=$2
  trap - ERR
  erro_fatal "Erro inesperado (código $codigo) em ${arquivo#"$RAIZ_PROJETO"/}, linha $linha" \
    "rode o mesmo comando de novo; se repetir, envie as últimas linhas do log"
}
trap 'erro_inesperado "$LINENO" "${BASH_SOURCE[0]:-instalar.sh}"' ERR

principal() {
  estado_iniciar
  printf '\n===== setup %s iniciado em %s =====\n' "$VERSAO" "$(date -Is)" >>"$LOG"

  if estado_tem instalacao_concluida; then
    banner_asimov
    mostra_resumo
    info "O menu para criar e gerenciar agentes chega numa próxima versão do setup."
    echo
    exit 0
  fi

  tela_boas_vindas
  tela_iniciando
  tela_dados
  tela_dns
  tela_instalacao
  tela_primeiro_agente
  tela_final
}

principal "$@"
