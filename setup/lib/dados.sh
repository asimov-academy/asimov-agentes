#!/usr/bin/env bash
# Telas de dados: modo da instalação, configuração e modelos de IA por função.
# Respostas comuns vão para o estado; chaves e modelos, para o .env.

# consulta_provedor provedor chave [opções do curl]: GET na lista de modelos do provedor.
# A chave vai por stdin (-H @-) para não aparecer na lista de processos.
consulta_provedor() {
  local provedor=$1 chave=$2
  shift 2
  case "$provedor" in
    openai) printf 'Authorization: Bearer %s\n' "$chave" |
      curl -s --max-time 20 -H @- "$@" https://api.openai.com/v1/models || true ;;
    groq) printf 'Authorization: Bearer %s\n' "$chave" |
      curl -s --max-time 20 -H @- "$@" https://api.groq.com/openai/v1/models || true ;;
    anthropic) printf 'x-api-key: %s\nanthropic-version: 2023-06-01\n' "$chave" |
      curl -s --max-time 20 -H @- "$@" 'https://api.anthropic.com/v1/models?limit=100' || true ;;
    gemini) printf 'x-goog-api-key: %s\n' "$chave" |
      curl -s --max-time 20 -H @- "$@" 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000' || true ;;
  esac
}

# testa_chave provedor chave -> 0 quando o provedor aceita a chave.
testa_chave() {
  [ "$(consulta_provedor "$1" "$2" -o /dev/null -w '%{http_code}')" = "200" ]
}

variavel_da_chave() {
  case "$1" in
    openai) echo OPENAI_API_KEY ;;
    anthropic) echo ANTHROPIC_API_KEY ;;
    gemini) echo GEMINI_API_KEY ;;
    groq) echo GROQ_API_KEY ;;
  esac
}

nome_bonito() {
  case "$1" in
    openai) echo OpenAI ;;
    anthropic) echo Anthropic ;;
    gemini) echo Gemini ;;
    groq) echo Groq ;;
  esac
}

pede_chave() {
  local provedor=$1 chave variavel
  variavel=$(variavel_da_chave "$provedor")
  if [ -n "$(env_get "$variavel")" ] && testa_chave "$provedor" "$(env_get "$variavel")"; then
    return 0
  fi
  while true; do
    pergunta_secreta chave "Chave de API da $(nome_bonito "$provedor")"
    printf '  %sTestando…%s' "$CINZA" "$NORMAL"
    if testa_chave "$provedor" "$chave"; then
      printf '\r\033[K'
      ok "Chave da $(nome_bonito "$provedor") válida"
      env_set "$variavel" "$chave"
      return 0
    fi
    printf '\r\033[K'
    falha "Chave recusada. Confira se copiou inteira e se a conta tem crédito."
  done
}

# Sugestões aparecem primeiro, mas só se o provedor ainda listar o modelo.
preferidos() {
  case "$1:$2" in
    openai:conversa) echo "gpt-5.5 gpt-5.1 gpt-5 gpt-4.1" ;;
    openai:visao) echo "gpt-5-mini gpt-5.1 gpt-4.1-mini" ;;
    openai:transcricao) echo "gpt-4o-transcribe whisper-1 gpt-4o-mini-transcribe" ;;
    anthropic:*) echo "claude-sonnet-5 claude-opus-5 claude-haiku-4-5" ;;
    gemini:conversa) echo "gemini-2.5-pro gemini-2.5-flash" ;;
    gemini:*) echo "gemini-2.5-flash gemini-2.5-pro" ;;
    groq:conversa) echo "llama-3.3-70b-versatile openai/gpt-oss-120b moonshotai/kimi-k2-instruct" ;;
    groq:visao) echo "meta-llama/llama-4-scout-17b-16e-instruct meta-llama/llama-4-maverick-17b-128e-instruct" ;;
    groq:transcricao) echo "whisper-large-v3-turbo whisper-large-v3" ;;
  esac
}

# filtra_modelos provedor função < ids: só o que serve para a função, sugeridos primeiro, até 8.
filtra_modelos() {
  local provedor=$1 funcao=$2 ids preferido
  ids=$(cat)
  if [ "$funcao" = transcricao ] && [ "$provedor" != gemini ]; then
    ids=$(grep -E 'whisper|transcribe' <<<"$ids" || true)
  else
    ids=$(grep -v -E 'whisper|transcribe|tts|audio|realtime|embed|image|dall-e|moderation|guard|search|babbage|davinci|sora|codex|computer|preview|exp' <<<"$ids" || true)
    if [ "$provedor" = openai ]; then
      ids=$(grep -E '^(gpt-|o[0-9])' <<<"$ids" || true)
    fi
  fi
  {
    for preferido in $(preferidos "$provedor" "$funcao"); do
      grep -x -F "$preferido" <<<"$ids" || true
    done
    sort -r <<<"$ids"
  } | awk 'NF && !visto[$0]++' | head -8
}

