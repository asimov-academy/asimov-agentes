#!/usr/bin/env bash
# Setup Asimov Academy: prepara uma VPS Ubuntu 24.04 vazia e sobe a plataforma de agentes.
# Pode ser rodado de novo a qualquer momento: continua de onde parou ou atualiza a instalação.
set -Eeuo pipefail

RAIZ_PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=setup/lib/base.sh
source "$RAIZ_PROJETO/setup/lib/base.sh"

# Instalação já concluída: completa o que versões novas pedem (modo, modelos), reconstrói se o
# código mudou e mostra o resumo.
atualiza() {
  banner_asimov
  tela_modo
  tela_modelos
  tela_instalacao
  ajusta_permissoes
  instala_comando
  tela_handoff_pendente
  mostra_resumo
}

principal() {
  estado_iniciar
  estado_nova_versao
  printf '\n===== setup %s iniciado em %s =====\n' "$VERSAO" "$(date -Is)" >>"$LOG"

  if estado_tem instalacao_concluida; then
    atualiza
    exit 0
  fi

  tela_boas_vindas
  tela_modo
  tela_iniciando
  tela_dados
  tela_modelos
  tela_dns
  tela_instalacao
  ajusta_permissoes
  tela_primeiro_agente
  estado_set handoff_perguntado "$(date -Is)"
  tela_final
}

principal "$@"
