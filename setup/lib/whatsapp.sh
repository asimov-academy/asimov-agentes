#!/usr/bin/env bash
# shellcheck disable=SC2034  # AGENTE_*, WHATSAPP_* e HANDOFF_DESTINO são lidas pelas telas
# WhatsApp oficial (Cloud API da Meta): credenciais do app, número da conta e template do aviso.
#
# Nada sobe na VPS por causa deste canal: quem fala com a Meta é a própria API. O endereço do
# webhook é apontado no número pela API, no momento em que o agente é criado; o operador não cola
# URL nenhuma no painel da Meta.

# Texto do template que o operador manda aprovar. Três parâmetros, na ordem em que o aviso usa.
TEMPLATE_SUGERIDO_NOME="aviso_handoff"

mostra_template_sugerido() {
  echo
  dica "Crie na Meta um template de categoria Utilidade, em português, com este corpo:"
  echo
  printf '    %sO agente passou uma conversa para voce.%s\n' "$CINZA" "$NORMAL"
  printf '    %s%s\n' "$CINZA" "$NORMAL"
  printf '    %sContato: {{1}}%s\n' "$CINZA" "$NORMAL"
  printf '    %sResumo: {{2}}%s\n' "$CINZA" "$NORMAL"
  printf '    %sCodigo: {{3}}%s\n' "$CINZA" "$NORMAL"
  printf '    %s%s\n' "$CINZA" "$NORMAL"
  printf '    %sResponda /retomar neste chat quando terminar.%s\n' "$CINZA" "$NORMAL"
  echo
  dica "Nome sugerido: $TEMPLATE_SUGERIDO_NOME. A aprovação costuma sair em alguns minutos."
}

# aviso_oficial: o que muda em relação à WAHA. Devolve 1 se o operador desistir.
aviso_oficial() {
  echo
  info "O WhatsApp oficial é a $(destaque "Cloud API da Meta"): número homologado, sem risco de bloqueio."
  dica "A Meta cobra por conversa, conforme a tabela dela. O número fica só com o agente: ele não"
  dica "roda no celular, então ninguém responde pelo aparelho como acontece na WAHA."
  dica "Você precisa ter, na Meta: um app, a conta de WhatsApp Business com o número, um token de"
  dica "acesso permanente, o segredo do app e um template aprovado para o aviso de handoff."
  echo
  confirma "Tenho isso em mãos. Continuar?"
}

# pede_credenciais_whatsapp: pergunta conta, token e segredo e confere na Meta.
# Define WHATSAPP_CONEXAO (JSON sem o número) e WHATSAPP_ACHADO (números e templates).
pede_credenciais_whatsapp() {
  local conta app token segredo corpo
  echo
  dica "Passo a passo com links: docs/whatsapp-oficial.md, no repositório."
  dica "Conta de WhatsApp Business (WABA ID): painel da Meta, em WhatsApp > Configuração da API."
  while true; do
    pergunta conta "ID da conta de WhatsApp Business" "$(estado_get whatsapp_waba)"
    conta=$(tr -cd '0-9' <<<"$conta")
    if [ -z "$conta" ]; then
      falha "O ID da conta é só números."
      continue
    fi
    dica "ID do app: painel da Meta, em Configurações do app > Básico, no topo."
    pergunta app "ID do app" "$(estado_get whatsapp_app)"
    app=$(tr -cd '0-9' <<<"$app")
    if [ -z "$app" ]; then
      falha "O ID do app é só números."
      continue
    fi
    dica "Token de acesso permanente (usuário do sistema), não o token de teste de 24 horas."
    pergunta_secreta token "Token de acesso"
    dica "Segredo do app: painel da Meta, em Configurações do app > Básico > Chave secreta."
    pergunta_secreta segredo "Segredo do app"
    corpo=$(jq -n --arg c "$conta" --arg a "$app" --arg t "$token" --arg s "$segredo" \
      '{conexao: {waba_id: $c, app_id: $a, access_token: $t, app_secret: $s}}')
    api_com_token POST /admin/canais/whatsapp/descobrir "$corpo" "Conferindo na Meta…"
    if [ "$API_STATUS" = 200 ]; then
      estado_set whatsapp_waba "$conta"
      estado_set whatsapp_app "$app"
      WHATSAPP_CONEXAO=$(jq -c '.conexao' <<<"$corpo")
      WHATSAPP_ACHADO=$API_RESPOSTA
      unset token segredo
      return 0
    fi
    unset token segredo
    falha "$(detalhe_erro "$API_RESPOSTA")"
  done
}

