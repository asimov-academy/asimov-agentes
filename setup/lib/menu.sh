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
  case "$(jq -r '.canal' <<<"$AGENTE")" in
    nativo) campo "Handoff" "aparece na conversa do terminal" ;;
    waha | whatsapp)
      campo "Handoff" "$(nome_do_destino "$(jq -c '.handoff_destino' <<<"$AGENTE")")$(jq -r '
        if .retomada_automatica_horas then "; volta com 👍 ou em \(.retomada_automatica_horas) h"
        else "; volta com 👍 ou /retomar" end' <<<"$AGENTE")"
      campo "Atende" "$(atende_do_agente "$AGENTE")"
      ;;
    *)
      campo "Handoff" "$(nome_do_destino "$(jq -c '.handoff_destino' <<<"$AGENTE")")$(jq -r '
        if .retomada_automatica_horas then "; volta em \(.retomada_automatica_horas) h se ninguém devolver"
        else "; volta quando a conversa voltar para Pendente" end' <<<"$AGENTE")"
      ;;
  esac
  campo "Digitação" "$(jq -r '"\(.digitacao_caracteres_por_segundo) caracteres/s, até \(.digitacao_maximo_segundos) s por mensagem"' <<<"$AGENTE")"
  campo "Ferramentas" "$(jq -r '(.ferramentas // []) | if length == 0 then "nenhuma" else map({calculadora: "calculadora", busca_web: "busca na web"}[.] // .) | join(", ") end' <<<"$AGENTE")"
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
  while IFS= read -r provedor; do provedores+=("$provedor"); done < <(provedores_com_chave)
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
  local -a rotulos acoes
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
    rotulos=("Nome" "Tempo de buffer" "Mensagens por resposta" "Digitação" "Ferramentas" "Modelos")
    acoes=(edita_nome edita_buffer edita_mensagens edita_digitacao edita_ferramentas edita_modelo)
    # No nativo o handoff aparece no próprio terminal: não há destino para escolher, mas dá para
    # ligar o agente num canal.
    case "$(jq -r '.canal' <<<"$AGENTE")" in
      nativo)
        rotulos+=("Conectar a um canal")
        acoes+=(conecta_canal)
        ;;
      waha)
        rotulos+=("WhatsApp")
        acoes+=(edita_waha)
        ;;
      whatsapp)
        rotulos+=("WhatsApp")
        acoes+=(edita_whatsapp)
        ;;
      *)
        rotulos+=("Handoff")
        acoes+=(edita_handoff)
        ;;
    esac
    rotulos+=("Voltar")
    ESC_ESCOLHE=${#rotulos[@]} escolha op "O que mudar?" "${rotulos[@]}"
    [ "$op" -lt "${#rotulos[@]}" ] || return 0
    com_voltar "${acoes[$((op - 1))]}"
    [ "$FALHOU" = 0 ] || pausa
  done
}

edita_nome() {
  local valor
  if [ "$(jq -r '.canal' <<<"$AGENTE")" = chatwoot ]; then
    dica "Muda também o nome do bot, que aparece nas mensagens no Chatwoot. A pasta do prompt continua a mesma."
  else
    dica "A pasta do prompt continua a mesma."
  fi
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

edita_digitacao() {
  local velocidade maximo
  dica "Antes de cada mensagem o agente fica digitando o tempo que uma pessoa levaria para escrever."
  dica "No celular, uma pessoa digita de 4 a 8 caracteres por segundo."
  pergunta_numero velocidade "Caracteres por segundo (1 a 30)" 1 30 "$(jq -r '.digitacao_caracteres_por_segundo' <<<"$AGENTE")"
  dica "Teto por mensagem, para resposta longa não demorar demais."
  pergunta_numero maximo "Máximo de segundos por mensagem (1 a 30)" 1 30 "$(jq -r '.digitacao_maximo_segundos' <<<"$AGENTE")"
  salva_agente "$(jq -n --argjson v "$velocidade" --argjson m "$maximo" \
    '{digitacao_caracteres_por_segundo: $v, digitacao_maximo_segundos: $m}')"
}

edita_ferramentas() {
  local escolhidas
  escolhe_ferramentas escolhidas "$AGENTE"
  salva_agente "$(jq -n --argjson f "$escolhidas" '{ferramentas: $f}')"
}

edita_modelo() {
  escolhe_modelo_do_agente
  salva_agente "$CORPO_MODELO"
}

# conecta_canal: liga o AGENTE nativo num canal externo. Prompt, modelos, ferramentas e conversas ficam.
conecta_canal() {
  local nome op
  nome=$(jq -r '.nome' <<<"$AGENTE")
  echo
  dica "$nome passa a atender pelo canal com o mesmo prompt, modelos e ferramentas."
  dica "A conversa de teste aqui no terminal continua funcionando."
  echo
  escolha op "Canal" \
    "Chatwoot  ${CINZA}caixa de entrada de um Chatwoot que já existe${NORMAL}" \
    "WhatsApp oficial  ${CINZA}Cloud API da Meta: número homologado, cobrado por mensagem${NORMAL}" \
    "WhatsApp pela WAHA  ${CINZA}seu número, pareado por QR code; API não oficial${NORMAL}"
  case "$op" in
    1) conecta_chatwoot "$nome" ;;
    2) conecta_whatsapp "$nome" ;;
    *) conecta_waha "$nome" ;;
  esac
  devolve AGENTE RESULTADO
}

