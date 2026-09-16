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

# escolhe_empresa "nome sugerido": define EMPRESA_ID e EMPRESA_NOME.
# Modo empresa: uma empresa só, criada no primeiro agente. Modo revenda: existente ou nova.
escolhe_empresa() {
  local sugerido=$1 op nome corpo id
  local -a ids nomes
  EMPRESA_ID="" EMPRESA_NOME=""

  api GET /admin/clientes
  ids=() nomes=()
  if [ "$API_STATUS" = 200 ]; then
    while IFS=$'\t' read -r id nome; do ids+=("$id"); nomes+=("$nome"); done \
      < <(jq -r '.[] | [.id, .nome] | @tsv' <<<"$API_RESPOSTA")
  fi

  if [ "$(env_get MODO_INSTALACAO)" = empresa ] && [ "${#ids[@]}" -gt 0 ]; then
    EMPRESA_ID=${ids[0]} EMPRESA_NOME=${nomes[0]}
    return 0
  fi

  if [ "$(env_get MODO_INSTALACAO)" = revenda ] && [ "${#ids[@]}" -gt 0 ]; then
    echo
    escolha op "Empresa" "${nomes[@]}" "${CIANO}+ nova empresa${NORMAL}"
    if [ "$op" -le "${#ids[@]}" ]; then
      EMPRESA_ID=${ids[$((op - 1))]} EMPRESA_NOME=${nomes[$((op - 1))]}
      return 0
    fi
  fi

  while true; do
    pergunta nome "$([ "$(env_get MODO_INSTALACAO)" = empresa ] && echo 'Nome da sua empresa' || echo 'Nome da empresa cliente')" "$sugerido"
    corpo=$(jq -n --arg nome "$nome" '{nome: $nome}')
    api POST /admin/clientes "$corpo"
    if [ "$API_STATUS" = 201 ]; then
      EMPRESA_ID=$(jq -r .id <<<"$API_RESPOSTA") EMPRESA_NOME=$nome
      return 0
    fi
    falha "$(detalhe_erro "$API_RESPOSTA")"
    sugerido=""
  done
}

# Preenche CHATWOOT_URL, CHATWOOT_TOKEN e CHATWOOT_CONTAS (JSON devolvido pela API).
acessa_chatwoot() {
  local corpo
  dica "Token: no Chatwoot, avatar > Configurações do perfil > Token de acesso (administrador)."
  while true; do
    pergunta CHATWOOT_URL "URL do Chatwoot" "$(estado_get chatwoot_url)"
    CHATWOOT_URL=${CHATWOOT_URL%%/app*}
    CHATWOOT_URL=${CHATWOOT_URL%/}
    pergunta_secreta CHATWOOT_TOKEN "Token de acesso"
    printf '  %sConectando…%s' "$CINZA" "$NORMAL"
    corpo=$(jq -n --arg url "$CHATWOOT_URL" --arg token "$CHATWOOT_TOKEN" '{conexao: {url: $url, token_admin: $token}}')
    api POST /admin/canais/chatwoot/descobrir "$corpo"
    printf '\r\033[K'
    if [ "$API_STATUS" = 200 ]; then
      estado_set chatwoot_url "$CHATWOOT_URL"
      CHATWOOT_CONTAS=$API_RESPOSTA
      return 0
    fi
    falha "$(detalhe_erro "$API_RESPOSTA")"
  done
}

# escolha_da_lista VAR "texto" JSON_ARRAY_DE_NOMES -> índice (0..n-1). Uma opção só: escolhe sozinho.
escolha_da_lista() {
  local __var=$1 texto=$2 lista=$3 numero linha
  local -a nomes=()
  while IFS= read -r linha; do nomes+=("$linha"); done < <(jq -r '.[]' <<<"$lista")
  if [ "${#nomes[@]}" -eq 1 ]; then
    ok "$texto: $(destaque "${nomes[0]}")"
    printf -v "$__var" '%s' 0
    return 0
  fi
  echo
  escolha numero "$texto" "${nomes[@]}"
  printf -v "$__var" '%s' "$((numero - 1))"
}

