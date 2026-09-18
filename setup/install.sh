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

VERSAO="${ASIMOV_VERSAO:-v0.24.0}"
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

# Atualizar sobrescreve os arquivos distribuídos, e alguns o operador é orientado a editar
# (modelos/privacidade.html, modelos/prompts, modelos/AGENTS.md.tmpl). Antes de extrair, uma cópia
# do que existe vai para ~/.asimov/antes-da-atualizacao/<data>, para nada se perder sem volta
# (auditoria de 2026-09-18, A15). O .env, os prompts dos agentes e o progresso nunca são tocados.
if [ -f "$DESTINO/setup/instalar.sh" ]; then
  echo "Atualizando o código em $DESTINO (.env, prompts e progresso ficam)."
  guardado="$HOME/.asimov/antes-da-atualizacao/$(date +%Y%m%d-%H%M%S)"
  if mkdir -p "$guardado" 2>/dev/null; then
    for pasta in modelos deploy; do
      [ -d "$DESTINO/$pasta" ] && cp -a "$DESTINO/$pasta" "$guardado/" 2>/dev/null || true
    done
    echo "Cópia do que havia em modelos/ e deploy/: $guardado"
  fi
fi
mkdir -p "$DESTINO"
tar -xzf "$temp/pacote.tar.gz" -C "$DESTINO" --strip-components=1 --no-same-owner
exec bash "$DESTINO/setup/instalar.sh"
