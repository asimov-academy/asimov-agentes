#!/usr/bin/env bash
# shellcheck disable=SC2034  # PASSO_ATUAL e PASSO_TOTAL são lidas por passo(), em estado.sh
# Tela 7: AGENTS.md e CLAUDE.md do projeto, primeiro commit e resumo.

gera_arquivos_de_contexto() {
  if [ -d "$RAIZ_PROJETO/spec" ]; then
    # Repositório de desenvolvimento da plataforma: os arquivos dele não podem ser trocados.
    echo "pasta spec/ encontrada; AGENTS.md e CLAUDE.md de desenvolvimento preservados"
    return 0
  fi
  local agente_codigo provedor
  agente_codigo=$([ "$(env_get AGENTE_CODIGO)" = codex ] && echo Codex || echo "Claude Code")
  provedor="$(env_get PROVEDOR_IA)"
  [ -n "$(env_get PROVEDOR_APOIO)" ] && provedor="$provedor (apoio: $(env_get PROVEDOR_APOIO))"

  sed -e "s|{{AGENTE_CODIGO}}|$agente_codigo|g" \
    -e "s|{{PROVEDOR_IA}}|$provedor|g" \
    -e "s|{{CANAIS}}|Chatwoot|g" \
    -e "s|{{CAMINHO_LOG}}|$LOG|g" \
    "$RAIZ_PROJETO/modelos/AGENTS.md.tmpl" >"$RAIZ_PROJETO/AGENTS.md"
  printf '@AGENTS.md\n' >"$RAIZ_PROJETO/CLAUDE.md"
}

primeiro_commit() {
  cd "$RAIZ_PROJETO" || return 1
  [ -d .git ] || git init -b main
  git add -A
  git diff --cached --quiet && return 0
  git -c user.name="${GIT_AUTHOR_NAME:-Operador}" -c user.email="${GIT_AUTHOR_EMAIL:-operador@localhost}" \
    commit -m "Instalação inicial pelo setup Asimov Academy $VERSAO"
}

mostra_resumo() {
  local sub comando
  sub=$(env_get SUBDOMINIO_BOT)
  comando=$([ "$(env_get AGENTE_CODIGO)" = codex ] && echo codex || echo claude)

  titulo "Instalação concluída"
  info "Plataforma:        https://$sub/health"
  local apoio
  apoio=$(env_get PROVEDOR_APOIO)
  info "Provedor de IA:    $(env_get PROVEDOR_IA)${apoio:+ (apoio: $apoio)}"
  info "Projeto:           $RAIZ_PROJETO"
  info "Log do setup:      $LOG"
  echo
  if [ -n "$(estado_get agente_id)" ]; then
    info "Agente:            $(estado_get agente_nome) ($(estado_get cliente_nome), Chatwoot)"
    info "Caixa de entrada:  $(estado_get agente_caixa) (bot criado e ligado no Chatwoot)"
    info "Prompt do agente:  prompts/ (edite e a mudança vale na próxima mensagem)"
    echo
  fi
  aviso "Guarde uma cópia do arquivo .env fora da VPS. Sem a CHAVE_CRIPTOGRAFIA dele,"
  aviso "as credenciais dos canais gravadas no banco não podem ser lidas."
  echo
  printf '  %sPróximos passos%s\n' "$NEGRITO" "$NORMAL"
  info "1. Mande uma mensagem na caixa de entrada do Chatwoot e veja o agente responder."
  info "2. cd $RAIZ_PROJETO && $comando"
  info "3. Depois de mudar o projeto: ./deploy/publicar.sh"
  echo
}

tela_final() {
  if ! estado_tem instalacao_concluida; then
    titulo "Finalizando"
    PASSO_ATUAL=0
    PASSO_TOTAL=2
    passo contexto "Gerando AGENTS.md e CLAUDE.md do projeto" "veja o log" --sem-repetir gera_arquivos_de_contexto
    passo commit "Criando o primeiro commit do projeto" "veja o log" --sem-repetir primeiro_commit
    estado_set instalacao_concluida "$(date -Is)"
  fi
  mostra_resumo
}
