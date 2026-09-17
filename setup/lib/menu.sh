#!/usr/bin/env bash
# Tela 8: menu do operador. Editar, remover e ver consumo, sempre pela API.

# mostra_agente: resumo do AGENTE escolhido.
mostra_agente() {
  local fallback
  fallback=$(jq -r '.modelo_fallback // ""' <<<"$AGENTE")
  campo "Empresa" "$AGENTE_EMPRESA"
  campo "Canal" "$(jq -r '.canal' <<<"$AGENTE")"
  campo "Buffer" "$(jq -r '.buffer_segundos' <<<"$AGENTE") s"
  campo "Mensagens" "até $(jq -r '.max_mensagens_por_resposta' <<<"$AGENTE") por resposta"
  campo "Resposta" "$(jq -r '.modelo_conversa' <<<"$AGENTE")${fallback:+ ${CINZA}→ $fallback${NORMAL}}"
  campo "Resumo" "$(jq -r '.modelo_auxiliar' <<<"$AGENTE")"
  campo "Visão" "$(jq -r '.modelo_visao' <<<"$AGENTE")"
  campo "Áudio" "$(jq -r '.modelo_transcricao' <<<"$AGENTE")"
  campo "Handoff" "$(nome_do_destino "$(jq -c '.handoff_destino' <<<"$AGENTE")")"
}

# salva_agente JSON: PATCH só com os campos do JSON; atualiza AGENTE e deixa o RESULTADO para a
# tela redesenhada mostrar.
salva_agente() {
  api_com_token PATCH "$(caminho_do_agente "$AGENTE")" "$1" "Salvando…"
  if [ "$API_STATUS" = 200 ]; then
    AGENTE=$API_RESPOSTA
    RESULTADO=$(ok "Salvo. Vale a partir da próxima mensagem.")
  else
    RESULTADO=$(falha "$(detalhe_erro "$API_RESPOSTA")")
  fi
  devolve AGENTE RESULTADO
}

# escolhe_modelo_do_agente: pergunta a função e o modelo; define CORPO_MODELO para o PATCH.
# Só provedores com chave no .env: a plataforma não enxerga chave nova sem reconstruir.
escolhe_modelo_do_agente() {
  local op campo funcao rotulo opcional="" provedor
  local -a provedores=()
  for provedor in openai anthropic gemini groq; do
    [ -n "$(env_get "$(variavel_da_chave "$provedor")")" ] && provedores+=("$provedor")
  done
  echo
  escolha op "Qual modelo" \
    "Resposta ao contato  ${CINZA}$(jq -r '.modelo_conversa' <<<"$AGENTE")${NORMAL}" \
    "Fallback  ${CINZA}$(jq -r '.modelo_fallback // "nenhum"' <<<"$AGENTE")${NORMAL}" \
    "Resumo do handoff  ${CINZA}$(jq -r '.modelo_auxiliar' <<<"$AGENTE")${NORMAL}" \
    "Visão  ${CINZA}$(jq -r '.modelo_visao' <<<"$AGENTE")${NORMAL}" \
    "Áudio  ${CINZA}$(jq -r '.modelo_transcricao' <<<"$AGENTE")${NORMAL}"
  case "$op" in
    1) campo=modelo_conversa funcao=conversa rotulo="Resposta ao contato" ;;
    2) campo=modelo_fallback funcao=conversa rotulo="Fallback, se a resposta falhar" opcional=1 ;;
    3)
      campo=modelo_auxiliar funcao=auxiliar rotulo="Resumo do handoff"
      dica "Só resume a conversa para o atendente: um modelo mais barato costuma bastar."
      ;;
    4) campo=modelo_visao funcao=visao rotulo="Visão (imagens e PDF)" ;;
    *) campo=modelo_transcricao funcao=transcricao rotulo="Transcrição de áudio" ;;
  esac
  escolhe_modelo_em MODELO_ESCOLHIDO "$rotulo" "$funcao" "$opcional" "${provedores[@]}"
  CORPO_MODELO=$(jq -n --arg campo "$campo" --arg modelo "$MODELO_ESCOLHIDO" \
    '{($campo): (if $modelo == "" then null else $modelo end)}')
}

