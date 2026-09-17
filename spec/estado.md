# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-16.

## Versão publicada

- `v0.6.3` em `asimov-academy/asimov-agentes` (público). Escolhas com setas e telas limpas desde a v0.5.1; Esc volta à tela anterior desde a v0.5.2. `main` tem também o README.
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `ASIMOV_ATUALIZAR=1` antes do mesmo comando, ou `asimov atualizar`.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real (texto respondido pelo Chatwoot com WhatsApp) |
| 2. Áudio, imagem e documento | Concluída e validada em VPS real (v0.3.2): áudio, imagem e PDF respondidos; 4 áudios seguidos numa resposta só; reenvio dos mesmos áudios sem nova transcrição |
| 3. Handoff no Chatwoot | Concluída e validada em VPS real (v0.4.1): conversa atribuída com resumo em nota privada, agente calado com a conversa Aberta, volta ao marcar Pendente |
| 4. Menu do operador | **Construída (v0.5.0)**, falta o critério de aceite numa VPS real |
| 5. WhatsApp oficial e Telegram diretos | Não iniciada |
| 6. Base de conhecimento | Não iniciada |
| 7. Polimento e distribuição | Parcial: repositório público, README, licença MIT, `install.sh` pelo GitHub; faltam backup e domínio próprio do setup |

## O que já existe além da fase 1

- Modo de uso perguntado antes de instalar: `MODO_INSTALACAO=empresa|revenda`.
- Modelo por função com provedor próprio: `MODELO_CONVERSA`, `MODELO_FALLBACK`, `MODELO_VISAO`, `MODELO_TRANSCRICAO` (openai, anthropic, gemini, groq). Fallback com `FallbackModel`. Visão e transcrição usadas desde a v0.3.0.
- Setup cria o Agent Bot no Chatwoot com o token de administrador (pedido uma vez e guardado cifrado desde a v0.6.0) e opera com o token do bot.
- Setup rodado de novo numa instalação concluída pede o que faltar de versões novas e reconstrói.

## Como a fase 2 ficou

- Webhook grava o anexo na Mensagem (uma por anexo) e agenda o turno; nada é baixado ali.
- No turno, `midia/servico.py` baixa pelo canal (`baixar_midia`), usa o cache por `cliente_id` + hash ou lê, e grava a `situacao` no anexo. O modelo recebe o conteúdo em `<midia_do_contato>`.
- Leitura de mídia registra Turno com `funcao` `transcricao` ou `visao`; mídia do cache não registra.
- Arquivos em volume Docker `midia` (`/var/lib/asimov/midia`). Retenção de 90 dias fica para a fase 7.
- Validada na VPS em 2026-09-16. O teste achou a mensagem perdida durante o turno, corrigida na v0.3.2 (spec/decisoes.md).
- O agente às vezes citava a mecânica ("recebi as transcrições"): `INSTRUCAO_DE_MIDIA` ajustada na v0.4.0; ainda não conferido na VPS.

## Como a fase 3 ficou

- Tool `transferir_para_humano` só registra o pedido em `ContextoTurno` (`ia/contexto.py`); `handoff/servico.py` transfere no fim do turno, depois do envio. Chatwoot: nota privada, atribuição, status aberto.
- Retomada: `conversation_status_changed`/`conversation_updated` com mudança de status para pendente, e o turno fecha handoff esquecido quando o Chatwoot já está pendente.
- Falha do modelo depois das tentativas e arquivo acima do limite também transferem.
- Destino por agente: usuário, time ou caixa. `asimov handoff` troca; a atualização pergunta uma vez para agentes antigos. `PATCH` do agente aceita só `handoff_destino` por enquanto.
- Ainda sem tool que altera estado além do handoff: a regra de turno com mídia continua sem efeito prático.
- Validada na VPS em 2026-09-16. O teste achou a nota longa demais, encurtada na v0.4.1 (spec/decisoes.md). O debug confirmou a retomada pelo evento do Chatwoot (log `handoff_retomado` no `api`), nenhuma Falha e um handoff aberto por conversa.
- Prompt de resumo de agente já criado não muda com atualização: o setup nunca sobrescreve prompt.

## Como a fase 4 ficou

- Menu em `setup/lib/menu.sh`: abre ao rodar o setup de novo e com `asimov`; subcomandos `editar`, `remover`, `consumo`. Seleção de agente em `escolhe_agente` (`agente.sh`).
- API: `PATCH` do agente com nome, buffer, mensagens, modelos (inclui `modelo_auxiliar`), destino e retomada; `DELETE` de agente (com token opcional para apagar o bot) e de empresa sem agentes; `GET /admin/consumo`; `POST .../conversas/{id}/retomar` (sem opção no menu).
- Contrato do canal ganhou `retoma_por_tempo` e `devolver_ao_agente`; `desconectar` do Chatwoot usa só o token de administrador.
- Log `handoff_retomado` do webhook agora sai com `conversa_id`.
- Decisões em spec/decisoes.md (2026-09-16, fase 4).

## Para validar a fase 4 na VPS

1. `asimov atualizar`, depois `bash ~/asimov-agentes/setup/instalar.sh`: resumo e menu aparecem.
2. Segundo cliente: no Chatwoot, uma segunda caixa (o setup cria o bot). Menu > Criar agente > nova empresa. Mandar mensagem nas duas caixas e conferir que cada agente responde só na sua.
3. Menu > Editar > Tempo de buffer (ex.: 20 s) e conferir a espera na próxima mensagem.
4. Menu > Editar > Modelos > Resumo do handoff com um modelo barato; forçar um handoff e ver o Turno `resumo_handoff` no consumo.
5. Menu > Remover: o bot some da caixa e o agente não responde mais, sem pedir o token de novo.
6. Menu > Ver consumo e falhas: totais de 7 e 30 dias por empresa.

## Fluxo de publicação combinado com o operador

1. Branch nova a partir de `main`.
2. Testes (`backend`), `shellcheck` e, se mexeu no setup, `setup/testes/simula_onboarding.sh`.
3. Commit com autor `Vitor Paim <vitor.paim@asimov.academy>` via `git -c user.name=... -c user.email=...` (a máquina não tem identidade git global).
4. PR, merge com `--delete-branch` e tag `vX.Y.Z` quando muda o setup ou o backend. Subir `VERSAO` em `setup/lib/base.sh` e o padrão em `setup/install.sh` antes da tag.
5. Dizer ao operador o comando de atualização da VPS.

## Nunca no repositório (é público)

Nome de cliente real, URL de Chatwoot de cliente, domínio ou IP da VPS de teste, tokens. Exemplos usam Loja Exemplo, agente Ana e `exemplo.com.br`.
