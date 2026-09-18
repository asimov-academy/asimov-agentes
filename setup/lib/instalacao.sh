#!/usr/bin/env bash
# shellcheck disable=SC2034  # PASSO_ATUAL e PASSO_TOTAL são lidas por passo(), em estado.sh
# Tela 5: firewall, ferramentas de desenvolvimento, segredos e a plataforma no ar.

firewall() {
  local porta
  # Libera a porta real do SSH antes de ligar o firewall, para não trancar o operador fora.
  for porta in $($SUDO ss -tlnpH 2>/dev/null | awk '/sshd/ {n=split($4,a,":"); print a[n]}' | sort -u); do
    $SUDO ufw allow "$porta/tcp"
  done
  $SUDO ufw allow OpenSSH
  $SUDO ufw allow 80/tcp
  $SUDO ufw allow 443/tcp
  $SUDO ufw --force enable
}

instala_node() {
  command -v node >/dev/null 2>&1 && return 0
  curl -fsSL https://deb.nodesource.com/setup_lts.x -o /tmp/nodesource.sh
  $SUDO bash /tmp/nodesource.sh
  apt_instala nodejs
}

instala_uv() {
  command -v uv >/dev/null 2>&1 || [ -x "$HOME/.local/bin/uv" ] && return 0
  curl -LsSf https://astral.sh/uv/install.sh | sh
}

instala_agente_codigo() {
  if [ "$(env_get AGENTE_CODIGO)" = codex ]; then
    command -v codex >/dev/null 2>&1 || $SUDO npm install -g @openai/codex
  else
    command -v claude >/dev/null 2>&1 || [ -x "$HOME/.local/bin/claude" ] ||
      curl -fsSL https://claude.ai/install.sh | bash
  fi
}

gera_segredos() {
  env_set_se_vazio POSTGRES_USER asimov
  env_set_se_vazio POSTGRES_DB asimov
  env_set_se_vazio POSTGRES_PASSWORD "$(openssl rand -hex 24)"
  env_set_se_vazio CHAVE_API_ADMIN "$(openssl rand -hex 32)"
  env_set_se_vazio CHAVE_CRIPTOGRAFIA "$(openssl rand -base64 32 | tr '+/' '-_')"
  # A chave da WAHA nasce aqui mesmo sem o contêiner dela: assim ligar o WhatsApp depois não
  # precisa reiniciar a API para ela enxergar a chave nova.
  env_set_se_vazio WAHA_API_KEY "$(openssl rand -hex 32)"
  env_set_se_vazio LOG_NIVEL INFO
  for variavel in OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY GROQ_API_KEY MODELO_FALLBACK; do
    env_set_se_vazio "$variavel" ""
  done
  # Os contêineres rodam com o usuário 1000 e criam os prompts de cada agente.
  mkdir -p "$RAIZ_PROJETO/prompts"
  $SUDO chown -R 1000:1000 "$RAIZ_PROJETO/prompts"
}

# Roda em toda execução: extrair uma atualização como root devolve prompts/ ao root, e a API
# (usuário 1000 no contêiner) deixaria de conseguir criar o prompt de um agente novo.
ajusta_permissoes() {
  mkdir -p "$RAIZ_PROJETO/prompts"
  $SUDO chown -R 1000:1000 "$RAIZ_PROJETO/prompts"
}

sobe_banco() { dc up -d --wait postgres redis; }
migra() { dc run --rm api alembic upgrade head; }
sobe_servicos() {
  dc up -d api worker caddy
  # O Caddyfile é montado, então atualizar o projeto muda o arquivo mas não o que o Caddy já
  # carregou: caminho público novo continuava respondendo 404 depois de `asimov atualizar`.
  # `reload` não derruba conexão; se ele falhar (contêiner recém-criado, por exemplo), reinicia.
  dc exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile >>"$LOG" 2>&1 ||
    dc restart caddy >>"$LOG" 2>&1 || true
}

espera_url() {
  local url=$1 tentativas=${2:-24}
  for _ in $(seq 1 "$tentativas"); do
    curl -fsS --max-time 10 "$url" && return 0
    sleep 5
  done
  return 1
}

tela_instalacao() {
  secao "Instalação"
  PASSO_ATUAL=0
  PASSO_TOTAL=11
  local sub
  sub=$(env_get SUBDOMINIO_BOT)
  # A IA é escolha de cada agente, feita depois: a imagem leva o SDK dos quatro provedores.
  env_set PROVEDORES "openai anthropic gemini groq"

  passo firewall "Firewall (SSH, 80 e 443)" "Confira com: ufw status" firewall
  passo node "Node.js" "Veja o log." instala_node
  passo uv "uv" "Veja o log." instala_uv
  passo agente_codigo "$(ia_nome)" "Veja o log." instala_agente_codigo
  passo segredos "Senhas e chaves" "Veja o log." --sem-repetir gera_segredos
  passo build "Plataforma" \
    "Confira o espaço em disco: df -h" dc build api worker
  passo banco "Banco e Redis" "Veja: source deploy/compose.sh && dc logs postgres" sobe_banco
  passo migracoes "Tabelas do banco" "Veja o log." migra
  passo servicos "API, worker e HTTPS" "Veja o log." sobe_servicos
  passo api_local "API respondendo" "Veja: source deploy/compose.sh && dc logs api" \
    --sem-repetir espera_url http://127.0.0.1:8000/health 24
  passo api_https "Certificado SSL em $sub" \
    "Confira se as portas 80 e 443 estão livres e se o domínio aponta para a VPS." \
    --sem-repetir espera_url "https://$sub/health" 36
}