# Chatwoot → conta → caixa → nome → empresa → cria. Define AGENTE_* para quem chamou.
fluxo_novo_agente() {
  local conta_i caixa_i conta_id conta_nome caixa_id caixas nome corpo
  acessa_chatwoot

  escolha_da_lista conta_i "Conta do Chatwoot" "$(jq -c '[.contas[].nome]' <<<"$CHATWOOT_CONTAS")"
  conta_id=$(jq -r ".contas[$conta_i].id" <<<"$CHATWOOT_CONTAS")
  conta_nome=$(jq -r ".contas[$conta_i].nome" <<<"$CHATWOOT_CONTAS")
  caixas=$(jq -c ".contas[$conta_i].caixas" <<<"$CHATWOOT_CONTAS")
  if [ "$(jq 'length' <<<"$caixas")" -eq 0 ]; then
    erro_fatal "A conta $conta_nome não tem caixa de entrada" "Crie a caixa no Chatwoot e rode o comando de novo."
  fi
  escolha_da_lista caixa_i "Caixa de entrada" "$(jq -c '[.[].nome]' <<<"$caixas")"
  caixa_id=$(jq -r ".[$caixa_i].id" <<<"$caixas")
  AGENTE_CAIXA=$(jq -r ".[$caixa_i].nome" <<<"$caixas")

  echo
  pergunta nome "Nome do agente"
  escolhe_empresa "$conta_nome"

  while true; do
    corpo=$(jq -n --arg nome "$nome" --arg url "$CHATWOOT_URL" --arg token "$CHATWOOT_TOKEN" \
      --argjson conta "$conta_id" --argjson caixa "$caixa_id" \
      '{nome: $nome, canal: "chatwoot",
        conexao: {url: $url, token_admin: $token, account_id: $conta, inbox_ids: [$caixa]}}')
    printf '  %sCriando o bot no Chatwoot…%s' "$CINZA" "$NORMAL"
    api POST "/admin/clientes/$EMPRESA_ID/agentes" "$corpo"
    printf '\r\033[K'
    if [ "$API_STATUS" = 201 ]; then
      AGENTE_NOME=$nome
      AGENTE_ID=$(jq -r .id <<<"$API_RESPOSTA")
      ok "$(destaque "$nome") no ar na caixa $(destaque "$AGENTE_CAIXA") ${CINZA}· $EMPRESA_NOME${NORMAL}"
      unset CHATWOOT_TOKEN
      return 0
    fi
    falha "$(detalhe_erro "$API_RESPOSTA")"
    if [ "$API_STATUS" = 409 ]; then
      pergunta nome "Outro nome para o agente"
    elif [ "$API_STATUS" = 422 ]; then
      fluxo_novo_agente
      return 0
    else
      erro_fatal "Não consegui criar o agente" "Rode o comando de novo."
    fi
  done
}

tela_primeiro_agente() {
  estado_tem agente_id && return 0
  secao "Agente no Chatwoot"
  fluxo_novo_agente
  estado_set agente_nome "$AGENTE_NOME"
  estado_set agente_caixa "$AGENTE_CAIXA"
  estado_set agente_conta "$EMPRESA_NOME"
  estado_set agente_id "$AGENTE_ID"
}

lista_agentes() {
  local clientes
  api GET /admin/clientes
  [ "$API_STATUS" = 200 ] || erro_fatal "A API não respondeu" "Veja: source deploy/compose.sh && dc logs api"
  clientes=$API_RESPOSTA
  api GET /admin/agentes
  [ "$API_STATUS" = 200 ] || erro_fatal "A API não respondeu" "Veja: source deploy/compose.sh && dc logs api"
  secao "Agentes"
  if [ "$(jq 'length' <<<"$API_RESPOSTA")" -eq 0 ]; then
    dica "Nenhum agente ainda. Crie com: asimov novo-agente"
    return 0
  fi
  jq -r --argjson clientes "$clientes" '
    ($clientes | map({(.id): .nome}) | add) as $nomes
    | group_by(.cliente_id)[]
    | "\($nomes[.[0].cliente_id] // "?")\t" + (map("\(.nome)|\(.canal)|\(.modelo_conversa)") | join("\t"))
  ' <<<"$API_RESPOSTA" | while IFS=$'\t' read -r empresa resto; do
    printf '  %s%s%s\n' "$NEGRITO" "$empresa" "$NORMAL"
    tr '\t' '\n' <<<"$resto" | while IFS='|' read -r nome canal modelo; do
      printf '    %s✓%s %-16s %s%s · %s%s\n' "$VERDE" "$NORMAL" "$nome" "$CINZA" "$canal" "$modelo" "$NORMAL"
    done
  done
  echo
}
