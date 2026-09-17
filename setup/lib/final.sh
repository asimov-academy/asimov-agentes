#!/usr/bin/env bash
# shellcheck disable=SC2034  # PASSO_ATUAL e PASSO_TOTAL são lidas por passo(), em estado.sh
# Tela 7: AGENTS.md e CLAUDE.md do projeto, primeiro commit e resumo.

gera_arquivos_de_contexto() {
  if [ -d "$RAIZ_PROJETO/spec" ]; then
    # Repositório de desenvolvimento da plataforma: os arquivos dele não podem ser trocados.
    echo "pasta spec/ encontrada; AGENTS.md e CLAUDE.md de desenvolvimento preservados"
    return 0
  fi
  local agente_codigo modelos
  agente_codigo=$([ "$(env_get AGENTE_CODIGO)" = codex ] && echo Codex || echo "Claude Code")
  modelos="resposta $(env_get MODELO_CONVERSA), fallback $(env_get MODELO_FALLBACK || true), visão $(env_get MODELO_VISAO), áudio $(env_get MODELO_TRANSCRICAO)"

  sed -e "s|{{AGENTE_CODIGO}}|$agente_codigo|g" \
    -e "s|{{MODELOS}}|$modelos|g" \
    -e "s|{{MODO}}|$(env_get MODO_INSTALACAO)|g" \
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

instala_comando() {
  $SUDO ln -sf "$RAIZ_PROJETO/setup/asimov.sh" /usr/local/bin/asimov
}

mostra_resumo() {
  local sub comando fallback
  sub=$(env_get SUBDOMINIO_BOT)
  fallback=$(env_get MODELO_FALLBACK)
  comando=$([ "$(env_get AGENTE_CODIGO)" = codex ] && echo codex || echo claude)

  secao "Pronto"
  if [ "$(estado_get agente_canal)" = nativo ]; then
    ok "Agente $(destaque "$(estado_get agente_nome)") criado para conversar no terminal ${CINZA}· $(estado_get agente_conta)${NORMAL}"
    echo
  elif [ -n "$(estado_get agente_id)" ]; then
    ok "$(destaque "$(estado_get agente_nome)") no ar na caixa $(destaque "$(estado_get agente_caixa)") ${CINZA}· $(estado_get agente_conta)${NORMAL}"
    echo
  fi
  campo "Versão" "$VERSAO"
  campo "Plataforma" "https://$sub/health"
  campo "Projeto" "$RAIZ_PROJETO"
  campo "Uso" "$([ "$(env_get MODO_INSTALACAO)" = revenda ] && echo 'revenda para empresas clientes' || echo 'só a minha empresa')"
  campo "Resposta" "$(env_get MODELO_CONVERSA)${fallback:+ ${CINZA}→ $fallback${NORMAL}}"
  campo "Visão" "$(env_get MODELO_VISAO)"
  campo "Áudio" "$(env_get MODELO_TRANSCRICAO)"
  echo
  aviso "Guarde uma cópia do .env fora da VPS: sem ele as credenciais dos canais não abrem."
  echo
  printf '  %sComandos%s\n' "$NEGRITO" "$NORMAL"
  printf '    %sasimov%s               %smenu: criar, editar e remover agentes, ver consumo%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov novo-agente%s   %soutro agente, para empresa nova ou existente%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov conversar%s     %sconversa com um agente nativo aqui no terminal%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov ajuda%s         %stodos os comandos%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %scd %s && %s%s   %sevoluir em vibecoding%s\n' "$CIANO" "$RAIZ_PROJETO" "$comando" "$NORMAL" "$CINZA" "$NORMAL"
  echo
}

tela_final() {
  if ! estado_tem instalacao_concluida; then
    secao "Finalizando"
    PASSO_ATUAL=0
    PASSO_TOTAL=3
    passo contexto "AGENTS.md e CLAUDE.md do projeto" "Veja o log." --sem-repetir gera_arquivos_de_contexto
    passo comando "Comando asimov" "Veja o log." --sem-repetir instala_comando
    passo commit "Primeiro commit do projeto" "Veja o log." --sem-repetir primeiro_commit
    estado_set instalacao_concluida "$(date -Is)"
  fi
  mostra_resumo
}
