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
  api PATCH "$(caminho_do_agente "$AGENTE")" "$1"
  if [ "$API_STATUS" = 200 ]; then
    AGENTE=$API_RESPOSTA
    RESULTADO=$(ok "Salvo. Vale a partir da próxima mensagem.")
  else
    RESULTADO=$(falha "$(detalhe_erro "$API_RESPOSTA")")
  fi
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

fluxo_editar_agente() {
  local op valor
  secao "Editar agente"
  # Sem agentes devolve 1: o menu segura a tela com a dica.
  escolhe_agente || return 1
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
    escolha op "O que mudar?" "Nome" "Tempo de buffer" "Mensagens por resposta" "Modelos" "Handoff" "Voltar"
    case "$op" in
      1)
        dica "O nome do bot no Chatwoot e a pasta do prompt continuam os mesmos."
        pergunta valor "Nome" "$(jq -r '.nome' <<<"$AGENTE")"
        salva_agente "$(jq -n --arg v "$valor" '{nome: $v}')"
        ;;
      2)
        dica "Quanto o agente espera o contato parar de mandar mensagens antes de responder."
        pergunta_numero valor "Segundos (1 a 60)" 1 60 "$(jq -r '.buffer_segundos' <<<"$AGENTE")"
        salva_agente "$(jq -n --argjson v "$valor" '{buffer_segundos: $v}')"
        ;;
      3)
        pergunta_numero valor "Máximo de mensagens por resposta (1 a 10)" 1 10 "$(jq -r '.max_mensagens_por_resposta' <<<"$AGENTE")"
        salva_agente "$(jq -n --argjson v "$valor" '{max_mensagens_por_resposta: $v}')"
        ;;
      4)
        escolhe_modelo_do_agente
        salva_agente "$CORPO_MODELO"
        ;;
      5) configura_handoff "$AGENTE" ;;
      *) return 0 ;;
    esac
  done
}

fluxo_remover_agente() {
  local nome confirmacao conexao=null corpo token cliente_id
  secao "Remover agente"
  escolhe_agente || return 0
  nome=$(jq -r '.nome' <<<"$AGENTE")
  cliente_id=$(jq -r '.cliente_id' <<<"$AGENTE")
  echo
  aviso "$(destaque "$nome") para de responder na hora e o webhook deixa de valer."
  dica "Conversas e consumo ficam guardados. O prompt fica em prompts/ e volta se você criar"
  dica "um agente com o mesmo nome nessa empresa."
  echo
  pergunta confirmacao "Digite o nome do agente para confirmar"
  if [ "$(jq -n --arg a "$confirmacao" --arg b "$nome" '($a | ascii_downcase | ltrimstr(" ") | rtrimstr(" ")) == ($b | ascii_downcase)')" != true ]; then
    falha "O nome não confere. Nada foi removido."
    return 0
  fi

  echo
  dica "Com o token de administrador do Chatwoot, o bot também sai da caixa de entrada."
  if confirma "Apagar o bot no Chatwoot?"; then
    pergunta_secreta token "Token de acesso"
    conexao=$(jq -n --arg token "$token" '{token_admin: $token}')
    unset token
  fi
  corpo=$(jq -n --arg c "$confirmacao" --argjson conexao "$conexao" '{confirmacao: $c, conexao: $conexao}')
  printf '  %sRemovendo…%s' "$CINZA" "$NORMAL"
  api DELETE "$(caminho_do_agente "$AGENTE")" "$corpo"
  printf '\r\033[K'
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

menu_operador() {
  local op
  while true; do
    secao "Menu"
    escolha op "O que fazer?" "Criar agente" "Listar agentes" "Editar agente" "Remover agente" \
      "Ver consumo e falhas" "Sair"
    case "$op" in
      1)
        secao "Novo agente"
        fluxo_novo_agente
        dica "Mande uma mensagem na caixa de entrada para testar."
        pausa
        ;;
      2)
        lista_agentes
        pausa
        ;;
      3) fluxo_editar_agente || pausa ;;
      4)
        fluxo_remover_agente
        pausa
        ;;
      5)
        mostra_consumo
        pausa
        ;;
      *) return 0 ;;
    esac
  done
}
