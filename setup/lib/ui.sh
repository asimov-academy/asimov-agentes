#!/usr/bin/env bash
# Tela: cores, banners, passos numerados, perguntas e erros.

AMARELO=$'\033[0;33m'
VERDE=$'\033[0;32m'
VERMELHO=$'\033[0;31m'
NEGRITO=$'\033[1m'
NORMAL=$'\033[0m'

moldura() {
  printf '%s%s%s\n' "$AMARELO" "==========================================================================" "$NORMAL"
}

banner_asimov() {
  clear
  cat <<'ARTE'

     █████╗ ███████╗██╗███╗   ███╗ ██████╗ ██╗   ██╗
    ██╔══██╗██╔════╝██║████╗ ████║██╔═══██╗██║   ██║
    ███████║███████╗██║██╔████╔██║██║   ██║██║   ██║
    ██╔══██║╚════██║██║██║╚██╔╝██║██║   ██║╚██╗ ██╔╝
    ██║  ██║███████║██║██║ ╚═╝ ██║╚██████╔╝ ╚████╔╝
    ╚═╝  ╚═╝╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝   ╚═══╝

     █████╗  ██████╗ █████╗ ██████╗ ███████╗███╗   ███╗██╗   ██╗
    ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝████╗ ████║╚██╗ ██╔╝
    ███████║██║     ███████║██║  ██║█████╗  ██╔████╔██║ ╚████╔╝
    ██╔══██║██║     ██╔══██║██║  ██║██╔══╝  ██║╚██╔╝██║  ╚██╔╝
    ██║  ██║╚██████╗██║  ██║██████╔╝███████╗██║ ╚═╝ ██║   ██║
    ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝     ╚═╝   ╚═╝
ARTE
  printf '\n%38s%sv. %s%s\n\n' "" "$AMARELO" "$VERSAO" "$NORMAL"
}

banner_iniciando() {
  clear
  moldura
  cat <<'ARTE'
  ██╗███╗   ██╗██╗ ██████╗██╗ █████╗ ███╗   ██╗██████╗  ██████╗
  ██║████╗  ██║██║██╔════╝██║██╔══██╗████╗  ██║██╔══██╗██╔═══██╗
  ██║██╔██╗ ██║██║██║     ██║███████║██╔██╗ ██║██║  ██║██║   ██║
  ██║██║╚██╗██║██║██║     ██║██╔══██║██║╚██╗██║██║  ██║██║   ██║
  ██║██║ ╚████║██║╚██████╗██║██║  ██║██║ ╚████║██████╔╝╚██████╔╝
  ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝
ARTE
  printf '%34s%sv. %s%s\n' "" "$AMARELO" "$VERSAO" "$NORMAL"
  moldura
  echo
}

titulo() {
  echo
  moldura
  printf '  %s%s%s\n' "$NEGRITO" "$1" "$NORMAL"
  moldura
  echo
}

# pergunta VAR "texto" [padrão]
pergunta() {
  local __var=$1 texto=$2 padrao=${3:-} resposta
  while true; do
    if [ -n "$padrao" ]; then
      printf '%s [%s]: ' "$texto" "$padrao"
    else
      printf '%s: ' "$texto"
    fi
    IFS= read -r resposta </dev/tty || true
    resposta=${resposta:-$padrao}
    if [ -n "$resposta" ]; then
      printf -v "$__var" '%s' "$resposta"
      return 0
    fi
    echo "  Resposta obrigatória."
  done
}

# pergunta_opcional VAR "texto": aceita Enter vazio.
pergunta_opcional() {
  local __var=$1 texto=$2 resposta
  printf '%s (Enter para pular): ' "$texto"
  IFS= read -r resposta </dev/tty || true
  printf -v "$__var" '%s' "$resposta"
}

# pergunta_secreta VAR "texto": não mostra o que é digitado.
pergunta_secreta() {
  local __var=$1 texto=$2 resposta
  while true; do
    printf '%s: ' "$texto"
    IFS= read -rs resposta </dev/tty || true
    echo
    if [ -n "$resposta" ]; then
      printf -v "$__var" '%s' "$resposta"
      return 0
    fi
    echo "  Resposta obrigatória."
  done
}

# escolha VAR "texto" opção1 opção2 ...: devolve o número escolhido.
escolha() {
  local __var=$1 texto=$2 resposta i item
  shift 2
  echo "$texto"
  i=1
  for item in "$@"; do
    printf '  %s) %s\n' "$i" "$item"
    i=$((i + 1))
  done
  while true; do
    printf 'Digite o número: '
    IFS= read -r resposta </dev/tty || true
    if [[ "$resposta" =~ ^[0-9]+$ ]] && [ "$resposta" -ge 1 ] && [ "$resposta" -le "$#" ]; then
      printf -v "$__var" '%s' "$resposta"
      return 0
    fi
    echo "  Escolha um número entre 1 e $#."
  done
}

# confirma "texto" -> 0 para sim
confirma() {
  local resposta
  printf '%s (S/n): ' "$1"
  IFS= read -r resposta </dev/tty || true
  [[ -z "$resposta" || "$resposta" =~ ^[SsYy]$ ]]
}

info() { printf '  %s\n' "$*"; }
aviso() { printf '  %s%s%s\n' "$AMARELO" "$*" "$NORMAL"; }

linha_ok() { printf '\r\033[K%s/%s - [ %sOK%s ] - %s\n' "$1" "$2" "$VERDE" "$NORMAL" "$3"; }
linha_rodando() { printf '\r\033[K%s/%s - [ .. ] - %s' "$1" "$2" "$3"; }
linha_erro() { printf '\r\033[K%s/%s - [ %sERRO%s ] - %s\n' "$1" "$2" "$VERMELHO" "$NORMAL" "$3"; }

# erro_fatal "o que falhou" "o que fazer"
erro_fatal() {
  echo
  printf '%s[ ERRO ]%s %s\n' "$VERMELHO" "$NORMAL" "$1"
  [ -n "${2:-}" ] && printf '  O que fazer: %s\n' "$2"
  printf '  Log completo: %s\n' "$LOG"
  printf '  Depois de resolver, rode o mesmo comando de novo: o setup continua de onde parou.\n\n'
  exit 1
}
