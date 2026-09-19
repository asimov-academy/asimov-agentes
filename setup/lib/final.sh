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
  agente_codigo=$(ia_nome)
  modelos="escolhidos por agente (asimov editar > Modelos, ou a ficha do agente no painel)"

  sed -e "s|{{AGENTE_CODIGO}}|$agente_codigo|g" \
    -e "s|{{MODELOS}}|$modelos|g" \
    -e "s|{{MODO}}|$(env_get MODO_INSTALACAO)|g" \
    -e "s|{{CANAIS}}|Chatwoot, WhatsApp oficial, WhatsApp pela WAHA e nativo (terminal)|g" \
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

# Painel ligado e ainda sem conta: o código de primeiro acesso aparece aqui, na última tela, que é
# a que fica no terminal. O mostrado ao ligar o painel some quando a tela seguinte limpa tudo.
resumo_acesso_ao_painel() {
  painel_ligado || return 0
  api GET /admin/painel
  [ "$API_STATUS" = 200 ] || return 0
  [ "$(jq -r '.tem_operador' <<<"$API_RESPOSTA" 2>/dev/null || echo true)" = false ] || return 0
  info "Primeiro acesso ao painel: abra o endereço e informe o código."
  painel_mostra_codigo || true
  if estado_tem primeiro_agente_no_painel && ! estado_tem agente_id; then
    dica "Depois de entrar, abra Agentes e clique em novo agente: o passo a passo começa ali."
    echo
  fi
}

mostra_resumo() {
  local sub
  sub=$(env_get SUBDOMINIO_BOT)

  secao "Pronto"
  if [ "$(estado_get agente_canal)" = nativo ]; then
    ok "Agente $(destaque "$(estado_get agente_nome)") criado para conversar no terminal ${CINZA}· $(estado_get agente_conta)${NORMAL}"
    echo
  elif [ "$(estado_get agente_canal)" = waha ]; then
    if [ -n "$(estado_get agente_caixa)" ]; then
      ok "$(destaque "$(estado_get agente_nome)") atende no WhatsApp $(destaque "$(estado_get agente_caixa)") ${CINZA}· $(estado_get agente_conta)${NORMAL}"
    else
      aviso "$(destaque "$(estado_get agente_nome)") criado, mas o número ainda não foi pareado: abra $(destaque asimov) > Editar agente > WhatsApp."
    fi
    echo
  elif [ -n "$(estado_get agente_id)" ]; then
    ok "$(destaque "$(estado_get agente_nome)") no ar na caixa $(destaque "$(estado_get agente_caixa)") ${CINZA}· $(estado_get agente_conta)${NORMAL}"
    echo
  fi
  campo "Versão" "$VERSAO"
  campo "Plataforma" "https://$sub/health"
  if painel_ligado; then
    campo "Painel" "$(painel_endereco)"
  fi
  if vinculo_ligado; then
    campo "Copiloto" "$(ia_nome)$([ -n "$(env_get IA_CONTA)" ] && printf ' · %s' "$(env_get IA_CONTA)")"
  fi
  campo "Projeto" "$RAIZ_PROJETO"
  campo "Uso" "$([ "$(env_get MODO_INSTALACAO)" = revenda ] && echo 'revenda para empresas clientes' || echo 'só a minha empresa')"
  echo
  resumo_acesso_ao_painel
  aviso "Guarde uma cópia do .env fora da VPS: sem ele as credenciais dos canais não abrem."
  echo
  printf '  %sComandos%s\n' "$NEGRITO" "$NORMAL"
  printf '    %sasimov%s               %smenu: criar, editar e remover agentes, ver consumo%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov novo-agente%s   %soutro agente, para empresa nova ou existente%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov conversar%s     %sconversa de teste com um agente aqui no terminal%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov painel%s        %s%s%s\n' "$CIANO" "$NORMAL" "$CINZA" \
    "$(painel_ligado && echo 'código de acesso ao painel no navegador' || echo 'administrar pelo navegador, em app.<domínio>')" "$NORMAL"
  printf '    %sasimov ia%s            %s%s%s\n' "$CIANO" "$NORMAL" "$CINZA" \
    "$(vinculo_ligado && echo 'trocar a conta de IA que move o copiloto do painel' || echo "entrar na conta de $(ia_nome) e ligar o copiloto do painel")" "$NORMAL"
  printf '    %sasimov ajuda%s         %stodos os comandos%s\n' "$CIANO" "$NORMAL" "$CINZA" "$NORMAL"
  printf '    %sasimov evoluir%s       %sabre o %s na pasta do projeto, para evoluir em vibecoding%s\n' \
    "$CIANO" "$NORMAL" "$CINZA" "$(ia_nome)" "$NORMAL"
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