# escolhe_numero_whatsapp: põe o `phone_number_id` escolhido em WHATSAPP_CONEXAO.
# Define WHATSAPP_NUMERO (como a Meta mostra). Devolve 1 se a conta não tem número.
escolhe_numero_whatsapp() {
  local numeros total op linha id
  local -a rotulos=()
  numeros=$(jq -c '.numeros' <<<"$WHATSAPP_ACHADO")
  total=$(jq 'length' <<<"$numeros")
  if [ "$total" -eq 0 ]; then
    falha "Essa conta não tem nenhum número. Adicione o número na Meta e tente de novo."
    return 1
  fi
  while IFS= read -r linha; do rotulos+=("$linha"); done \
    < <(jq -r --arg cinza "$CINZA" --arg normal "$NORMAL" '.[] | "\(.numero)  \($cinza)\(.nome)\($normal)"' <<<"$numeros")
  if [ "$total" -eq 1 ]; then
    op=1
    ok "Número: $(destaque "$(jq -r '.[0].numero' <<<"$numeros")")"
  else
    echo
    escolha op "Número do agente" "${rotulos[@]}"
  fi
  id=$(jq -r ".[$((op - 1))].phone_number_id" <<<"$numeros")
  WHATSAPP_NUMERO=$(jq -r ".[$((op - 1))].numero" <<<"$numeros")
  WHATSAPP_CONEXAO=$(jq -c --arg id "$id" '. + {phone_number_id: $id}' <<<"$WHATSAPP_CONEXAO")
  return 0
}

# escolhe_template_whatsapp JSON_DOS_TEMPLATES [NOME_ATUAL]: define TEMPLATE_HANDOFF (JSON ou null).
# Só entram os aprovados com três parâmetros: com outro formato o aviso não caberia.
escolhe_template_whatsapp() {
  local servem=$1 atual=${2:-} op total linha
  local -a rotulos=()
  servem=$(jq -c '[.[] | select(.serve // (.situacao == "APPROVED" and .parametros == 3))]' <<<"$servem")
  total=$(jq 'length' <<<"$servem")
  TEMPLATE_HANDOFF=null
  echo
  dica "Fora da janela de 24 horas, a Meta só entrega template aprovado: é ele que leva o aviso."
  if [ "$total" -eq 0 ]; then
    aviso "Nenhum template aprovado com três parâmetros nessa conta."
    mostra_template_sugerido
    dica "Sem ele, o aviso de handoff só chega se o destino tiver escrito ao agente nas últimas 24 h."
    confirma "Seguir sem template por enquanto?" && return 0
    return 1
  fi
  while IFS= read -r linha; do rotulos+=("$linha"); done \
    < <(jq -r --arg cinza "$CINZA" --arg normal "$NORMAL" '.[] | "\(.nome)  \($cinza)\(.idioma)\($normal)"' <<<"$servem")
  if [ -n "$atual" ]; then
    ok "Hoje: $(destaque "$atual")"
  fi
  echo
  escolha op "Template do aviso de handoff" "${rotulos[@]}"
  TEMPLATE_HANDOFF=$(jq -c --argjson i "$((op - 1))" '{nome: .[$i].nome, idioma: .[$i].idioma}' <<<"$servem")
  return 0
}

