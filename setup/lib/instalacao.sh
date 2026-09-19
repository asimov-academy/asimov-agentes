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

# instala_timer_backup: dump do banco e cópia do .env todo dia de madrugada, com retenção.
# Roda no host, como o timer da WAHA: quem fala com o Docker é o host, nunca um contêiner.
instala_timer_backup() {
  local quando="*-*-* 03:20:00 America/Sao_Paulo"
  command -v systemctl >/dev/null 2>&1 || return 0
  if ! systemd-analyze calendar "$quando" >/dev/null 2>&1; then
    quando="*-*-* 03:20:00"
  fi
  $SUDO tee /etc/systemd/system/asimov-backup.service >/dev/null <<UNIDADE || return 1
[Unit]
Description=Backup diário do Asimov Agentes
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
Environment=HOME=$HOME
ExecStart=$RAIZ_PROJETO/deploy/backup.sh
UNIDADE
  $SUDO tee /etc/systemd/system/asimov-backup.timer >/dev/null <<UNIDADE || return 1
[Unit]
Description=Guarda o banco e o .env todo dia

[Timer]
OnCalendar=$quando
RandomizedDelaySec=20m
Persistent=true

[Install]
WantedBy=timers.target
UNIDADE
  $SUDO systemctl daemon-reload >/dev/null 2>&1 || return 1
  $SUDO systemctl enable --now asimov-backup.timer >/dev/null 2>&1 || return 1
  return 0
}

# confere_maquina: o que a VPS precisa ter antes de a instalação começar a demorar.
# Aviso, não impedimento: a pessoa pode saber de algo que a checagem não sabe, e travar a
# instalação por 200 MB de RAM a menos seria pior que deixá-la tentar.
confere_maquina() {
  local memoria disco
  memoria=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
  disco=$(df -m --output=avail "$RAIZ_PROJETO" 2>/dev/null | tail -1 | tr -d ' ' || echo 0)
  [ "${memoria:-0}" -ge 1900 ] || aviso "Esta VPS tem ${memoria} MB de memória. Abaixo de 2 GB, o build costuma ser morto no meio."
  [ "${disco:-0}" -ge 8000 ] || aviso "Restam ${disco} MB de disco. As imagens do Docker pedem uns 8 GB."
  return 0
}

# confere_proxy_do_dns: a nuvem laranja da Cloudflare responde pelo domínio e o Caddy nunca tira o
# certificado; o operador fica esperando um SSL que não vem. O IP dela é o sintoma visível.
confere_proxy_do_dns() {
  local sub ips
  sub=$(env_get SUBDOMINIO_BOT)
  [ -n "$sub" ] || return 0
  ips=$(dig +short "$sub" A 2>/dev/null || true)
  case "$ips" in
    104.16.* | 104.17.* | 104.18.* | 104.19.* | 104.20.* | 104.21.* | 172.6[4-9].* | 172.7[0-1].* | 188.114.* | 190.93.*)
      aviso "O DNS de $sub aponta para a Cloudflare. Desligue a nuvem laranja (modo DNS only), senão o certificado nunca sai."
      ;;
  esac
  return 0
}

tela_instalacao() {
  secao "Instalação"
  PASSO_ATUAL=0
  PASSO_TOTAL=13
  local sub
  sub=$(env_get SUBDOMINIO_BOT)

  confere_maquina
  confere_proxy_do_dns
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
  # Depois de a API responder: `sobe_waha` avisa a plataforma da manutenção antes de mexer no
  # contêiner. A WAHA entra na instalação porque o painel não sabe subir contêiner nenhum.
  passo whatsapp "WhatsApp na VPS (WAHA)" \
    "Veja: source deploy/compose.sh && dc logs waha" instala_waha
  # Depois de a plataforma estar no ar: backup de instalação que não subiu não serve para nada.
  passo backup "Backup diário" "Veja: systemctl status asimov-backup.timer" instala_timer_backup
  # O `.env` guarda a chave que decifra as credenciais dos canais: ninguém além do dono o lê.
  chmod 600 "$RAIZ_PROJETO/.env" 2>/dev/null || true
}
