#!/usr/bin/env bash
# shellcheck disable=SC2034  # variáveis usadas pelas telas e pelo comando asimov
# Caminhos, versão, sudo e bibliotecas. Carregado por setup/instalar.sh e setup/asimov.sh.

VERSAO="0.3.1"
# O instalador da main aponta sempre para a última versão marcada.
URL_INSTALL="https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh"

# Contagem de caracteres (alinhamento com acentos) depende de locale UTF-8.
if locale -a 2>/dev/null | grep -qi '^c\.utf-\?8$'; then
  export LC_ALL=C.UTF-8
fi
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
    "Rode o mesmo comando de novo; se repetir, envie as últimas linhas do log."
}
trap 'erro_inesperado "$LINENO" "${BASH_SOURCE[0]:-setup}"' ERR
