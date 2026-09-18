#!/usr/bin/env bash
# Setup Asimov Academy: prepara uma VPS Ubuntu 24.04 vazia e sobe a plataforma de agentes.
# Pode ser rodado de novo a qualquer momento: continua de onde parou ou atualiza a instalação.
set -Eeuo pipefail

RAIZ_PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=setup/lib/base.sh
source "$RAIZ_PROJETO/setup/lib/base.sh"

# Instalação já concluída: completa o que versões novas pedem (modo), reconstrói se o
# código mudou, mostra o resumo e abre o menu. `asimov atualizar` para no resumo.
atualiza() {
  banner_asimov
  tela_modo
  tela_instalacao
  ajusta_permissoes
  instala_comando
  # Instalação que ligou o WhatsApp antes de o timer semanal e dos eventos de hoje.
  if [ "$(env_get WAHA_ATIVA)" = 1 ]; then
    instala_timer_waha || true
    reconfigura_sessoes_waha
  fi
  tela_handoff_pendente
  tela_vinculo_ia
  tela_painel_oferta
  mostra_resumo
  [ -n "${ASIMOV_ATUALIZAR:-}" ] || menu_operador
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
  tela_dns
  tela_instalacao
  ajusta_permissoes
  # O essencial está no ar. A conta de IA vem antes do painel: vinculada, o painel já nasce com o
  # copiloto. O painel vem antes do primeiro agente: quem liga o painel cria o agente por lá, no
  # passo a passo com prévia; quem fica no terminal cria aqui.
  tela_vinculo_ia
  tela_painel_oferta
  tela_primeiro_agente
  estado_set handoff_perguntado "$(date -Is)"
  tela_final
}

principal "$@"
