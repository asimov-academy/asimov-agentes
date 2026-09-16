#!/usr/bin/env bash
# Tela 3: dados da instalação. Respostas comuns vão para o estado; chaves, para o .env.

NOMES_PROVEDOR=([1]=openai [2]=anthropic [3]=gemini)

# testa_chave provedor chave -> 0 quando o provedor aceita a chave.
# A chave vai por stdin (-H @-) para não aparecer na lista de processos.
testa_chave() {
  local provedor=$1 chave=$2 codigo
  case "$provedor" in
    openai)
      codigo=$(printf 'Authorization: Bearer %s\n' "$chave" |
        curl -s -o /dev/null -w '%{http_code}' -H @- https://api.openai.com/v1/models || true)
      ;;
    anthropic)
      codigo=$(printf 'x-api-key: %s\nanthropic-version: 2023-06-01\n' "$chave" |
        curl -s -o /dev/null -w '%{http_code}' -H @- https://api.anthropic.com/v1/models || true)
      ;;
    gemini)
      codigo=$(printf 'x-goog-api-key: %s\n' "$chave" |
        curl -s -o /dev/null -w '%{http_code}' -H @- https://generativelanguage.googleapis.com/v1beta/models || true)
      ;;
  esac
  [ "$codigo" = "200" ]
}

variavel_da_chave() {
  case "$1" in
    openai) echo OPENAI_API_KEY ;;
    anthropic) echo ANTHROPIC_API_KEY ;;
    gemini) echo GEMINI_API_KEY ;;
  esac
}

pede_chave() {
  local provedor=$1 chave variavel
  variavel=$(variavel_da_chave "$provedor")
  if [ -n "$(env_get "$variavel")" ] && testa_chave "$provedor" "$(env_get "$variavel")"; then
    info "Chave de $provedor já gravada e válida."
    return 0
  fi
  while true; do
    pergunta_secreta chave "Cole a chave de API de $provedor"
    printf '  Testando a chave...'
    if testa_chave "$provedor" "$chave"; then
      printf ' %sválida%s\n' "$VERDE" "$NORMAL"
      env_set "$variavel" "$chave"
      return 0
    fi
    printf ' %srecusada%s\n' "$VERMELHO" "$NORMAL"
    info "Confira se copiou a chave inteira e se a conta tem crédito ativo."
  done
}

valida_dominio() {
  [[ "$1" =~ ^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$ ]]
}

tela_dados() {
  estado_tem dados_confirmados && return 0
  titulo "Dados da instalação"

  local dominio email opcao provedor apoio="" agente_codigo
  while true; do
    pergunta dominio "Domínio base (o setup usa bot.<domínio>, ex: minhaempresa.com.br)" "$(estado_get dominio)"
    dominio=${dominio#bot.}
    valida_dominio "$dominio" && break
    info "Domínio inválido. Digite só o domínio, sem https:// e sem barra."
  done
  while true; do
    pergunta email "E-mail para o certificado SSL" "$(estado_get email)"
    [[ "$email" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]] && break
    info "E-mail inválido."
  done
  echo
  escolha opcao "Qual agente de código você vai usar para evoluir o projeto?" "Claude Code" "Codex"
  agente_codigo=$([ "$opcao" = 1 ] && echo claude_code || echo codex)
  echo
  escolha opcao "Qual provedor de IA os agentes vão usar?" \
    "OpenAI (conversa, visão, áudio e embeddings)" \
    "Anthropic (conversa e visão; pede OpenAI ou Gemini para áudio e embeddings)" \
    "Gemini (conversa, visão, áudio e embeddings)"
  provedor=${NOMES_PROVEDOR[$opcao]}
  if [ "$provedor" = anthropic ]; then
    echo
    escolha opcao "Qual provedor cuida de áudio e embeddings?" "OpenAI" "Gemini"
    apoio=$([ "$opcao" = 1 ] && echo openai || echo gemini)
  fi

  echo
  pede_chave "$provedor"
  [ -n "$apoio" ] && pede_chave "$apoio"

  titulo "Confira"
  info "Webhooks em:      https://bot.$dominio"
  info "E-mail do SSL:    $email"
  info "Agente de código: $([ "$agente_codigo" = claude_code ] && echo 'Claude Code' || echo Codex)"
  info "Provedor de IA:   $provedor${apoio:+ (apoio: $apoio)}"
  echo
  if ! confirma "Está tudo certo?"; then
    estado_set dominio "$dominio"
    estado_set email "$email"
    tela_dados
    return 0
  fi

  estado_set dominio "$dominio"
  estado_set email "$email"
  env_set DOMINIO_BASE "$dominio"
  env_set SUBDOMINIO_BOT "bot.$dominio"
  env_set EMAIL_SSL "$email"
  env_set AGENTE_CODIGO "$agente_codigo"
  env_set PROVEDOR_IA "$provedor"
  env_set PROVEDOR_APOIO "$apoio"
  env_set PROVEDORES "$(printf '%s %s' "$provedor" "$apoio" | xargs)"
  estado_set dados_confirmados "$(date -Is)"
}