conecta_chatwoot() {
  local nome=$1 corpo rapido=""
  escolhe_caixa_chatwoot
  pergunta_retomada 4 chatwoot
  ritmo_do_whatsapp && rapido=1

  corpo=$(jq -n --argjson conexao "$CHATWOOT_CONEXAO" --argjson destino "$HANDOFF_DESTINO" \
    --argjson horas "$RETOMADA_HORAS" \
    '{canal: "chatwoot", conexao: $conexao, handoff_destino: $destino, retomada_automatica_horas: $horas}')
  api_com_token POST "$(caminho_do_agente "$AGENTE")/canal" "$corpo" "Criando o bot no Chatwoot…"
  if [ "$API_STATUS" != 200 ]; then
    RESULTADO=$(falha "$(detalhe_erro "$API_RESPOSTA")")
    return 0
  fi
  AGENTE=$API_RESPOSTA
  RESULTADO=$(ok "$(destaque "$nome") no ar na caixa $(destaque "$AGENTE_CAIXA") ${CINZA}· handoff para $(nome_do_destino "$HANDOFF_DESTINO")${NORMAL}")
  [ -n "$rapido" ] && aplica_ritmo_do_whatsapp
  return 0
}

conecta_waha() {
  local nome=$1 rapido=""
  aviso_nao_oficial || return 0
  garante_waha
  prepara_aparelho "$nome" "$AGENTE_EMPRESA"
  pergunta_retomada
  ritmo_do_whatsapp && rapido=1

  api POST "$(caminho_do_agente "$AGENTE")/canal" '{"canal": "waha", "conexao": {}}'
  if [ "$API_STATUS" != 200 ]; then
    RESULTADO=$(falha "$(detalhe_erro "$API_RESPOSTA")")
    return 0
  fi
  AGENTE=$API_RESPOSTA
  api PATCH "$(caminho_do_agente "$AGENTE")" "$(jq -n --argjson h "$RETOMADA_HORAS" '{retomada_automatica_horas: $h}')"
  [ "$API_STATUS" = 200 ] && AGENTE=$API_RESPOSTA
  [ -n "$rapido" ] && aplica_ritmo_do_whatsapp

  if espera_waha "$AGENTE"; then
    escolhe_destino_waha "$AGENTE"
    api PATCH "$(caminho_do_agente "$AGENTE")" "$(jq -n --argjson d "$HANDOFF_DESTINO" '{handoff_destino: $d}')"
    if [ "$API_STATUS" = 200 ]; then
      AGENTE=$API_RESPOSTA
      RESULTADO=$(ok "$(destaque "$nome") atende no WhatsApp $(destaque "+$WAHA_NUMERO") ${CINZA}· handoff para $(nome_do_destino "$HANDOFF_DESTINO")${NORMAL}")
      return 0
    fi
    RESULTADO=$(falha "$(detalhe_erro "$API_RESPOSTA")")
    return 0
  fi
  RESULTADO=$(aviso "$(destaque "$nome") está no WhatsApp, mas o número ainda não foi pareado. Volte em WhatsApp para ler o QR code.")
  return 0
}

# O ritmo de teste (buffer e digitando curtos) parece robô para quem escreve no WhatsApp.
ritmo_do_whatsapp() {
  [ "$(jq -r '.buffer_segundos < 8 or .digitacao_maximo_segundos < 20' <<<"$AGENTE")" = true ] || return 1
  echo
  dica "O ritmo de teste (buffer e digitando curtos) parece robô para quem escreve no WhatsApp."
  confirma "Usar o ritmo do WhatsApp (espera 8 s e digita como uma pessoa)?"
}

