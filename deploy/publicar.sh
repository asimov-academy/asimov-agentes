#!/usr/bin/env bash
# Publica as mudanças do projeto: testes, build, migrações, serviços e health check.
# Nada sobe se um teste falhar.
set -euo pipefail

SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"
# shellcheck source=deploy/compose.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/compose.sh"

echo "==> Testes"
if ! "$RAIZ_PROJETO/deploy/testar.sh"; then
  echo "[ ERRO ] Testes falharam. Nada foi publicado."
  exit 1
fi

echo "==> Build"
dc build api worker

echo "==> Migrações"
dc run --rm api alembic upgrade head

echo "==> Subindo serviços"
dc up -d api worker caddy
# O Caddyfile é montado: `up -d` não recria o contêiner quando só o arquivo muda, e o Caddy segue
# com a configuração que já carregou. Sem isto, caminho público novo responde 404 até alguém
# reiniciar na mão (auditoria de 2026-09-18, A16; mesma armadilha corrigida no setup na v0.16.1).
dc exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile ||
  dc restart caddy || true

echo "==> Health check"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[ OK ] Publicado."
    exit 0
  fi
  sleep 2
done
echo "[ ERRO ] A API não respondeu em 60 s. Veja: docker compose logs api"
exit 1
