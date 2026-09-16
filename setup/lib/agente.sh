#!/usr/bin/env bash
# Tela 6: primeiro agente. Tudo passa pela API; o setup nunca toca no banco.

API_LOCAL="http://127.0.0.1:8000"

# api MÉTODO CAMINHO [JSON]: grava o status HTTP em API_STATUS e o corpo em API_RESPOSTA.
# Não chame dentro de $(...): as variáveis se perderiam na subshell.
api() {
  local metodo=$1 caminho=$2 corpo=${3:-} saida
  local dados=()
  [ -n "$corpo" ] && dados=(--data "$corpo")
  saida=$(mktemp)
  API_STATUS=$(printf 'X-Admin-Key: %s\n' "$(env_get CHAVE_API_ADMIN)" |
    curl -s -o "$saida" -w '%{http_code}' -X "$metodo" -H @- \
      -H 'Content-Type: application/json' "${dados[@]}" "$API_LOCAL$caminho" || true)
  API_RESPOSTA=$(cat "$saida")
  rm -f "$saida"
}

detalhe_erro() {
  if [ "$API_STATUS" = "000" ] || [ -z "$1" ]; then
    echo "a API não respondeu em $API_LOCAL. Veja: source deploy/compose.sh && dc logs api"
    return 0
  fi
  jq -r '.detail | if type == "string" then . else (map(.msg) | join("; ")) end' 2>/dev/null <<<"$1" || echo "$1"
}

cria_cliente() {
  local nome corpo
  if [ -n "$(estado_get cliente_id)" ]; then
    return 0
  fi
  while true; do
    pergunta nome "Nome do cliente (a empresa atendida por este agente)"
    corpo=$(jq -n --arg nome "$nome" '{nome: $nome}')
    api POST /admin/clientes "$corpo"
    if [ "$API_STATUS" = 201 ]; then
      estado_set cliente_id "$(jq -r .id <<<"$API_RESPOSTA")"
      estado_set cliente_nome "$nome"
      return 0
    fi
    info "Não deu certo: $(detalhe_erro "$API_RESPOSTA")"
  done
}

cria_agente() {
  local nome url conta inboxes token segredo handoff corpo inbox_json handoff_json
  local sub
  sub=$(env_get SUBDOMINIO_BOT)

  echo
  info "Canal: Chatwoot. WhatsApp oficial e Telegram diretos chegam numa próxima versão."
  echo
  info "Antes de continuar, no Chatwoot:"
  info "  1. Configurações > Bots > Adicionar bot."
  info "     Em URL do webhook, coloque https://$sub/aguardando (vamos trocar no fim)."
  info "  2. Copie o secret que o Chatwoot mostra ao criar o bot."
  info "  3. Perfil > Token de acesso: copie o token do seu usuário."
  echo

  pergunta nome "Nome do agente" "$(estado_get agente_nome)"
  while true; do
    pergunta url "URL do Chatwoot (ex: https://chat.minhaempresa.com.br)" "$(estado_get chatwoot_url)"
    url=${url%/}
    pergunta conta "ID da conta no Chatwoot (número na URL: /app/accounts/NÚMERO)" "$(estado_get chatwoot_conta)"
    pergunta inboxes "ID das caixas de entrada que o agente atende, separados por vírgula" "$(estado_get chatwoot_inboxes)"
    pergunta_secreta token "Token de acesso do usuário do Chatwoot"
    pergunta_secreta segredo "Secret do bot do Chatwoot"
    pergunta_opcional handoff "ID do usuário do Chatwoot que recebe as conversas transferidas"

    estado_set agente_nome "$nome"
    estado_set chatwoot_url "$url"
    estado_set chatwoot_conta "$conta"
    estado_set chatwoot_inboxes "$inboxes"

    if ! [[ "$conta" =~ ^[0-9]+$ ]] || ! [[ "$inboxes" =~ ^[0-9]+([[:space:]]*,[[:space:]]*[0-9]+)*$ ]]; then
      info "A conta e as caixas de entrada precisam ser números."
      continue
    fi
    if [ -n "$handoff" ] && ! [[ "$handoff" =~ ^[0-9]+$ ]]; then
      info "O ID do usuário de handoff precisa ser um número."
      continue
    fi

    inbox_json=$(tr -d ' ' <<<"$inboxes" | jq -Rc 'split(",") | map(tonumber)')
    handoff_json=$([ -n "$handoff" ] && jq -nc --argjson id "$handoff" '{tipo: "usuario", id: $id}' || echo null)
    corpo=$(jq -n \
      --arg nome "$nome" --arg url "$url" --argjson conta "$conta" --argjson inboxes "$inbox_json" \
      --arg token "$token" --arg segredo "$segredo" --argjson handoff "$handoff_json" \
      '{nome: $nome, canal: "chatwoot", handoff_destino: $handoff,
        credenciais: {url: $url, account_id: $conta, inbox_ids: $inboxes,
                      api_access_token: $token, bot_secret: $segredo}}')

    printf '  Testando as credenciais no Chatwoot...'
    api POST "/admin/clientes/$(estado_get cliente_id)/agentes" "$corpo"
    if [ "$API_STATUS" = 201 ]; then
      printf ' %sok%s\n' "$VERDE" "$NORMAL"
      estado_set agente_id "$(jq -r .id <<<"$API_RESPOSTA")"
      estado_set agente_webhook "$(jq -r .url_webhook <<<"$API_RESPOSTA")"
      return 0
    fi
    printf ' %sfalhou%s\n' "$VERMELHO" "$NORMAL"
    info "$(detalhe_erro "$API_RESPOSTA")"
    if [ "$API_STATUS" = 409 ]; then
      pergunta nome "Escolha outro nome para o agente"
    fi
    echo
  done
}

tela_primeiro_agente() {
  estado_tem agente_id && return 0
  titulo "Primeiro agente"
  cria_cliente
  cria_agente

  titulo "Ligue o agente no Chatwoot"
  info "1. Configurações > Bots > editar o bot que você criou."
  info "   Troque a URL do webhook por:"
  echo
  printf '     %s%s%s\n' "$NEGRITO" "$(estado_get agente_webhook)" "$NORMAL"
  echo
  info "2. Configurações > Caixas de entrada > a caixa do agente > Bot:"
  info "   selecione o bot e salve."
  echo
  printf 'Enter quando terminar: '
  IFS= read -r _ </dev/tty || true
}