aplica_ritmo_do_whatsapp() {
  api PATCH "$(caminho_do_agente "$AGENTE")" '{"buffer_segundos": 8, "digitacao_caracteres_por_segundo": 6, "digitacao_maximo_segundos": 20}'
  if [ "$API_STATUS" = 200 ]; then
    AGENTE=$API_RESPOSTA
  else
    RESULTADO+=$'\n'$(falha "Ritmo não mudou: $(detalhe_erro "$API_RESPOSTA")")
  fi
}

edita_handoff() {
  configura_handoff "$AGENTE"
  devolve AGENTE RESULTADO
}

fluxo_remover_agente() {
  local nome confirmacao corpo cliente_id canal aguarde="Removendo…"
  secao "Remover agente"
  escolhe_agente || return 0
  nome=$(jq -r '.nome' <<<"$AGENTE")
  cliente_id=$(jq -r '.cliente_id' <<<"$AGENTE")
  canal=$(jq -r '.canal' <<<"$AGENTE")
  echo
  case "$canal" in
    chatwoot)
      aviso "$(destaque "$nome") para de responder na hora e o webhook deixa de valer."
      dica "O bot sai do Chatwoot. Conversas e consumo ficam guardados; o prompt fica em prompts/ e"
      aguarde="Removendo e apagando o bot no Chatwoot…"
      ;;
    whatsapp)
      aviso "$(destaque "$nome") para de responder na hora e o webhook deixa de valer."
      dica "O número continua na Meta, com os webhooks de volta para a URL do app. Conversas e"
      dica "consumo ficam guardados; o prompt fica em prompts/ e"
      aguarde="Removendo e devolvendo o webhook na Meta…"
      ;;
    waha)
      aviso "$(destaque "$nome") para de responder na hora e o número é desconectado."
      dica "O aparelho sai da lista de aparelhos conectados do WhatsApp. Conversas e consumo ficam"
      dica "guardados; o prompt fica em prompts/ e"
      aguarde="Removendo e desconectando o número…"
      ;;
    *)
      aviso "$(destaque "$nome") deixa de conversar no terminal."
      dica "Conversas e consumo ficam guardados; o prompt fica em prompts/ e"
      ;;
  esac
  dica "volta se você criar um agente com o mesmo nome nessa empresa."
  echo
  pergunta confirmacao "Para confirmar, digite $(destaque "$nome")"
  if [ "$(normaliza "$confirmacao")" != "$(normaliza "$nome")" ]; then
    falha "Você digitou $(destaque "$confirmacao"), e o agente se chama $(destaque "$nome"). Nada foi removido."
    return 0
  fi

  corpo=$(jq -n --arg c "$confirmacao" '{confirmacao: $c}')
  api_com_token DELETE "$(caminho_do_agente "$AGENTE")" "$corpo" "$aguarde"
  if [ "$API_STATUS" = 422 ]; then
    falha "$(detalhe_erro "$API_RESPOSTA")"
    confirma "Remover mesmo assim, deixando a conexão no canal?" || return 0
    api DELETE "$(caminho_do_agente "$AGENTE")" "$(jq -c '. + {desconectar_canal: false}' <<<"$corpo")"
  fi
  if [ "$API_STATUS" != 200 ]; then
    falha "$(detalhe_erro "$API_RESPOSTA")"
    return 0
  fi
  ok "$(destaque "$nome") removido"
  if [ "$(jq -r '.canal_desconectado' <<<"$API_RESPOSTA")" != true ]; then
    if [ "$canal" = waha ]; then
      aviso "O número continua conectado: tire o aparelho no WhatsApp, em Aparelhos conectados."
    elif [ "$canal" = whatsapp ]; then
      aviso "O webhook do número continua apontado para cá: tire o override no painel da Meta."
    else
      aviso "O bot continua no Chatwoot: tire ele da caixa de entrada nas configurações de bot da caixa."
    fi
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
  local semana mes nivel nome t7 k7 c7 t30 k30 c30 asterisco parcial="" data tipo onde erro op linha
  local filtro="" titulo="Consumo"
  local -a ids=() nomes=()
  api GET /admin/clientes
  exige_api
  while IFS=$'\t' read -r nome linha; do nomes+=("$nome"); ids+=("$linha"); done \
    < <(jq -r '.[] | [.nome, .id] | @tsv' <<<"$API_RESPOSTA")
  if [ "${#ids[@]}" -gt 1 ]; then
    secao "Consumo"
    escolha op "De qual empresa?" "Todas as empresas" "${nomes[@]}"
    if [ "$op" -gt 1 ]; then
      filtro="&cliente_id=${ids[$((op - 2))]}"
      titulo="Consumo · ${nomes[$((op - 2))]}"
    fi
  fi
  api GET "/admin/consumo?dias=7$filtro"
  exige_api
  semana=$API_RESPOSTA
  api GET "/admin/consumo?dias=30$filtro"
  exige_api
  mes=$API_RESPOSTA

  secao "$titulo"
  if [ "$(jq '.agentes | length' <<<"$mes")" -eq 0 ]; then
    dica "Nenhum turno nos últimos 30 dias."
  else
    printf '  %s%s%s%s\n' "$CINZA" "$(coluna "" 22)" "$(coluna "últimos 7 dias" 28)" "últimos 30 dias$NORMAL"
    printf '  %s%s%7s %7s %9s   %7s %7s %9s%s\n' "$CINZA" "$(coluna "" 22)" turnos tokens "US\$" turnos tokens "US\$" "$NORMAL"
    while IFS=$'\x1f' read -r nivel nome t7 k7 c7 t30 k30 c30 asterisco; do
      [ -n "$asterisco" ] && parcial=1
      if [ "$nivel" = empresa ]; then
        printf '  %s%s%7s %7s %9s   %7s %7s %9s%s%s\n' "$NEGRITO" "$(coluna "$nome" 22)" "$t7" "$k7" "$c7" "$t30" "$k30" "$c30" "$asterisco" "$NORMAL"
      else
        printf '    %s%7s %7s %9s   %7s %7s %9s%s\n' "$(coluna "$nome" 20)" "$t7" "$k7" "$c7" "$t30" "$k30" "$c30" "$asterisco"
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
  local -a rotulos acoes
  # Uma consulta só ao abrir: número fora do ar deixa o agente mudo e ninguém percebe sozinho.
  avisa_numeros_fora_do_ar
  while true; do
    secao "Menu"
    # A WAHA atualiza sozinha; o aviso aparece aqui quando ela precisou voltar para a versão anterior.
    [ -n "$(estado_get waha_aviso)" ] && aviso "WhatsApp: $(estado_get waha_aviso)"
    if [ -n "${AVISO_WAHA:-}" ]; then
      aviso "Número fora do ar no WhatsApp: $(destaque "$AVISO_WAHA")"
      dica "Leia o QR code de novo em Editar agente > WhatsApp > Parear o número."
    fi
    rotulos=("Criar agente" "Conversar com agente" "Listar agentes" "Editar agente" "Remover agente" "Ver consumo e falhas")
    acoes=(acao_novo_agente fluxo_conversar "com_pausa lista_agentes" fluxo_editar_agente "com_pausa fluxo_remover_agente" "com_pausa mostra_consumo")
    if [ "$(env_get WAHA_ATIVA)" = 1 ]; then
      rotulos+=("WhatsApp (WAHA)")
      acoes+=("com_pausa fluxo_waha")
    fi
    rotulos+=("Token do Chatwoot" "Sair")
    acoes+=("com_pausa fluxo_token_chatwoot")
    ESC_ESCOLHE=${#rotulos[@]} escolha op "O que fazer?" "${rotulos[@]}"
    [ "$op" -lt "${#rotulos[@]}" ] || return 0
    # shellcheck disable=SC2086  # a ação pode vir com `com_pausa` na frente
    com_voltar ${acoes[$((op - 1))]}
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
  if [ "$AGENTE_CANAL" = chatwoot ]; then
    dica "Mande uma mensagem na caixa de entrada para testar."
    return 0
  fi
  echo
  if confirma "Conversar com $AGENTE_NOME agora?"; then
    conversa_no_terminal
    AGENTE_CONVERSOU=1
  else
    dica "Para conversar depois: asimov conversar"
  fi
}

acao_novo_agente() {
  AGENTE_CONVERSOU=""
  novo_agente
  # Quem saiu da conversa já leu tudo: volta direto ao menu.
  [ -n "$AGENTE_CONVERSOU" ] || pausa
}
