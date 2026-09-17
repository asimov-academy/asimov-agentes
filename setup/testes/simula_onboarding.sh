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
# WAHA: o contêiner e o desenho do QR code não existem aqui.
garante_waha() { ok "WAHA no ar (simulado)"; }
espera_waha_no_ar() { :; }
# Docker Hub e Compose não existem aqui: a tag nova vem de mentira e o `dc` só registra.
curl() { case "$*" in *hub.docker.com*) echo '{"results":[{"name":"gows-2026.9.1"},{"name":"gows-arm-2026.9.1"},{"name":"gows-2026.8.2"},{"name":"gows-arm-2026.8.2"},{"name":"gows"},{"name":"dev"}]}' ;; *) return 1 ;; esac; }
dc() { echo "dc $*" >>"$DIR/dc.log"; }
qrencode() { printf '  [QR code de %s]\n' "${*: -1}"; }
WAHA_ESPERA_STATUS=0
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
    "PATCH /admin/clientes/c1/agentes/a1") API_STATUS=200; API_RESPOSTA=$(jq -c --argjson m "$3" '. + $m' <<<'{"id":"a1","cliente_id":"c1","nome":"Luiz","canal":"chatwoot","ativo":true,"url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/tok1","buffer_segundos":8,"max_mensagens_por_resposta":3,"modelo_conversa":"openai:gpt-5.5","modelo_fallback":null,"modelo_auxiliar":"openai:gpt-5.5","modelo_visao":"openai:gpt-5-mini","modelo_transcricao":"openai:whisper-1","handoff_destino":null,"digitacao_caracteres_por_segundo":6,"digitacao_maximo_segundos":20,"ferramentas":["calculadora","busca_web"],"credenciais":{"url":"https://chatwoot.exemplo.com.br","account_id":4}}') ;;
    "GET /admin/agentes") API_STATUS=200; API_RESPOSTA='[{"id":"a4","cliente_id":"c1","nome":"Carlos","canal":"waha","ativo":true},{"id":"a1","cliente_id":"c1","nome":"Luiz","canal":"chatwoot","ativo":true,"url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/tok1","buffer_segundos":8,"max_mensagens_por_resposta":3,"modelo_conversa":"openai:gpt-5.5","modelo_fallback":null,"modelo_auxiliar":"openai:gpt-5.5","modelo_visao":"openai:gpt-5-mini","modelo_transcricao":"openai:whisper-1","handoff_destino":null,"digitacao_caracteres_por_segundo":6,"digitacao_maximo_segundos":20,"ferramentas":["calculadora","busca_web"],"credenciais":{"url":"https://chatwoot.exemplo.com.br","account_id":4}},{"id":"a2","cliente_id":"c2","nome":"Bia","canal":"chatwoot","ativo":true,"url_webhook":"https://bot.exemplo.com.br/webhook/chatwoot/tok2","modelo_conversa":"groq:llama-3.3-70b-versatile","handoff_destino":{"tipo":"time","id":2,"nome":"Vendas"},"credenciais":{"url":"https://chatwoot.exemplo.com.br","account_id":3}}]' ;;
    "GET /admin/agentes?cliente_id=c1") API_STATUS=200; API_RESPOSTA='[]' ;;
    "DELETE /admin/clientes/c1/agentes/a1") API_STATUS=200; API_RESPOSTA='{"removido":true,"canal_desconectado":true}' ;;
    "GET /admin/ferramentas") API_STATUS=200; API_RESPOSTA='[{"nome":"calculadora","rotulo":"Calculadora","descricao":"contas exatas","padrao":false},{"nome":"busca_web","rotulo":"Busca na web","descricao":"pesquisa na internet","padrao":false}]' ;;
    "GET /admin/canais/chatwoot/acessos") API_STATUS=200; API_RESPOSTA='[{"endereco":"https://chatwoot.exemplo.com.br","atualizado_em":"2026-09-16T22:00:00Z"}]' ;;
    "DELETE /admin/canais/chatwoot/acessos?endereco=https%3A%2F%2Fchatwoot.exemplo.com.br") API_STATUS=204; API_RESPOSTA='' ;;
    "DELETE /admin/clientes/c1") API_STATUS=204; API_RESPOSTA='' ;;
    "GET /admin/consumo?dias=7") API_STATUS=200; API_RESPOSTA='{"agentes":[{"cliente_id":"c1","cliente":"Loja Exemplo","agente_id":"a1","agente":"Luiz","turnos":12,"chamadas":15,"tokens_entrada":81200,"tokens_saida":1900,"custo_estimado":"0.412300","sem_custo":0}],"falhas":[]}' ;;
    "GET /admin/consumo?dias=30") API_STATUS=200; API_RESPOSTA='{"agentes":[{"cliente_id":"c1","cliente":"Loja Exemplo","agente_id":"a1","agente":"Luiz","turnos":480,"chamadas":530,"tokens_entrada":3100000,"tokens_saida":52000,"custo_estimado":"12.805","sem_custo":3},{"cliente_id":"c2","cliente":"Padaria Pão Quente","agente_id":"a2","agente":"Bia","turnos":40,"chamadas":40,"tokens_entrada":300,"tokens_saida":90,"custo_estimado":"0.05","sem_custo":0}],"falhas":[{"criado_em":"2026-09-16T21:05:08.123456Z","tipo":"envio_falhou","detalhe":{"erro":"HTTPStatusError(500)"},"cliente":"Loja Exemplo","agente":"Luiz"},{"criado_em":"2026-09-15T08:00:00Z","tipo":"webhook_token_desconhecido","detalhe":{"canal":"chatwoot"},"cliente":null,"agente":null}]}' ;;
    "POST /admin/clientes/c1/agentes")
      if grep -q '"canal": *"waha"' <<<"$3"; then
        API_STATUS=201; API_RESPOSTA='{"id":"a4","cliente_id":"c1","nome":"Carlos","canal":"waha","ativo":true,"contatos_permitidos":[],"buffer_segundos":8,"max_mensagens_por_resposta":3,"modelo_conversa":"openai:gpt-5.5","modelo_fallback":null,"modelo_auxiliar":"openai:gpt-5.5","modelo_visao":"openai:gpt-5-mini","modelo_transcricao":"openai:whisper-1","handoff_destino":null,"retomada_automatica_horas":4,"digitacao_caracteres_por_segundo":6,"digitacao_maximo_segundos":20,"ferramentas":[],"arquivo_prompt":"loja-exemplo/carlos/persona.md","credenciais":{"sessao":"carlos-a1b2c3","hmac_key":"***"}}'; echo "$3" >"$DIR/criado_waha"
      else
        API_STATUS=201; API_RESPOSTA='{"id":"a3","cliente_id":"c1","nome":"Ana","canal":"nativo","ativo":true,"buffer_segundos":2,"arquivo_prompt":"loja-exemplo/ana/persona.md","credenciais":{}}'; echo "$3" >"$DIR/criado_nativo"
      fi ;;
    "GET /admin/clientes/c1/agentes/a4/waha")
      # Primeira consulta: esperando a leitura. Segunda: número pareado.
      if [ -f "$DIR/qr_visto" ]; then
        API_STATUS=200; API_RESPOSTA='{"status":"WORKING","pareado":true,"numero":"5511988887777","nome":"Carlos","qr":null}'
      else
        touch "$DIR/qr_visto"; API_STATUS=200; API_RESPOSTA='{"status":"SCAN_QR_CODE","pareado":false,"numero":null,"nome":null,"qr":"2@abc123"}'
      fi ;;
    "POST /admin/clientes/c1/agentes/a4/waha/numero") API_STATUS=200; API_RESPOSTA=$(jq -c '{existe: true, chat_id: (.telefone + "@c.us"), telefone: .telefone}' <<<"$3") ;;
    "GET /admin/clientes/c1/agentes/a4/waha/grupos") API_STATUS=200; API_RESPOSTA='[{"chat_id": "120363110@g.us", "nome": "Atendimento Loja Exemplo"}, {"chat_id": "120363111@g.us", "nome": "Avisos da equipe"}, {"chat_id": "120363112@g.us", "nome": "Carga e entrega"}, {"chat_id": "120363113@g.us", "nome": "Diretoria"}, {"chat_id": "120363114@g.us", "nome": "Estoque"}, {"chat_id": "120363115@g.us", "nome": "Financeiro"}, {"chat_id": "120363116@g.us", "nome": "Fornecedores"}, {"chat_id": "120363117@g.us", "nome": "Marketing"}, {"chat_id": "120363118@g.us", "nome": "Pós-venda"}, {"chat_id": "120363119@g.us", "nome": "Suporte técnico"}, {"chat_id": "1203631110@g.us", "nome": "Time de vendas"}, {"chat_id": "1203631111@g.us", "nome": "Urgências"}]' ;;
    "PATCH /admin/clientes/c1/agentes/a4") API_STATUS=200; API_RESPOSTA=$(jq -c --argjson m "$3" '. + $m' <<<'{"id":"a4","cliente_id":"c1","nome":"Carlos","canal":"waha","ativo":true,"contatos_permitidos":[],"buffer_segundos":8,"max_mensagens_por_resposta":3,"modelo_conversa":"openai:gpt-5.5","modelo_fallback":null,"modelo_auxiliar":"openai:gpt-5.5","modelo_visao":"openai:gpt-5-mini","modelo_transcricao":"openai:whisper-1","handoff_destino":null,"retomada_automatica_horas":4,"digitacao_caracteres_por_segundo":6,"digitacao_maximo_segundos":20,"ferramentas":[],"credenciais":{"sessao":"carlos-a1b2c3"}}'); echo "$3" >"$DIR/patch_waha" ;;
    "POST /admin/clientes/c1/agentes/a3/terminal") API_STATUS=200; API_RESPOSTA='{"conversa":"k1","conversa_id":"u1","agendada":true}' ;;
    "GET /admin/clientes/c1/agentes/a3/terminal/k1?depois=0") API_STATUS=200; API_RESPOSTA='{"mensagens":[{"id":"m1","texto":"Oi! Sou a Ana.\nComo posso ajudar?"}],"proxima":1,"digitando":false,"respondendo":false,"turno":{"id":"t1","modelo":"openai:gpt-5.5","latencia_ms":3140,"tokens_entrada":1180,"tokens_saida":64,"custo_estimado":"0.002100","ferramentas":["web_search","calcular"],"erro":null},"handoff":{"motivo":"contato pediu uma pessoa","resumo":"Quer falar com alguém.","codigo":"K7M2QX"}}' ;;
    "POST /admin/clientes/c1/agentes/a3/canal") API_STATUS=200; API_RESPOSTA='{"id":"a3","cliente_id":"c1","nome":"Ana","canal":"chatwoot","buffer_segundos":2,"digitacao_maximo_segundos":1}'; echo "$3" >"$DIR/conectado" ;;
    "PATCH /admin/clientes/c1/agentes/a3") API_STATUS=200; API_RESPOSTA=$(jq -c --argjson m "$3" '. + $m' <<<'{"id":"a3","cliente_id":"c1","nome":"Ana","canal":"chatwoot"}') ;;
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
# Menu: criar agente nativo e conversar, conversar sem agente nativo, editar buffer, ferramentas e modelo do resumo, remover agente e empresa, consumo, esquecer token, sair.
menu_operador
jq -c . "$DIR/criado_nativo"
# Conectar o nativo criado ao Chatwoot pela ficha de edição.
AGENTE='{"id":"a3","cliente_id":"c1","nome":"Ana","canal":"nativo","buffer_segundos":2,"digitacao_maximo_segundos":1}'
com_voltar conecta_canal
printf '%s\n' "$RESULTADO"
jq -c . "$DIR/conectado"
jq -c . <<<"$AGENTE"
# Agente no WhatsApp: cria, pareia pelo QR code, escolhe o grupo do handoff e troca o destino depois.
EMPRESA_ID=c1 EMPRESA_NOME="Loja Exemplo"
com_voltar fluxo_agente_waha
jq -c . "$DIR/criado_waha"
AGENTE='{"id":"a4","cliente_id":"c1","nome":"Carlos","canal":"waha","handoff_destino":{"tipo":"grupo","chat_id":"120363111@g.us","nome":"Atendimento Loja Exemplo"},"retomada_automatica_horas":4}'
com_voltar edita_waha
jq -c . "$DIR/patch_waha"
# Atualização da WAHA: tag nova no Docker Hub, troca a versão e registra.
env_set WAHA_ATIVA 1
env_set VERSAO_WAHA gows-2026.8.2
com_voltar fluxo_waha
printf 'VERSAO_WAHA=%s\n' "$(env_get VERSAO_WAHA)"
