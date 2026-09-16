#!/usr/bin/env bash
# shellcheck disable=SC2034  # cores usadas pelas outras telas
# Tela: cores, banners, seções, perguntas, passos numerados e erros.
#
# Padrão visual: seção em ciano, pergunta com ❯, dica em cinza, valor em negrito,
# ✓ verde para sucesso, ▲ amarelo para atenção, ✗ vermelho para erro.

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  CIANO=$'\033[36m'
  VERDE=$'\033[32m'
  AMARELO=$'\033[33m'
  VERMELHO=$'\033[31m'
  CINZA=$'\033[90m'
  NEGRITO=$'\033[1m'
  NORMAL=$'\033[0m'
else
  CIANO="" VERDE="" AMARELO="" VERMELHO="" CINZA="" NEGRITO="" NORMAL=""
fi

# Respostas vêm do terminal (descritor 3), mesmo quando o script chega por bash <(curl ...).
# Testes automatizados trocam o terminal por um arquivo com as respostas (ASIMOV_TTY).
# O grupo evita que o 2>/dev/null do exec fique valendo para o script inteiro.
{ exec 3<"${ASIMOV_TTY:-/dev/tty}"; } 2>/dev/null || exec 3<&0

ler() { IFS= read -r "$@" <&3 || true; }

banner_asimov() {
  clear 2>/dev/null || true
  printf '%s%s' "$CIANO" "$NEGRITO"
  cat <<'ARTE'

     █████╗ ███████╗██╗███╗   ███╗ ██████╗ ██╗   ██╗
    ██╔══██╗██╔════╝██║████╗ ████║██╔═══██╗██║   ██║
    ███████║███████╗██║██╔████╔██║██║   ██║██║   ██║
    ██╔══██║╚════██║██║██║╚██╔╝██║██║   ██║╚██╗ ██╔╝
    ██║  ██║███████║██║██║ ╚═╝ ██║╚██████╔╝ ╚████╔╝
    ╚═╝  ╚═╝╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝   ╚═══╝
ARTE
  printf '%s    %sACADEMY%s  %sagentes de atendimento · v%s%s\n\n' \
    "$NORMAL" "$NEGRITO" "$NORMAL" "$CINZA" "$VERSAO" "$NORMAL"
}

banner_iniciando() {
  clear 2>/dev/null || true
  printf '%s%s' "$CIANO" "$NEGRITO"
  cat <<'ARTE'

  ██╗███╗   ██╗██╗ ██████╗██╗ █████╗ ███╗   ██╗██████╗  ██████╗
  ██║████╗  ██║██║██╔════╝██║██╔══██╗████╗  ██║██╔══██╗██╔═══██╗
  ██║██╔██╗ ██║██║██║     ██║███████║██╔██╗ ██║██║  ██║██║   ██║
  ██║██║╚██╗██║██║██║     ██║██╔══██║██║╚██╗██║██║  ██║██║   ██║
  ██║██║ ╚████║██║╚██████╗██║██║  ██║██║ ╚████║██████╔╝╚██████╔╝
  ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝
ARTE
  printf '%s  %sv%s%s\n\n' "$NORMAL" "$CINZA" "$VERSAO" "$NORMAL"
}

