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
    "POST /admin/canais/chatwoot/descobrir")
      # Como a API: sem token guardado pede o token (428); o que vier fica guardado.
      if [ ! -f "$DIR/token" ] && ! grep -q token_admin <<<"$3"; then API_STATUS=428; API_RESPOSTA='{"detail":"informe o token"}'; return; fi
      touch "$DIR/token"; API_STATUS=200; API_RESPOSTA='{"contas":[{"id":4,"nome":"Loja Exemplo","caixas":[{"id":1,"nome":"BecomApp"},{"id":3,"nome":"WhatsApp"}],"atendentes":[{"id":7,"nome":"Joana"}],"times":[{"id":2,"nome":"Vendas"}]},{"id":3,"nome":"Contour","caixas":[{"id":9,"nome":"Site"}]}]}' ;;
    "GET /admin/clientes") API_STATUS=200; API_RESPOSTA='[{"id":"c1","nome":"Loja Exemplo"},{"id":"c2","nome":"Padaria Pão Quente"}]' ;;
    "POST /admin/clientes") API_STATUS=201; API_RESPOSTA='{"id":"c9"}' ;;
    "PATCH /admin/clientes/c1/agentes/a1") API_STATUS=200; API_RESPOSTA=$(jq -c --argjson m "$3" '. + $m' <<<'{"id":"a1","cliente_id":"c1","nome":"Luiz","canal":"chatwoot","ativo":true,"url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/tok1","buffer_segundos":8,"max_mensagens_por_resposta":3,"modelo_conversa":"openai:gpt-5.5","modelo_fallback":null,"modelo_auxiliar":"openai:gpt-5.5","modelo_visao":"openai:gpt-5-mini","modelo_transcricao":"openai:whisper-1","handoff_destino":null,"credenciais":{"url":"https://chatwoot.exemplo.com.br","account_id":4}}') ;;
    "GET /admin/agentes") API_STATUS=200; API_RESPOSTA='[{"id":"a1","cliente_id":"c1","nome":"Luiz","canal":"chatwoot","ativo":true,"url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/tok1","buffer_segundos":8,"max_mensagens_por_resposta":3,"modelo_conversa":"openai:gpt-5.5","modelo_fallback":null,"modelo_auxiliar":"openai:gpt-5.5","modelo_visao":"openai:gpt-5-mini","modelo_transcricao":"openai:whisper-1","handoff_destino":null,"credenciais":{"url":"https://chatwoot.exemplo.com.br","account_id":4}},{"id":"a2","cliente_id":"c2","nome":"Bia","canal":"chatwoot","ativo":true,"url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/tok2","modelo_conversa":"groq:llama-3.3-70b-versatile","handoff_destino":{"tipo":"time","id":2,"nome":"Vendas"},"credenciais":{"url":"https://chatwoot.exemplo.com.br","account_id":3}}]' ;;
    "GET /admin/agentes?cliente_id=c1") API_STATUS=200; API_RESPOSTA='[]' ;;
    "DELETE /admin/clientes/c1/agentes/a1") API_STATUS=200; API_RESPOSTA='{"removido":true,"canal_desconectado":true}' ;;
    "GET /admin/canais/chatwoot/acessos") API_STATUS=200; API_RESPOSTA='[{"endereco":"https://chatwoot.exemplo.com.br","atualizado_em":"2026-09-16T22:00:00Z"}]' ;;
    "DELETE /admin/canais/chatwoot/acessos?endereco=https%3A%2F%2Fchatwoot.exemplo.com.br") API_STATUS=204; API_RESPOSTA='' ;;
    "DELETE /admin/clientes/c1") API_STATUS=204; API_RESPOSTA='' ;;
    "GET /admin/consumo?dias=7") API_STATUS=200; API_RESPOSTA='{"agentes":[{"cliente_id":"c1","cliente":"Loja Exemplo","agente_id":"a1","agente":"Luiz","turnos":12,"chamadas":15,"tokens_entrada":81200,"tokens_saida":1900,"custo_estimado":"0.412300","sem_custo":0}],"falhas":[]}' ;;
    "GET /admin/consumo?dias=30") API_STATUS=200; API_RESPOSTA='{"agentes":[{"cliente_id":"c1","cliente":"Loja Exemplo","agente_id":"a1","agente":"Luiz","turnos":480,"chamadas":530,"tokens_entrada":3100000,"tokens_saida":52000,"custo_estimado":"12.805","sem_custo":3},{"cliente_id":"c2","cliente":"Padaria Pão Quente","agente_id":"a2","agente":"Bia","turnos":40,"chamadas":40,"tokens_entrada":300,"tokens_saida":90,"custo_estimado":"0.05","sem_custo":0}],"falhas":[{"criado_em":"2026-09-16T21:05:08.123456Z","tipo":"envio_falhou","detalhe":{"erro":"HTTPStatusError(500)"},"cliente":"Loja Exemplo","agente":"Luiz"},{"criado_em":"2026-09-15T08:00:00Z","tipo":"webhook_token_desconhecido","detalhe":{"canal":"chatwoot"},"cliente":null,"agente":null}]}' ;;
    *) API_STATUS=201; API_RESPOSTA='{"id":"a1","url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/x"}' ;;
  esac
}
banner_asimov; tela_boas_vindas; tela_modo; tela_dados; tela_modelos; tela_dns
tela_primeiro_agente
estado_set instalacao_concluida x
mostra_resumo
lista_agentes
# Atualização de uma instalação anterior ao handoff: agente sem destino.
estado_remove handoff_perguntado
tela_handoff_pendente
# Menu: editar buffer e modelo do resumo, remover agente e empresa, consumo, esquecer token, sair.
menu_operador
