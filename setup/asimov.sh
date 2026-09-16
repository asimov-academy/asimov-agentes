#!/usr/bin/env bash
# Comando `asimov` na VPS (link em /usr/local/bin/asimov criado pelo setup).
set -Eeuo pipefail

RAIZ_PROJETO="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
# shellcheck source=setup/lib/base.sh
source "$RAIZ_PROJETO/setup/lib/base.sh"

ajuda() {
  printf '\n  %sasimov%s %sv%s%s\n\n' "$NEGRITO" "$NORMAL" "$CINZA" "$VERSAO" "$NORMAL"
  printf '    %snovo-agente%s   cria um agente no Chatwoot\n' "$CIANO" "$NORMAL"
  printf '    %sagentes%s       lista os agentes e as empresas\n' "$CIANO" "$NORMAL"
  printf '    %satualizar%s     baixa a versão nova e republica\n' "$CIANO" "$NORMAL"
  echo
}

exige_instalacao() {
  estado_tem instalacao_concluida && return 0
  erro_fatal "A instalação ainda não terminou" "Rode o setup: bash ~/asimov-agentes/setup/instalar.sh"
}

case "${1:-ajuda}" in
  novo-agente)
    exige_instalacao
    secao "Novo agente"
    fluxo_novo_agente
    echo
    dica "Mande uma mensagem na caixa de entrada para testar."
    echo
    ;;
  agentes)
    exige_instalacao
    lista_agentes
    ;;
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
