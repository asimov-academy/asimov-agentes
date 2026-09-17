#!/usr/bin/env bash
# Tela 8, Conversar com agente: o operador é o contato de um agente nativo, aqui no terminal.
# A mensagem vai pela API, que grava e agenda o buffer; a resposta chega pelo worker e o terminal
# consulta a API a cada segundo enquanto espera.

# Máximo de espera por uma resposta: buffer, mídia, modelo e digitando cabem com folga.
CONVERSA_ESPERA_MAXIMA=300

fluxo_conversar() {
  secao "Conversar com agente"
  if ! escolhe_agente nativo; then
    dica "O agente nativo não tem canal: em Criar agente, escolha Nativo."
    pausa
    return 0
  fi
  conversa_no_terminal
}

# conversa_no_terminal: conversa com o AGENTE escolhido até Esc ou /sair.
conversa_no_terminal() {
  local nome caminho cliente_id buffer tecla
  nome=$(jq -r .nome <<<"$AGENTE")
  cliente_id=$(jq -r .cliente_id <<<"$AGENTE")
  buffer=$(jq -r .buffer_segundos <<<"$AGENTE")
  caminho="$(caminho_do_agente "$AGENTE")/terminal"
  CONVERSA="" CONVERSA_ID="" PROXIMA=0 DIGITANDO=0 ESPERANDO=0 ENVIADA_EM=0 RECEBEU=0 HANDOFF_VISTO=""
  INDICADOR=0 DIGITADO="" CONSULTOU_EM=-1

  secao "Conversa com $nome"
  dica "Cada linha é uma mensagem. O agente espera ${buffer} s depois da última antes de responder."
  dica "/nova começa outra conversa · /retomar devolve ao agente depois do handoff"
  dica "/sair ou Esc volta"
  echo

  if ! tem_terminal; then
    _conversa_por_linha
    return 0
  fi

  descarta_pendentes
  _conversa_prompt
  while true; do
    le_tecla tecla 1
    case "$tecla" in
      nada) ;;
      enter)
        printf '\n'
        _conversa_linha "$DIGITADO" || return 0
        DIGITADO=""
        _conversa_prompt
        ;;
      esc)
        printf '\r\033[K'
        volta_se_puder
        return 0
        ;;
      apagar)
        if [ -n "$DIGITADO" ]; then
          DIGITADO=${DIGITADO%?}
          printf '\b \b'
        fi
        ;;
      ?)
        DIGITADO+=$tecla
        printf '%s' "$tecla"
        ;;
    esac
    # Uma consulta por segundo: digitando rápido não pode esperar a API a cada tecla.
    if [ "$ESPERANDO" = 1 ] && [ "$SECONDS" != "$CONSULTOU_EM" ]; then
      CONSULTOU_EM=$SECONDS
      _conversa_consulta
    fi
  done
}

_conversa_prompt() {
  printf '\r\033[K'
  _prompt "Você"
  printf ': %s' "$DIGITADO"
}

# Sem terminal (simulação com arquivo de respostas): lê uma linha e espera a resposta inteira.
_conversa_por_linha() {
  local linha
  while true; do
    _prompt "Você"
    printf ': '
    linha=""
    ler linha
    echo
    _conversa_linha "$linha" || return 0
    while [ "$ESPERANDO" = 1 ]; do
      _conversa_consulta
      [ "$ESPERANDO" = 1 ] && sleep 1
    done
  done
}

# _conversa_linha TEXTO: comando ou mensagem. Devolve 1 para sair da conversa.
_conversa_linha() {
  local texto corpo
  texto=$(printf '%s' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  case "$texto" in
    "") return 0 ;;
    /sair) return 1 ;;
    /nova)
      CONVERSA="" CONVERSA_ID="" PROXIMA=0 ESPERANDO=0 HANDOFF_VISTO=""
      _conversa_mostra "$(dica "Conversa nova: o agente não lembra da anterior.")"
      return 0
      ;;
    /retomar)
      if [ -z "$CONVERSA_ID" ]; then
        _conversa_mostra "$(dica "Nenhuma conversa ainda.")"
        return 0
      fi
      api POST "/admin/clientes/$cliente_id/conversas/$CONVERSA_ID/retomar"
      if [ "$API_STATUS" != 200 ]; then
        _conversa_mostra "$(falha "$(detalhe_erro "$API_RESPOSTA")")"
      elif [ "$(jq -r .retomado <<<"$API_RESPOSTA")" = true ]; then
        HANDOFF_VISTO=""
        _conversa_mostra "$(ok "O agente voltou a responder nesta conversa.")"
      else
        _conversa_mostra "$(dica "A conversa não estava com humano.")"
      fi
      return 0
      ;;
  esac

  corpo=$(jq -n --arg texto "$texto" --arg conversa "$CONVERSA" '{texto: $texto} + (if $conversa == "" then {} else {conversa: $conversa} end)')
  api POST "$caminho" "$corpo"
  if [ "$API_STATUS" != 200 ]; then
    _conversa_mostra "$(falha "$(detalhe_erro "$API_RESPOSTA")")"
    return 0
  fi
  CONVERSA=$(jq -r .conversa <<<"$API_RESPOSTA")
  CONVERSA_ID=$(jq -r .conversa_id <<<"$API_RESPOSTA")
  if [ "$(jq -r .agendada <<<"$API_RESPOSTA")" != true ]; then
    _conversa_mostra "$(aviso "A conversa está com humano e o agente não responde. /retomar devolve a conversa ao agente.")"
    return 0
  fi
  ESPERANDO=1 RECEBEU=0 ENVIADA_EM=$SECONDS
}

