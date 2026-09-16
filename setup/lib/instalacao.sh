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
  env_set_se_vazio LOG_NIVEL INFO
  for variavel in OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY; do
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
sobe_servicos() { dc up -d api worker caddy; }

espera_url() {
  local url=$1 tentativas=$2
  for _ in $(seq 1 "$tentativas"); do
    curl -fsS --max-time 10 "$url" && return 0
    sleep 5
  done
  return 1
}

tela_instalacao() {
  titulo "Instalação"
  PASSO_ATUAL=0
  PASSO_TOTAL=11
  local sub
  sub=$(env_get SUBDOMINIO_BOT)

  passo firewall "Configurando firewall (SSH, 80 e 443)" "veja o log; confira com 'ufw status'" firewall
  passo node "Verificando/Instalando Node.js LTS" "veja o log" instala_node
  passo uv "Verificando/Instalando Python uv" "veja o log" instala_uv
  passo agente_codigo "Verificando/Instalando $( [ "$(env_get AGENTE_CODIGO)" = codex ] && echo Codex || echo 'Claude Code')" \
    "veja o log" instala_agente_codigo
  passo segredos "Gerando senhas e chaves da instalação" "veja o log" --sem-repetir gera_segredos
  passo build "Instalando SDK de $(env_get PROVEDORES) e construindo a plataforma" \
    "veja o log; confira espaço em disco com 'df -h'" dc build api worker
  passo banco "Subindo banco de dados e Redis" "veja: docker compose logs postgres" sobe_banco
  passo migracoes "Criando as tabelas do banco" "veja o log" migra
  passo servicos "Subindo API, worker e HTTPS" "veja o log" sobe_servicos
  passo api_local "Conferindo a API" "veja: docker compose logs api" \
    --sem-repetir espera_url http://127.0.0.1:8000/health 24
  passo api_https "Conferindo https://$sub (certificado SSL)" \
    "o certificado não saiu. Confira se as portas 80 e 443 estão livres e se o domínio aponta para a VPS" \
    --sem-repetir espera_url "https://$sub/health" 36
}
