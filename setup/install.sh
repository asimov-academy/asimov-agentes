#!/usr/bin/env bash
# Uso na VPS:
#   bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)
# Para testar o que está na main em vez da versão marcada: ASIMOV_VERSAO=main antes do bash.
# Para atualizar o código de uma instalação existente (mantém .env, prompts e o progresso):
#   ASIMOV_ATUALIZAR=1 antes do bash.
#
# Baixa a versão da plataforma para ~/asimov-agentes e roda o setup.
# Se o projeto já existe, só roda o setup (retomada ou resumo).
set -euo pipefail

VERSAO="${ASIMOV_VERSAO:-v0.11.2}"
PACOTE="${ASIMOV_PACOTE:-https://codeload.github.com/asimov-academy/asimov-agentes/tar.gz/$VERSAO}"
SHA256="${ASIMOV_SHA256:-}"
DESTINO="${ASIMOV_DIR:-$HOME/asimov-agentes}"

if [ -f "$DESTINO/setup/instalar.sh" ] && [ -z "${ASIMOV_ATUALIZAR:-}" ]; then
  exec bash "$DESTINO/setup/instalar.sh"
fi

command -v curl >/dev/null 2>&1 || { echo "Instale o curl: apt-get install -y curl"; exit 1; }
command -v tar >/dev/null 2>&1 || { echo "Instale o tar: apt-get install -y tar"; exit 1; }

temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT

echo "Baixando a plataforma $VERSAO..."
curl -fsSL "$PACOTE" -o "$temp/pacote.tar.gz"
if [ -n "$SHA256" ]; then
  echo "$SHA256  $temp/pacote.tar.gz" | sha256sum -c --quiet - || {
    echo "O pacote baixado não confere com o checksum esperado. Abortando."
    exit 1
  }
fi

[ -f "$DESTINO/setup/instalar.sh" ] && echo "Atualizando o código em $DESTINO (.env, prompts e progresso ficam)."
mkdir -p "$DESTINO"
tar -xzf "$temp/pacote.tar.gz" -C "$DESTINO" --strip-components=1 --no-same-owner
exec bash "$DESTINO/setup/instalar.sh"
