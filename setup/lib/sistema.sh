#!/usr/bin/env bash
# shellcheck disable=SC2034  # PASSO_ATUAL e PASSO_TOTAL são lidas por passo(), em estado.sh
# Telas 1 e 2: boas-vindas com aceite e preparação da VPS vazia.

MEMORIA_MINIMA_KB=1800000
DISCO_MINIMO_KB=20000000

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
APT_OPCOES=(-y -o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold)

tela_boas_vindas() {
  estado_tem aceite && return 0
  banner_asimov
  moldura
  cat <<'TEXTO'
  Este instalador prepara esta VPS para rodar agentes de IA de atendimento
  no Chatwoot, com a estrutura pronta para você evoluir em vibecoding com
  Claude Code ou Codex. Ele atualiza o sistema, instala Docker, banco de
  dados, HTTPS e a plataforma dos agentes.

  Licença MIT. Você pode usar, copiar, modificar e distribuir, mantendo o
  crédito à Asimov Academy (asimov.academy).
TEXTO
  moldura
  echo
  local resposta
  printf 'Ao digitar Y você aceita e concorda com as orientações acima (Y/N): '
  IFS= read -r resposta </dev/tty || true
  if [[ ! "$resposta" =~ ^[YySs]$ ]]; then
    echo "Instalação cancelada. Nada foi alterado."
    exit 0
  fi
  estado_set aceite "$(date -Is)"
}

verifica_ubuntu() {
  # shellcheck disable=SC1091
  . /etc/os-release
  [ "${ID:-}" = "ubuntu" ] && [ "${VERSION_ID:-}" = "24.04" ]
}

verifica_recursos() {
  local memoria disco
  memoria=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
  disco=$(df --output=avail -k / | tail -1 | tr -d ' ')
  echo "memória: ${memoria} kB, disco livre: ${disco} kB"
  [ "$memoria" -ge "$MEMORIA_MINIMA_KB" ] && [ "$disco" -ge "$DISCO_MINIMO_KB" ]
}

apt_update() { $SUDO apt-get -o DPkg::Lock::Timeout=600 update; }
apt_upgrade() { $SUDO apt-get "${APT_OPCOES[@]}" upgrade; }
apt_instala() { $SUDO apt-get "${APT_OPCOES[@]}" install "$@"; }

instala_docker() {
  if command -v docker >/dev/null 2>&1 && $SUDO docker compose version >/dev/null 2>&1; then
    return 0
  fi
  curl -fsSL https://get.docker.com -o /tmp/instala-docker.sh
  $SUDO sh /tmp/instala-docker.sh
  $SUDO systemctl enable --now docker
  $SUDO docker compose version
}

tela_iniciando() {
  banner_iniciando
  PASSO_ATUAL=0
  PASSO_TOTAL=9
  passo ubuntu "Verificando Ubuntu 24.04" \
    "este setup só roda em Ubuntu 24.04. Reinstale a VPS com essa imagem." \
    --sem-repetir verifica_ubuntu
  passo recursos "Verificando memória e disco" \
    "a VPS precisa de pelo menos 2 GB de RAM e 20 GB livres. Aumente o plano." \
    --sem-repetir verifica_recursos
  passo update "Fazendo Update" "confira a internet da VPS com: ping -c 3 archive.ubuntu.com" apt_update
  passo upgrade "Fazendo Upgrade" "rode 'apt-get upgrade' manualmente para ver o erro" apt_upgrade
  passo base "Verificando/Instalando sudo, apt-utils e dialog" "veja o log" apt_instala sudo apt-utils dialog
  passo ferramentas "Verificando/Instalando jq, curl e dnsutils" "veja o log" \
    apt_instala jq curl ca-certificates gnupg dnsutils openssl
  passo git "Verificando/Instalando Git" "veja o log" apt_instala git
  passo python "Verificando/Instalando python3 e ufw" "veja o log" apt_instala python3 ufw
  passo docker "Verificando/Instalando Docker" \
    "confira se a VPS alcança https://get.docker.com e rode de novo" instala_docker
}