# Cada mudança roda em `com_voltar`: Esc no meio volta para a ficha sem salvar.
fluxo_editar_agente() {
  local op
  secao "Editar agente"
  if ! escolhe_agente; then
    pausa
    return 0
  fi
  RESULTADO=""
  while true; do
    secao "Editar $(jq -r '.nome' <<<"$AGENTE")"
    mostra_agente
    if [ -n "$RESULTADO" ]; then
      echo
      printf '%s\n' "$RESULTADO"
      RESULTADO=""
    fi
    echo
    ESC_ESCOLHE=6 escolha op "O que mudar?" "Nome" "Tempo de buffer" "Mensagens por resposta" "Modelos" "Handoff" "Voltar"
    case "$op" in
      1) com_voltar edita_nome ;;
      2) com_voltar edita_buffer ;;
      3) com_voltar edita_mensagens ;;
      4) com_voltar edita_modelo ;;
      5) com_voltar edita_handoff ;;
      *) return 0 ;;
    esac
    [ "$FALHOU" = 0 ] || pausa
  done
}

edita_nome() {
  local valor
  dica "Muda também o nome do bot, que aparece nas mensagens no Chatwoot. A pasta do prompt continua a mesma."
  pergunta valor "Nome" "$(jq -r '.nome' <<<"$AGENTE")"
  salva_agente "$(jq -n --arg v "$valor" '{nome: $v}')"
  if [ "$API_STATUS" = 422 ]; then
    printf '%s\n' "$RESULTADO"
    if confirma "Salvar o nome só aqui, sem mudar no Chatwoot?"; then
      salva_agente "$(jq -n --arg v "$valor" '{nome: $v, renomear_no_canal: false}')"
    fi
  fi
}

edita_buffer() {
  local valor
  dica "Quanto o agente espera o contato parar de mandar mensagens antes de responder."
  pergunta_numero valor "Segundos (1 a 60)" 1 60 "$(jq -r '.buffer_segundos' <<<"$AGENTE")"
  salva_agente "$(jq -n --argjson v "$valor" '{buffer_segundos: $v}')"
}

edita_mensagens() {
  local valor
  pergunta_numero valor "Máximo de mensagens por resposta (1 a 10)" 1 10 "$(jq -r '.max_mensagens_por_resposta' <<<"$AGENTE")"
  salva_agente "$(jq -n --argjson v "$valor" '{max_mensagens_por_resposta: $v}')"
}

edita_modelo() {
  escolhe_modelo_do_agente
  salva_agente "$CORPO_MODELO"
}

edita_handoff() {
  configura_handoff "$AGENTE"
  devolve AGENTE RESULTADO
}

fluxo_remover_agente() {
  local nome confirmacao corpo cliente_id
  secao "Remover agente"
  escolhe_agente || return 0
  nome=$(jq -r '.nome' <<<"$AGENTE")
  cliente_id=$(jq -r '.cliente_id' <<<"$AGENTE")
  echo
  aviso "$(destaque "$nome") para de responder na hora e o webhook deixa de valer."
  dica "O bot sai do Chatwoot. Conversas e consumo ficam guardados; o prompt fica em prompts/ e"
  dica "volta se você criar um agente com o mesmo nome nessa empresa."
  echo
  pergunta confirmacao "Para confirmar, digite $(destaque "$nome")"
  if [ "$(normaliza "$confirmacao")" != "$(normaliza "$nome")" ]; then
    falha "Você digitou $(destaque "$confirmacao"), e o agente se chama $(destaque "$nome"). Nada foi removido."
    return 0
  fi

  corpo=$(jq -n --arg c "$confirmacao" '{confirmacao: $c}')
  api_com_token DELETE "$(caminho_do_agente "$AGENTE")" "$corpo" "Removendo e apagando o bot no Chatwoot…"
  if [ "$API_STATUS" = 422 ]; then
    falha "$(detalhe_erro "$API_RESPOSTA")"
    confirma "Remover mesmo assim, deixando o bot no Chatwoot?" || return 0
    api DELETE "$(caminho_do_agente "$AGENTE")" "$(jq -c '. + {desconectar_canal: false}' <<<"$corpo")"
  fi
  if [ "$API_STATUS" != 200 ]; then
    falha "$(detalhe_erro "$API_RESPOSTA")"
    return 0
  fi
  ok "$(destaque "$nome") removido"
  if [ "$(jq -r '.canal_desconectado' <<<"$API_RESPOSTA")" != true ]; then
    aviso "O bot continua no Chatwoot: tire ele da caixa de entrada nas configurações de bot da caixa."
  fi

  [ "$(env_get MODO_INSTALACAO)" = revenda ] || return 0
  api GET "/admin/agentes?cliente_id=$cliente_id"
  [ "$API_STATUS" = 200 ] && [ "$(jq 'length' <<<"$API_RESPOSTA")" -eq 0 ] || return 0
  echo
  if confirma "A empresa $AGENTE_EMPRESA ficou sem agentes. Remover a empresa também?"; then
    api DELETE "/admin/clientes/$cliente_id" "$(jq -n --arg c "$AGENTE_EMPRESA" '{confirmacao: $c}')"
    if [ "$API_STATUS" = 204 ]; then
      ok "Empresa $(destaque "$AGENTE_EMPRESA") removida"
    else
      falha "$(detalhe_erro "$API_RESPOSTA")"
    fi
  fi
}