# lista_modelos provedor função: ids direto da API do provedor, já filtrados.
lista_modelos() {
  local provedor=$1 funcao=$2 json
  json=$(consulta_provedor "$provedor" "$(env_get "$(variavel_da_chave "$provedor")")")
  if [ "$provedor" = gemini ]; then
    jq -r '.models[]? | select(.supportedGenerationMethods | index("generateContent")) | .name | sub("^models/"; "")' <<<"$json" 2>/dev/null |
      { grep '^gemini' || true; } | filtra_modelos "$provedor" "$funcao"
  else
    jq -r '.data[]?.id' <<<"$json" 2>/dev/null | filtra_modelos "$provedor" "$funcao"
  fi
}

# escolhe_modelo VAR_ENV "rótulo" função [opcional]
escolhe_modelo() {
  local var=$1 rotulo=$2 funcao=$3 opcional=${4:-} op i provedor modelo linha
  local -a provedores nomes modelos
  if [ "$funcao" = transcricao ]; then
    provedores=(openai groq gemini)
  else
    provedores=(openai anthropic gemini groq)
  fi
  nomes=()
  [ -n "$opcional" ] && nomes+=("Sem fallback")
  for provedor in "${provedores[@]}"; do nomes+=("$(nome_bonito "$provedor")"); done

  echo
  escolha op "$rotulo" "${nomes[@]}"
  if [ -n "$opcional" ]; then
    if [ "$op" = 1 ]; then
      env_set "$var" ""
      return 0
    fi
    op=$((op - 1))
  fi
  provedor=${provedores[$((op - 1))]}
  pede_chave "$provedor"

  modelos=()
  while IFS= read -r linha; do modelos+=("$linha"); done < <(lista_modelos "$provedor" "$funcao")
  if [ "${#modelos[@]}" -eq 0 ]; then
    dica "Não consegui listar os modelos da $(nome_bonito "$provedor"); digite o nome."
    pergunta modelo "Modelo"
  else
    escolha i "Modelo" "${modelos[@]}" "${CINZA}outro (digitar)${NORMAL}"
    if [ "$i" -gt "${#modelos[@]}" ]; then
      pergunta modelo "Nome do modelo"
    else
      modelo=${modelos[$((i - 1))]}
    fi
  fi
  env_set "$var" "$provedor:$modelo"
}

valida_dominio() {
  [[ "$1" =~ ^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$ ]]
}

tela_modo() {
  [ -n "$(env_get MODO_INSTALACAO)" ] && return 0
  secao "Uso"
  local op
  escolha op "Para quem são os agentes?" \
    "Só para a minha empresa" \
    "Para empresas clientes  ${CINZA}revenda: cada empresa com seus agentes${NORMAL}"
  env_set MODO_INSTALACAO "$([ "$op" = 1 ] && echo empresa || echo revenda)"
}

tela_modelos() {
  [ -n "$(env_get MODELO_CONVERSA)" ] && estado_tem modelos_confirmados && return 0
  secao "Modelos de IA"
  dica "Cada função pode usar um provedor diferente. A chave de cada provedor é pedida uma vez."
  local fallback
  while true; do
    escolhe_modelo MODELO_CONVERSA "Resposta ao contato" conversa
    escolhe_modelo MODELO_FALLBACK "Fallback, se a resposta falhar" conversa opcional
    escolhe_modelo MODELO_VISAO "Visão (imagens e PDF)" visao
    escolhe_modelo MODELO_TRANSCRICAO "Transcrição de áudio" transcricao

    fallback=$(env_get MODELO_FALLBACK)
    echo
    campo "Resposta" "$(env_get MODELO_CONVERSA)"
    campo "Fallback" "${fallback:-nenhum}"
    campo "Visão" "$(env_get MODELO_VISAO)"
    campo "Áudio" "$(env_get MODELO_TRANSCRICAO)"
    echo
    confirma "Modelos certos?" && break
  done

  local provedores variavel
  provedores=$(for variavel in MODELO_CONVERSA MODELO_FALLBACK MODELO_VISAO MODELO_TRANSCRICAO; do
    env_get "$variavel" | cut -d: -f1
    echo
  done | awk 'NF && !visto[$0]++' | xargs)
  env_set PROVEDORES "$provedores"
  estado_set modelos_confirmados "$(date -Is)"
}

tela_dados() {
  estado_tem dados_confirmados && return 0
  secao "Configuração"

  local dominio email opcao
  dica "Os webhooks dos agentes ficam em bot.<domínio>."
  while true; do
    pergunta dominio "Domínio" "$(estado_get dominio)"
    dominio=${dominio#http://}
    dominio=${dominio#https://}
    dominio=${dominio%%/*}
    dominio=${dominio#bot.}
    valida_dominio "$dominio" && break
    falha "Domínio inválido. Ex: minhaempresa.com.br"
  done
  while true; do
    pergunta email "E-mail para o SSL" "$(estado_get email)"
    [[ "$email" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]] && break
    falha "E-mail inválido."
  done
  echo
  escolha opcao "Agente de código" "Claude Code" "Codex"

  estado_set dominio "$dominio"
  estado_set email "$email"
  env_set DOMINIO_BASE "$dominio"
  env_set SUBDOMINIO_BOT "bot.$dominio"
  env_set EMAIL_SSL "$email"
  env_set AGENTE_CODIGO "$([ "$opcao" = 1 ] && echo claude_code || echo codex)"
  estado_set dados_confirmados "$(date -Is)"
}