# _conversa_mostra TEXTO: escreve acima da linha que está sendo digitada, sem perder o que já foi digitado.
_conversa_mostra() {
  printf '\r\033[K'
  if [ "$INDICADOR" = 1 ]; then
    printf '\033[1A\r\033[K'
    INDICADOR=0
  fi
  [ -n "$1" ] && printf '%s\n' "$1"
  if [ "$DIGITANDO" = 1 ]; then
    printf '  %s%s está digitando…%s\n' "$CINZA" "$nome" "$NORMAL"
    INDICADOR=1
  fi
  tem_terminal && _conversa_prompt
  return 0
}

# _conversa_consulta: mensagens novas do agente, digitando e handoff. Para de esperar quando o agente
# respondeu e o turno terminou (o handoff chega depois da última mensagem), ou passou do tempo máximo.
_conversa_consulta() {
  local saida="" digitando handoff codigo
  api GET "$caminho/$CONVERSA?depois=$PROXIMA"
  if [ "$API_STATUS" != 200 ]; then
    ESPERANDO=0
    _conversa_mostra "$(falha "$(detalhe_erro "$API_RESPOSTA")")"
    return 0
  fi
  if [ "$(jq '.mensagens | length' <<<"$API_RESPOSTA")" -gt 0 ]; then
    RECEBEU=1
    saida=$(jq -r --arg nome "$nome" --arg ciano "$CIANO$NEGRITO" --arg normal "$NORMAL" \
      '.mensagens[] | "  \($ciano)\($nome):\($normal) \(.texto | gsub("\n"; "\n    "))"' <<<"$API_RESPOSTA")
    PROXIMA=$(jq -r .proxima <<<"$API_RESPOSTA")
  fi
  digitando=$([ "$(jq -r .digitando <<<"$API_RESPOSTA")" = true ] && echo 1 || echo 0)

  handoff=$(jq -c .handoff <<<"$API_RESPOSTA")
  codigo=$(jq -r '.handoff.codigo // ""' <<<"$API_RESPOSTA")
  if [ -n "$codigo" ] && [ "$codigo" != "$HANDOFF_VISTO" ]; then
    HANDOFF_VISTO=$codigo
    saida+="${saida:+$'\n'}$(aviso "Conversa passada para humano · código $(destaque "$codigo")")"
    saida+=$'\n'$(dica "Motivo: $(jq -r .motivo <<<"$handoff")")
    saida+=$'\n'$(jq -r '.resumo' <<<"$handoff" | sed "s/^/  $CINZA/; s/\$/$NORMAL/")
    saida+=$'\n'$(dica "O agente fica calado nesta conversa. /retomar devolve a conversa ao agente.")
  fi

  if [ -n "$saida" ] || [ "$digitando" != "$DIGITANDO" ]; then
    DIGITANDO=$digitando
    _conversa_mostra "$saida"
  fi
  if [ "$RECEBEU" = 1 ] && [ "$DIGITANDO" = 0 ] && [ "$(jq -r .respondendo <<<"$API_RESPOSTA")" != true ]; then
    ESPERANDO=0
  elif [ $((SECONDS - ENVIADA_EM)) -ge "$CONVERSA_ESPERA_MAXIMA" ]; then
    ESPERANDO=0
    _conversa_mostra "$(aviso "Sem resposta em $((CONVERSA_ESPERA_MAXIMA / 60)) minutos. Veja em Ver consumo e falhas.")"
  fi
}