# Uma linha por empresa (total) e por agente, com 7 e 30 dias lado a lado.
mostra_consumo() {
  local semana mes nivel nome t7 k7 c7 t30 k30 c30 marca parcial="" data tipo onde erro
  api GET "/admin/consumo?dias=7"
  exige_api
  semana=$API_RESPOSTA
  api GET "/admin/consumo?dias=30"
  exige_api
  mes=$API_RESPOSTA

  secao "Consumo"
  if [ "$(jq '.agentes | length' <<<"$mes")" -eq 0 ]; then
    dica "Nenhum turno nos últimos 30 dias."
  else
    printf '  %s%s%s%s\n' "$CINZA" "$(coluna "" 22)" "$(coluna "últimos 7 dias" 28)" "últimos 30 dias$NORMAL"
    printf '  %s%s%7s %7s %9s   %7s %7s %9s%s\n' "$CINZA" "$(coluna "" 22)" turnos tokens "US\$" turnos tokens "US\$" "$NORMAL"
    while IFS=$'\x1f' read -r nivel nome t7 k7 c7 t30 k30 c30 marca; do
      [ -n "$marca" ] && parcial=1
      if [ "$nivel" = empresa ]; then
        printf '  %s%s%7s %7s %9s   %7s %7s %9s%s%s\n' "$NEGRITO" "$(coluna "$nome" 22)" "$t7" "$k7" "$c7" "$t30" "$k30" "$c30" "$marca" "$NORMAL"
      else
        printf '    %s%7s %7s %9s   %7s %7s %9s%s\n' "$(coluna "$nome" 20)" "$t7" "$k7" "$c7" "$t30" "$k30" "$c30" "$marca"
      fi
    done < <(jq -r --argjson semana "$semana" '
      def soma(lista): {
        turnos: (lista | map(.turnos) | add // 0),
        tokens: (lista | map(.tokens_entrada + .tokens_saida) | add // 0),
        custo: (lista | map(.custo_estimado | tonumber) | add // 0),
        sem_custo: (lista | map(.sem_custo) | add // 0)
      };
      def curto: if . >= 1000000 then "\(. / 100000 | floor / 10)M"
        elif . >= 1000 then "\(. / 1000 | floor)k" else tostring end;
      def dinheiro: (. * 100 | round) as $c | "\($c / 100 | floor).\(($c % 100) + 100 | tostring | .[1:])";
      def linha(nivel; nome; s; m): [nivel, nome, (s.turnos | tostring), (s.tokens | curto), (s.custo | dinheiro),
        (m.turnos | tostring), (m.tokens | curto), (m.custo | dinheiro),
        (if m.sem_custo > 0 then "*" else "" end)] | join("");
      .agentes | group_by(.cliente_id) | sort_by(.[0].cliente) | .[]
      | .[0].cliente_id as $cliente
      | linha("empresa"; .[0].cliente; soma($semana.agentes | map(select(.cliente_id == $cliente))); soma(.)),
        (.[] | .agente_id as $agente
          | linha("agente"; .agente; soma($semana.agentes | map(select(.agente_id == $agente))); soma([.])))
    ' <<<"$mes")
    [ -n "$parcial" ] && dica "* algum modelo não informou o preço: o custo real é maior que o mostrado."
  fi

  echo
  if [ "$(jq '.falhas | length' <<<"$mes")" -eq 0 ]; then
    ok "Nenhuma falha nos últimos 30 dias"
  else
    printf '  %sÚltimas falhas%s\n' "$NEGRITO" "$NORMAL"
    while IFS=$'\x1f' read -r data tipo onde erro; do
      printf '    %s%s%s  %s  %s%s%s\n' "$CINZA" "$data" "$NORMAL" "$(coluna "$tipo" 26)" "$CINZA" "$onde" "$NORMAL"
      [ -n "$erro" ] && printf '                 %s%s%s\n' "$CINZA" "$erro" "$NORMAL"
    done < <(jq -r '.falhas[] | [
        (.criado_em | sub("\\.[0-9]+"; "") | sub("[+]00:00$"; "Z") | fromdateiso8601 | strflocaltime("%d/%m %H:%M")),
        .tipo,
        ([.cliente, .agente] | map(select(. != null)) | join(" · ")),
        ((.detalhe.erro // .detalhe.problemas // "") | tostring | gsub("\\s+"; " ") | .[0:90])
      ] | join("")' <<<"$mes")
    dica "Detalhes: source deploy/compose.sh && dc logs api worker"
  fi
  echo
}

# Cada opção roda em `com_voltar`: Esc em qualquer pergunta volta para este menu, e erro no meio
# mostra o motivo e volta também, em vez de fechar o menu.
menu_operador() {
  local op
  while true; do
    secao "Menu"
    ESC_ESCOLHE=7 escolha op "O que fazer?" "Criar agente" "Listar agentes" "Editar agente" "Remover agente" \
      "Ver consumo e falhas" "Token do Chatwoot" "Sair"
    case "$op" in
      1) com_voltar acao_novo_agente ;;
      2) com_voltar com_pausa lista_agentes ;;
      3) com_voltar fluxo_editar_agente ;;
      4) com_voltar com_pausa fluxo_remover_agente ;;
      5) com_voltar com_pausa mostra_consumo ;;
      6) com_voltar com_pausa fluxo_token_chatwoot ;;
      *) return 0 ;;
    esac
    [ "$FALHOU" = 0 ] || pausa
  done
}

