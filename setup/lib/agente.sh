#!/usr/bin/env bash
# Tela 6: primeiro agente. Tudo passa pela API; o setup nunca toca no banco.
# O token de administrador do Chatwoot só vive nesta tela: a API cria o bot e o descarta.

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

# Preenche CHATWOOT_URL, CHATWOOT_TOKEN e CHATWOOT_CONTAS (JSON devolvido pela API).
acessa_chatwoot() {
  local corpo
  echo
  info "Canal: Chatwoot. O setup cria o bot e liga na caixa de entrada para você."
  info "Precisa do token de um administrador: no Chatwoot, clique no seu avatar >"
  info "Configurações do perfil > Token de acesso."
  echo
  while true; do
    pergunta CHATWOOT_URL "URL do Chatwoot (ex: https://chat.minhaempresa.com.br)" "$(estado_get chatwoot_url)"
    CHATWOOT_URL=${CHATWOOT_URL%/}
    CHATWOOT_URL=${CHATWOOT_URL%%/app*}
    pergunta_secreta CHATWOOT_TOKEN "Token de acesso do administrador"
    corpo=$(jq -n --arg url "$CHATWOOT_URL" --arg token "$CHATWOOT_TOKEN" '{conexao: {url: $url, token_admin: $token}}')
    api POST /admin/canais/chatwoot/descobrir "$corpo"
    if [ "$API_STATUS" = 200 ]; then
      estado_set chatwoot_url "$CHATWOOT_URL"
      CHATWOOT_CONTAS=$API_RESPOSTA
      return 0
    fi
    info "Não deu certo: $(detalhe_erro "$API_RESPOSTA")"
    echo
  done
}

# escolha_da_lista VAR "texto" JSON_ARRAY_DE_NOMES -> índice (0..n-1)
escolha_da_lista() {
  local __var=$1 texto=$2 lista=$3 total numero
  local -a nomes
  mapfile -t nomes < <(jq -r '.[]' <<<"$lista")
  total=${#nomes[@]}
  if [ "$total" -eq 1 ]; then
    info "$texto: ${nomes[0]}"
    printf -v "$__var" '%s' 0
    return 0
  fi
  escolha numero "$texto" "${nomes[@]}"
  printf -v "$__var" '%s' "$((numero - 1))"
}

cria_agente() {
  local conta_i caixa_i conta_id caixa_id caixa_nome caixas nome corpo
  acessa_chatwoot

  echo
  escolha_da_lista conta_i "Conta do Chatwoot" "$(jq -c '[.contas[].nome]' <<<"$CHATWOOT_CONTAS")"
  conta_id=$(jq -r ".contas[$conta_i].id" <<<"$CHATWOOT_CONTAS")
  caixas=$(jq -c ".contas[$conta_i].caixas" <<<"$CHATWOOT_CONTAS")
  if [ "$(jq 'length' <<<"$caixas")" -eq 0 ]; then
    erro_fatal "A conta escolhida não tem nenhuma caixa de entrada" \
      "crie a caixa de entrada no Chatwoot (ex: WhatsApp) e rode o mesmo comando de novo"
  fi
  echo
  escolha_da_lista caixa_i "Caixa de entrada que o agente vai atender" "$(jq -c '[.[].nome]' <<<"$caixas")"
  caixa_id=$(jq -r ".[$caixa_i].id" <<<"$caixas")
  caixa_nome=$(jq -r ".[$caixa_i].nome" <<<"$caixas")

  echo
  pergunta nome "Nome do agente (o nome que o contato vê)" "$(estado_get agente_nome)"
  while true; do
    corpo=$(jq -n --arg nome "$nome" --arg url "$CHATWOOT_URL" --arg token "$CHATWOOT_TOKEN" \
      --argjson conta "$conta_id" --argjson caixa "$caixa_id" \
      '{nome: $nome, canal: "chatwoot",
        conexao: {url: $url, token_admin: $token, account_id: $conta, inbox_ids: [$caixa]}}')
    printf '  Criando o bot no Chatwoot e ligando na caixa %s...' "$caixa_nome"
    api POST "/admin/clientes/$(estado_get cliente_id)/agentes" "$corpo"
    if [ "$API_STATUS" = 201 ]; then
      printf ' %sok%s\n' "$VERDE" "$NORMAL"
      estado_set agente_nome "$nome"
      estado_set agente_caixa "$caixa_nome"
      estado_set agente_id "$(jq -r .id <<<"$API_RESPOSTA")"
      estado_set agente_webhook "$(jq -r .url_webhook <<<"$API_RESPOSTA")"
      return 0
    fi
    printf ' %sfalhou%s\n' "$VERMELHO" "$NORMAL"
    info "$(detalhe_erro "$API_RESPOSTA")"
    if [ "$API_STATUS" = 409 ]; then
      pergunta nome "Escolha outro nome para o agente"
    elif [ "$API_STATUS" = 422 ]; then
      cria_agente
      return 0
    else
      erro_fatal "Não consegui criar o agente" "rode o mesmo comando de novo"
    fi
  done
}

tela_primeiro_agente() {
  estado_tem agente_id && return 0
  titulo "Primeiro agente"
  cria_cliente
  cria_agente
  unset CHATWOOT_TOKEN
}