# secao "Título": cabeçalho de uma linha.
secao() {
  local traco
  traco=$(printf '%*s' $((56 - ${#1})) '' | tr ' ' '-')
  printf '\n%s%s▍ %s %s%s%s\n\n' "$CIANO" "$NEGRITO" "$1" "$NORMAL$CINZA" "$traco" "$NORMAL"
}
titulo() { secao "$@"; }

info() { printf '  %s\n' "$*"; }
dica() { printf '  %s%s%s\n' "$CINZA" "$*" "$NORMAL"; }
ok() { printf '  %s✓%s %s\n' "$VERDE" "$NORMAL" "$*"; }
aviso() { printf '  %s▲%s %s\n' "$AMARELO" "$NORMAL" "$*"; }
falha() { printf '  %s✗%s %s\n' "$VERMELHO" "$NORMAL" "$*"; }
destaque() { printf '%s%s%s' "$NEGRITO" "$*" "$NORMAL"; }

# campo "Rótulo" "valor": linha de resumo alinhada.
campo() {
  local espacos
  espacos=$(printf '%*s' $((11 - ${#1})) '')
  printf '  %s%s%s%s %s%s%s\n' "$CINZA" "$1" "$espacos" "$NORMAL" "$NEGRITO" "$2" "$NORMAL"
}

_prompt() { printf '%s❯%s %s%s%s' "$CIANO" "$NORMAL" "$NEGRITO" "$1" "$NORMAL"; }

# Variáveis internas com prefixo __ para não colidir com a variável de quem chama.

# pergunta VAR "texto" [padrão]: Enter aceita o padrão.
pergunta() {
  local __var=$1 __texto=$2 __padrao=${3:-} __resposta
  while true; do
    _prompt "$__texto"
    [ -n "$__padrao" ] && printf ' %s(%s)%s' "$CINZA" "$__padrao" "$NORMAL"
    printf ': '
    __resposta=""
    ler __resposta
    __resposta=${__resposta:-$__padrao}
    if [ -n "$__resposta" ]; then
      printf -v "$__var" '%s' "$__resposta"
      return 0
    fi
    falha "Resposta obrigatória."
  done
}

# pergunta_secreta VAR "texto": não mostra o que é digitado.
pergunta_secreta() {
  local __var=$1 __texto=$2 __resposta
  while true; do
    _prompt "$__texto"
    printf ': '
    __resposta=""
    ler -s __resposta
    if [ -n "$__resposta" ]; then
      printf '%s••••••••%s\n' "$CINZA" "$NORMAL"
      printf -v "$__var" '%s' "$__resposta"
      return 0
    fi
    echo
    falha "Resposta obrigatória."
  done
}

# escolha VAR "texto" opção1 opção2 ...: devolve o número escolhido.
escolha() {
  local __var=$1 __texto=$2 __resposta __i __item
  shift 2
  _prompt "$__texto"
  echo
  __i=1
  for __item in "$@"; do
    printf '    %s%s%s  %s\n' "$CIANO" "$__i" "$NORMAL" "$__item"
    __i=$((__i + 1))
  done
  while true; do
    printf '  %sNúmero:%s ' "$CINZA" "$NORMAL"
    __resposta=""
    ler __resposta
    if [[ "$__resposta" =~ ^[0-9]+$ ]] && [ "$__resposta" -ge 1 ] && [ "$__resposta" -le "$#" ]; then
      printf -v "$__var" '%s' "$__resposta"
      return 0
    fi
    falha "Escolha de 1 a $#."
  done
}

# confirma "texto" -> 0 para sim
confirma() {
  local __resposta=""
  _prompt "$1"
  printf ' %s(S/n)%s: ' "$CINZA" "$NORMAL"
  ler __resposta
  [[ -z "$__resposta" || "$__resposta" =~ ^[SsYy]$ ]]
}

linha_ok() { printf '\r\033[K  %s%2s/%s%s  %s✓%s  %s\n' "$CINZA" "$1" "$2" "$NORMAL" "$VERDE" "$NORMAL" "$3"; }
linha_rodando() { printf '\r\033[K  %s%2s/%s%s  %s…%s  %s' "$CINZA" "$1" "$2" "$NORMAL" "$CIANO" "$NORMAL" "$3"; }
linha_erro() { printf '\r\033[K  %s%2s/%s%s  %s✗%s  %s\n' "$CINZA" "$1" "$2" "$NORMAL" "$VERMELHO" "$NORMAL" "$3"; }

# erro_fatal "o que falhou" "o que fazer"
erro_fatal() {
  echo
  printf '  %s%s✗ %s%s\n' "$VERMELHO" "$NEGRITO" "$1" "$NORMAL"
  [ -n "${2:-}" ] && printf '    %s\n' "$2"
  printf '    %sLog: %s · rode o mesmo comando de novo para continuar daqui%s\n\n' "$CINZA" "$LOG" "$NORMAL"
  exit 1
}