# escolhe_destino_whatsapp JSON_DOS_TEMPLATES [DESTINO_ATUAL]: define HANDOFF_DESTINO.
escolhe_destino_whatsapp() {
  local templates=$1 atual=${2:-null} telefone padrao
  padrao=$(jq -r '.telefone // ""' <<<"$atual")
  echo
  dica "Quando o agente passar a conversa para uma pessoa, o aviso com o resumo vai para cá."
  dica "Para devolver: 👍 no aviso, ou /retomar no mesmo chat."
  dica "Com DDI e DDD, como 5511988887777. Precisa ser um número que use WhatsApp."
  while true; do
    pergunta telefone "Número que recebe o handoff" "$padrao"
    telefone=$(tr -cd '0-9' <<<"$telefone")
    if [ "${#telefone}" -ge 10 ] && [ "${#telefone}" -le 15 ]; then
      break
    fi
    falha "Número fora do formato: use DDI, DDD e o número, só dígitos."
  done
  escolhe_template_whatsapp "$templates" "$(jq -r '.template.nome // ""' <<<"$atual")" || return 1
  HANDOFF_DESTINO=$(jq -n --arg t "$telefone" --argjson tpl "$TEMPLATE_HANDOFF" \
    '{tipo: "numero", telefone: $t} + (if $tpl == null then {} else {template: $tpl} end)')
  return 0
}

# Credenciais → número → nome → empresa → ferramentas → handoff → cria.
# O webhook é apontado no número pela própria criação: a Meta confere o endereço na hora.
fluxo_agente_whatsapp() {
  local nome corpo ferramentas
  AGENTE_CANAL=whatsapp
  secao "Agente no WhatsApp oficial"
  aviso_oficial || return 0
  pede_credenciais_whatsapp
  escolhe_numero_whatsapp || return 0
  AGENTE_CAIXA=$WHATSAPP_NUMERO

  echo
  pergunta nome "Nome do agente"
  escolhe_empresa ""
  escolhe_ferramentas ferramentas ""
  pergunta_retomada 4 whatsapp
  escolhe_contatos_permitidos
  escolhe_destino_whatsapp "$(jq -c '.templates_todos' <<<"$WHATSAPP_ACHADO")" || return 0

  while true; do
    corpo=$(jq -n --arg nome "$nome" --argjson conexao "$WHATSAPP_CONEXAO" --argjson f "$ferramentas" \
      --argjson destino "$HANDOFF_DESTINO" --argjson horas "$RETOMADA_HORAS" \
      --argjson permitidos "$CONTATOS_PERMITIDOS" \
      '{nome: $nome, canal: "whatsapp", conexao: $conexao, ferramentas: $f, handoff_destino: $destino,
        retomada_automatica_horas: $horas, contatos_permitidos: $permitidos}')
    api_com_token POST "/admin/clientes/$EMPRESA_ID/agentes" "$corpo" "Apontando o webhook na Meta…"
    if [ "$API_STATUS" = 201 ]; then break; fi
    falha "$(detalhe_erro "$API_RESPOSTA")"
    if [ "$API_STATUS" = 409 ]; then
      pergunta nome "Outro nome para o agente"
    elif confirma "Tentar com outras credenciais?"; then
      pede_credenciais_whatsapp
      escolhe_numero_whatsapp || return 0
    else
      return 0
    fi
  done

  AGENTE=$API_RESPOSTA
  AGENTE_NOME=$nome
  AGENTE_ID=$(jq -r .id <<<"$AGENTE")
  echo
  ok "$(destaque "$nome") no ar no número $(destaque "$WHATSAPP_NUMERO") ${CINZA}· $EMPRESA_NOME${NORMAL}"
  ok "Handoff para $(destaque "$(nome_do_destino "$(jq -c .handoff_destino <<<"$AGENTE")")")"
  dica "Mande uma mensagem para o número e o agente responde."
}

# conecta_whatsapp NOME: liga um agente nativo no WhatsApp oficial (Editar agente).
conecta_whatsapp() {
  local nome=$1 corpo rapido=""
  aviso_oficial || return 0
  pede_credenciais_whatsapp
  escolhe_numero_whatsapp || return 0
  pergunta_retomada 4 whatsapp
  escolhe_destino_whatsapp "$(jq -c '.templates_todos' <<<"$WHATSAPP_ACHADO")" || return 0
  ritmo_do_whatsapp && rapido=1

  corpo=$(jq -n --argjson conexao "$WHATSAPP_CONEXAO" --argjson destino "$HANDOFF_DESTINO" \
    --argjson horas "$RETOMADA_HORAS" \
    '{canal: "whatsapp", conexao: $conexao, handoff_destino: $destino, retomada_automatica_horas: $horas}')
  api_com_token POST "$(caminho_do_agente "$AGENTE")/canal" "$corpo" "Apontando o webhook na Meta…"
  if [ "$API_STATUS" != 200 ]; then
    RESULTADO=$(falha "$(detalhe_erro "$API_RESPOSTA")")
    return 0
  fi
  AGENTE=$API_RESPOSTA
  [ -n "$rapido" ] && aplica_ritmo_do_whatsapp
  RESULTADO=$(ok "$(destaque "$nome") atende no WhatsApp $(destaque "$WHATSAPP_NUMERO") ${CINZA}· handoff para $(nome_do_destino "$HANDOFF_DESTINO")${NORMAL}")
  return 0
}

