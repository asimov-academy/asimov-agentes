#!/usr/bin/env bash
# Tela 4: bot.<domínio> precisa apontar para esta VPS antes de emitir o certificado.

ip_publico() {
  curl -4 -fsS --max-time 10 https://api.ipify.org 2>/dev/null ||
    curl -4 -fsS --max-time 10 https://ifconfig.me 2>/dev/null
}

ip_do_dominio() {
  dig +short A "$1" @1.1.1.1 2>/dev/null | grep -E '^[0-9.]+$' | tail -1
}

ip_da_cloudflare() {
  local faixas
  faixas=$(curl -fsS --max-time 10 https://www.cloudflare.com/ips-v4 2>/dev/null) || return 1
  python3 - "$1" "$faixas" <<'PY'
import ipaddress, sys
ip = ipaddress.ip_address(sys.argv[1])
sys.exit(0 if any(ip in ipaddress.ip_network(f.strip()) for f in sys.argv[2].split() if f.strip()) else 1)
PY
}

tela_dns() {
  estado_tem dns_ok && return 0
  local sub ip resolvido resposta
  sub=$(env_get SUBDOMINIO_BOT)
  titulo "Checagem do domínio"

  ip=$(ip_publico) || erro_fatal "Não consegui descobrir o IP público da VPS" "confira a internet da VPS"
  while true; do
    resolvido=$(ip_do_dominio "$sub")
    info "IP desta VPS:        $ip"
    info "$sub aponta para: ${resolvido:-nenhum IP}"
    echo

    if [ "$resolvido" = "$ip" ]; then
      printf '  %s[ OK ]%s O domínio aponta para esta VPS.\n' "$VERDE" "$NORMAL"
      estado_set dns_ok "$(date -Is)"
      return 0
    fi

    if [ -n "$resolvido" ] && ip_da_cloudflare "$resolvido"; then
      aviso "O domínio está passando pelo proxy da Cloudflare (nuvem laranja)."
      info "Na Cloudflare, deixe o registro '$sub' como 'Somente DNS' (nuvem cinza)."
    else
      aviso "O domínio ainda não aponta para esta VPS."
      info "No painel do seu domínio, crie o registro:"
      info "  Tipo: A    Nome: bot    Valor: $ip"
      info "A propagação pode levar alguns minutos."
    fi
    echo
    printf 'Enter para verificar de novo, ou S para sair e voltar depois: '
    IFS= read -r resposta </dev/tty || true
    if [[ "$resposta" =~ ^[Ss]$ ]]; then
      echo "Quando o domínio apontar, rode o mesmo comando: o setup continua daqui."
      exit 0
    fi
    echo
  done
}
