#!/usr/bin/env bash
# Tela 4: bot.<domínio> precisa apontar para esta VPS antes de emitir o certificado.
#
# Toda consulta aqui termina com `|| true`: domínio sem registro é o caso normal desta tela,
# e com `set -e` um grep sem resultado derrubaria o setup em silêncio.

INTERVALO_DNS=15

ip_publico() {
  curl -4 -fsS --max-time 10 https://api.ipify.org 2>/dev/null ||
    curl -4 -fsS --max-time 10 https://ifconfig.me 2>/dev/null || true
}

ip_do_dominio() {
  { dig +short A "$1" @1.1.1.1 2>/dev/null | grep -E '^[0-9.]+$' | tail -1; } || true
}

ipv6_do_dominio() {
  { dig +short AAAA "$1" @1.1.1.1 2>/dev/null | grep ':' | tail -1; } || true
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

instrucoes_dns() {
  local ip=$1 dominio=$2
  printf '  %sCrie este registro no painel onde o domínio %s é gerenciado:%s\n' "$NEGRITO" "$dominio" "$NORMAL"
  echo
  info "  Tipo:  A"
  info "  Nome:  bot"
  info "  Valor: $ip"
  info "  TTL:   300 (ou o menor disponível)"
  echo
  info "Na Hostinger: hPanel > Domínios > $dominio > DNS / Nameservers > Gerenciar registros DNS."
  info "Na Cloudflare: DNS > Records > Add record, com o proxy desligado (nuvem cinza)."
  info "Na Registro.br: Editar zona > Nova entrada."
  echo
  info "Se já existir um registro 'bot' com outro valor, edite em vez de criar outro."
}

tela_dns() {
  estado_tem dns_ok && return 0
  local sub dominio ip resolvido ipv6 resposta
  sub=$(env_get SUBDOMINIO_BOT)
  dominio=$(env_get DOMINIO_BASE)
  titulo "Checagem do domínio"

  ip=$(ip_publico)
  [ -n "$ip" ] || erro_fatal "Não consegui descobrir o IP público da VPS" "confira a internet da VPS"

  resolvido=$(ip_do_dominio "$sub")
  if [ "$resolvido" != "$ip" ]; then
    instrucoes_dns "$ip" "$dominio"
  fi

  while true; do
    resolvido=$(ip_do_dominio "$sub")
    ipv6=$(ipv6_do_dominio "$sub")
    info "IP desta VPS:             $ip"
    info "$sub aponta para: ${resolvido:-nenhum IP ainda}"

    if [ "$resolvido" = "$ip" ]; then
      if [ -n "$ipv6" ]; then
        echo
        aviso "Existe também um registro AAAA (IPv6) para $sub: $ipv6"
        info "Apague esse registro AAAA: o certificado SSL é validado por IPv6 quando ele existe."
      else
        echo
        printf '  %s[ OK ]%s O domínio aponta para esta VPS.\n' "$VERDE" "$NORMAL"
        estado_set dns_ok "$(date -Is)"
        return 0
      fi
    elif [ -n "$resolvido" ] && ip_da_cloudflare "$resolvido"; then
      echo
      aviso "O domínio está passando pelo proxy da Cloudflare (nuvem laranja)."
      info "Na Cloudflare, deixe o registro 'bot' como 'Somente DNS' (nuvem cinza)."
    elif [ -n "$resolvido" ]; then
      echo
      aviso "O registro 'bot' existe, mas aponta para outro IP ($resolvido)."
      info "Edite o valor para $ip."
    fi

    echo
    printf 'Verificando de novo em %s s. Enter para verificar agora, S para sair e voltar depois: ' "$INTERVALO_DNS"
    resposta=""
    IFS= read -r -t "$INTERVALO_DNS" resposta </dev/tty || true
    echo
    if [[ "$resposta" =~ ^[Ss]$ ]]; then
      echo "Quando o domínio apontar, rode o mesmo comando: o setup continua daqui."
      exit 0
    fi
  done
}
