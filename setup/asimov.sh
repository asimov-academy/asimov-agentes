#!/usr/bin/env bash
# Comando `asimov` na VPS (link em /usr/local/bin/asimov criado pelo setup).
set -Eeuo pipefail

RAIZ_PROJETO="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
# shellcheck source=setup/lib/base.sh
source "$RAIZ_PROJETO/setup/lib/base.sh"

ajuda() {
  printf '\n  %sasimov%s %sv%s%s\n\n' "$NEGRITO" "$NORMAL" "$CINZA" "$VERSAO" "$NORMAL"
  printf '    %sasimov%s        abre o menu\n' "$CIANO" "$NORMAL"
  printf '    %snovo-agente%s   cria um agente no Chatwoot\n' "$CIANO" "$NORMAL"
  printf '    %sagentes%s       lista os agentes, empresas e webhooks\n' "$CIANO" "$NORMAL"
  printf '    %seditar%s        muda nome, buffer, mensagens, modelos ou handoff de um agente\n' "$CIANO" "$NORMAL"
  printf '    %sremover%s       remove um agente\n' "$CIANO" "$NORMAL"
  printf '    %sconsumo%s       turnos, tokens, custo e falhas em 7 e 30 dias\n' "$CIANO" "$NORMAL"
  printf '    %shandoff%s       troca quem recebe a conversa passada pelo agente\n' "$CIANO" "$NORMAL"
  printf '    %satualizar%s     baixa a versão nova e republica\n' "$CIANO" "$NORMAL"
  printf '    %steclas%s        mostra o que o terminal manda em cada tecla (diagnóstico)\n' "$CIANO" "$NORMAL"
  echo
}

exige_instalacao() {
  estado_tem instalacao_concluida && return 0
  erro_fatal "A instalação ainda não terminou" "Rode o setup: bash ~/asimov-agentes/setup/instalar.sh"
}

# Esc em qualquer pergunta encerra o comando sem mudar nada.
roda() {
  exige_instalacao
  com_voltar "$@"
  [ "$FALHOU" = 0 ] || exit 1
}

case "${1:-menu}" in
  menu)
    exige_instalacao
    menu_operador
    ;;
  novo-agente) roda novo_agente ;;
  agentes) roda lista_agentes ;;
  editar) roda fluxo_editar_agente ;;
  remover) roda fluxo_remover_agente ;;
  consumo) roda mostra_consumo ;;
  handoff) roda fluxo_handoff ;;
  teclas) diagnostico_teclas ;;
  atualizar)
    # O install.sh local tem fixa a versão já instalada: baixa o da main.
    mkdir -p "$DIR_ESTADO"
    curl -fsSL "$URL_INSTALL" -o "$DIR_ESTADO/install.sh" \
      || erro_fatal "Não consegui baixar o instalador" "Confira a internet da VPS e rode asimov atualizar de novo."
    ASIMOV_ATUALIZAR=1 exec bash "$DIR_ESTADO/install.sh"
    ;;
  *)
    ajuda
    ;;
esac
