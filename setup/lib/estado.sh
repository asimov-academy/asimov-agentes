#!/usr/bin/env bash
# Estado do setup em arquivo CHAVE=VALOR (sem depender de jq, que só é instalado no passo 2)
# e segredos no .env do projeto. Permite retomar de onde parou.

estado_iniciar() {
  mkdir -p "$DIR_ESTADO"
  chmod 700 "$DIR_ESTADO"
  touch "$ARQ_ESTADO" "$LOG"
  chmod 600 "$ARQ_ESTADO" "$LOG"
}

estado_get() {
  local linha
  linha=$(grep -m1 "^$1=" "$ARQ_ESTADO" 2>/dev/null || true)
  printf '%s' "${linha#*=}"
}

estado_set() {
  local temp
  temp=$(mktemp)
  grep -v "^$1=" "$ARQ_ESTADO" >"$temp" 2>/dev/null || true
  printf '%s=%s\n' "$1" "$2" >>"$temp"
  mv "$temp" "$ARQ_ESTADO"
  chmod 600 "$ARQ_ESTADO"
}

estado_tem() {
  grep -q "^$1=" "$ARQ_ESTADO" 2>/dev/null
}

env_get() {
  local linha
  linha=$(grep -m1 "^$1=" "$ARQ_ENV" 2>/dev/null || true)
  printf '%s' "${linha#*=}"
}

# env_set CHAVE VALOR: grava no .env com permissão 600, substituindo o valor anterior.
env_set() {
  local temp
  [ -f "$ARQ_ENV" ] || install -m 600 /dev/null "$ARQ_ENV"
  temp=$(mktemp)
  grep -v "^$1=" "$ARQ_ENV" >"$temp" || true
  printf '%s=%s\n' "$1" "$2" >>"$temp"
  install -m 600 "$temp" "$ARQ_ENV"
  rm -f "$temp"
}

# env_set_se_vazio CHAVE VALOR: não troca segredo já gerado numa execução anterior.
env_set_se_vazio() {
  [ -n "$(env_get "$1")" ] || env_set "$1" "$2"
}

# tentar comando...: 1 tentativa e até 3 repetições (5, 15 e 45 s). Saída vai para o log.
tentar() {
  local espera
  for espera in 5 15 45 fim; do
    if "$@" >>"$LOG" 2>&1; then
      return 0
    fi
    [ "$espera" = fim ] && return 1
    printf '\n[repetindo em %s s] %s\n' "$espera" "$*" >>"$LOG"
    sleep "$espera"
  done
}

PASSO_ATUAL=0
PASSO_TOTAL=0

# passo ID "descrição" "o que fazer se falhar" [--sem-repetir] comando...
passo() {
  local id=$1 descricao=$2 dica=$3 repetir=1
  shift 3
  if [ "${1:-}" = "--sem-repetir" ]; then
    repetir=0
    shift
  fi
  PASSO_ATUAL=$((PASSO_ATUAL + 1))

  if estado_tem "passo_$id"; then
    linha_ok "$PASSO_ATUAL" "$PASSO_TOTAL" "$descricao"
    return 0
  fi

  linha_rodando "$PASSO_ATUAL" "$PASSO_TOTAL" "$descricao"
  printf '\n===== %s: %s =====\n' "$(date -Is)" "$descricao" >>"$LOG"
  local ok=1
  if [ "$repetir" -eq 1 ]; then
    tentar "$@" || ok=0
  else
    "$@" >>"$LOG" 2>&1 || ok=0
  fi

  if [ "$ok" -eq 1 ]; then
    estado_set "passo_$id" "$(date -Is)"
    linha_ok "$PASSO_ATUAL" "$PASSO_TOTAL" "$descricao"
  else
    linha_erro "$PASSO_ATUAL" "$PASSO_TOTAL" "$descricao"
    erro_fatal "$descricao" "$dica"
  fi
}