# templates_do_agente: lista os templates da conta do AGENTE. Define WHATSAPP_TEMPLATES.
templates_do_agente() {
  api_com_token GET "$(caminho_do_agente "$AGENTE")/whatsapp/templates" "" "Procurando os templates…"
  if [ "$API_STATUS" != 200 ]; then
    WHATSAPP_TEMPLATES="[]"
    return 1
  fi
  WHATSAPP_TEMPLATES=$API_RESPOSTA
  return 0
}

# Editar agente, opção WhatsApp: confere o número na Meta e troca destino, prazo e quem atende.
edita_whatsapp() {
  local op nome
  nome=$(jq -r '.nome' <<<"$AGENTE")
  api_com_token GET "$(caminho_do_agente "$AGENTE")/whatsapp" "" "Conferindo o número na Meta…"
  secao "WhatsApp de $nome"
  if [ "$API_STATUS" = 200 ]; then
    campo "Número" "$(jq -r '.numero' <<<"$API_RESPOSTA") ${CINZA}$(jq -r '.nome' <<<"$API_RESPOSTA")${NORMAL}"
  else
    campo "Número" "não consegui falar com a Meta: $(detalhe_erro "$API_RESPOSTA")"
  fi
  campo "Handoff" "$(nome_do_destino "$(jq -c '.handoff_destino' <<<"$AGENTE")")"
  campo "Template" "$(jq -r '.handoff_destino.template.nome // "nenhum: o aviso só chega dentro da janela de 24 h"' <<<"$AGENTE")"
  campo "Retomada" "👍 no aviso$(jq -r 'if .retomada_automatica_horas then ", ou sozinho em \(.retomada_automatica_horas) h" else " ou /retomar" end' <<<"$AGENTE")"
  campo "Atende" "$(atende_do_agente "$AGENTE")"
  echo
  ESC_ESCOLHE=5 escolha op "O que fazer?" \
    "Quem recebe o handoff  ${CINZA}número e template${NORMAL}" \
    "Horas até voltar sozinho" \
    "Quem o agente atende" \
    "Refazer o webhook na Meta  ${CINZA}se o agente parou de receber mensagem${NORMAL}" \
    "Voltar"
  case "$op" in
    1)
      templates_do_agente || aviso "Não consegui listar os templates agora."
      escolhe_destino_whatsapp "$WHATSAPP_TEMPLATES" "$(jq -c '.handoff_destino // {}' <<<"$AGENTE")" || return 0
      salva_agente "$(jq -n --argjson d "$HANDOFF_DESTINO" '{handoff_destino: $d}')"
      ;;
    2)
      pergunta_retomada "$(jq -r '.retomada_automatica_horas // 0' <<<"$AGENTE")" whatsapp
      salva_agente "$(jq -n --argjson h "$RETOMADA_HORAS" '{retomada_automatica_horas: $h}')"
      ;;
    3)
      escolhe_contatos_permitidos "$(jq -c '.contatos_permitidos // []' <<<"$AGENTE")"
      salva_agente "$(jq -n --argjson p "$CONTATOS_PERMITIDOS" '{contatos_permitidos: $p}')"
      ;;
    4)
      echo
      dica "Liga de novo os webhooks do app, inscreve a conta e aponta o número para este servidor."
      api_com_token POST "$(caminho_do_agente "$AGENTE")/whatsapp/webhook" '{}' "Refazendo na Meta…"
      if [ "$API_STATUS" = 204 ]; then
        ok "Webhook refeito. Mande uma mensagem para o número e confira com: asimov consumo"
      else
        falha "$(detalhe_erro "$API_RESPOSTA")"
      fi
      pausa
      ;;
  esac
}