# O token de administrador fica guardado depois da primeira vez; aqui o operador pode esquecê-lo.
fluxo_token_chatwoot() {
  local op endereco linha
  local -a enderecos=()
  secao "Token do Chatwoot"
  api GET /admin/canais/chatwoot/acessos
  exige_api
  while IFS= read -r linha; do enderecos+=("$linha"); done < <(jq -r '.[].endereco' <<<"$API_RESPOSTA")
  if [ "${#enderecos[@]}" -eq 0 ]; then
    dica "Nenhum token guardado. Ele é pedido na próxima ação que precisar."
    return 0
  fi
  dica "Guardado criptografado. Criar, renomear e remover agente e trocar o handoff usam este token."
  echo
  escolha op "Esquecer o token de" "${enderecos[@]}"
  endereco=${enderecos[$((op - 1))]}
  api DELETE "/admin/canais/chatwoot/acessos?endereco=$(jq -rn --arg e "$endereco" '$e | @uri')"
  if [ "$API_STATUS" = 204 ]; then
    ok "Token esquecido. Será pedido de novo na próxima vez."
  else
    falha "$(detalhe_erro "$API_RESPOSTA")"
  fi
}

com_pausa() {
  "$@"
  pausa
}

novo_agente() {
  secao "Novo agente"
  fluxo_novo_agente
  dica "Mande uma mensagem na caixa de entrada para testar."
}

acao_novo_agente() {
  novo_agente
  pausa
}
