#!/usr/bin/env bash
# Roda os testes do backend com Postgres e Redis reais, dentro do Compose.
# Argumentos extras vão para o pytest: ./deploy/testar.sh testes/test_turno.py -k buffer
set -euo pipefail

SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"
# shellcheck source=deploy/compose.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/compose.sh"

dc up -d --wait postgres redis
# shellcheck disable=SC2016  # as variáveis expandem dentro do contêiner
dc exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select 1 from pg_database where datname = '\''asimov_teste'\''" | grep -q 1 || createdb -U "$POSTGRES_USER" asimov_teste'
dc --profile teste build teste
dc --profile teste run --rm teste pytest -q "$@"
