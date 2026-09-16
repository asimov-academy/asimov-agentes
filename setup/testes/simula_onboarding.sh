#!/usr/bin/env bash
# Simula o onboarding inteiro sem VPS: respostas vêm de setup/testes/respostas.txt,
# rede, DNS e API são falsos. Serve para conferir telas e fluxo depois de mexer no setup.
#   ASIMOV_TTY=setup/testes/respostas.txt bash setup/testes/simula_onboarding.sh
# Precisa de bash 4+ para date -Is (no macOS, date -Is falha mas o fluxo segue).
set -Eeuo pipefail
RAIZ_PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR=$(mktemp -d); export HOME=$DIR
source $RAIZ_PROJETO/setup/lib/base.sh
ARQ_ENV=$DIR/.env; estado_iniciar
clear() { :; }
consulta_provedor() {
  local provedor=$1 chave=$2; shift 2
  case "$*" in *http_code*) [ "$chave" = "boa" ] && echo 200 || echo 401; return ;; esac
  case "$provedor" in
    openai) echo '{"data":[{"id":"gpt-4o"},{"id":"gpt-5.5"},{"id":"whisper-1"},{"id":"gpt-4o-transcribe"},{"id":"text-embedding-3-small"},{"id":"gpt-5-mini"},{"id":"gpt-realtime"},{"id":"dall-e-3"},{"id":"gpt-5.1"}]}' ;;
    groq) echo '{"data":[{"id":"llama-3.3-70b-versatile"},{"id":"whisper-large-v3-turbo"},{"id":"meta-llama/llama-guard-4-12b"},{"id":"openai/gpt-oss-120b"}]}' ;;
  esac
}
ip_publico() { echo 203.0.113.10; }
ip_do_dominio() { local n; n=$(cat $DIR/n 2>/dev/null || echo 0); echo $((n+1)) > $DIR/n; [ "$n" -ge 2 ] && echo 203.0.113.10 || true; }
ipv6_do_dominio() { :; }
ip_da_cloudflare() { return 1; }
INTERVALO_DNS=0.3
api() {
  case "$1 $2" in
    "POST /admin/canais/chatwoot/descobrir") API_STATUS=200; API_RESPOSTA='{"contas":[{"id":4,"nome":"Loja Exemplo","caixas":[{"id":1,"nome":"BecomApp"},{"id":3,"nome":"WhatsApp"}]},{"id":3,"nome":"Contour","caixas":[{"id":9,"nome":"Site"}]}]}' ;;
    "GET /admin/clientes") API_STATUS=200; API_RESPOSTA='[{"id":"c1","nome":"Loja Exemplo"},{"id":"c2","nome":"Padaria Pão Quente"}]' ;;
    "POST /admin/clientes") API_STATUS=201; API_RESPOSTA='{"id":"c9"}' ;;
    "GET /admin/agentes") API_STATUS=200; API_RESPOSTA='[{"cliente_id":"c1","nome":"Luiz","canal":"chatwoot","modelo_conversa":"openai:gpt-5.5"},{"cliente_id":"c2","nome":"Bia","canal":"chatwoot","modelo_conversa":"groq:llama-3.3-70b-versatile"}]' ;;
    *) API_STATUS=201; API_RESPOSTA='{"id":"a1","url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/x"}' ;;
  esac
}
banner_asimov; tela_boas_vindas; tela_modo; tela_dados; tela_modelos; tela_dns
tela_primeiro_agente
estado_set instalacao_concluida x
mostra_resumo
lista_agentes
