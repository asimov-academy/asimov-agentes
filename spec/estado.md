# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-16.

## Versão publicada

- `v0.4.1` em `asimov-academy/asimov-agentes` (público). `main` tem também o README.
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `ASIMOV_ATUALIZAR=1` antes do mesmo comando, ou `asimov atualizar`.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real (texto respondido pelo Chatwoot com WhatsApp) |
| 2. Áudio, imagem e documento | Concluída e validada em VPS real (v0.3.2): áudio, imagem e PDF respondidos; 4 áudios seguidos numa resposta só; reenvio dos mesmos áudios sem nova transcrição |
| 3. Handoff no Chatwoot | Concluída e validada em VPS real (v0.4.1): conversa atribuída com resumo em nota privada, agente calado com a conversa Aberta, volta ao marcar Pendente |
| 4. Menu do operador | **Próxima**. Parcial: `asimov novo-agente` e `asimov agentes` prontos; faltam editar, remover e consumo |
| 5. WhatsApp oficial e Telegram diretos | Não iniciada |
| 6. Base de conhecimento | Não iniciada |
| 7. Polimento e distribuição | Parcial: repositório público, README, licença MIT, `install.sh` pelo GitHub; faltam backup e domínio próprio do setup |

## O que já existe além da fase 1

- Modo de uso perguntado antes de instalar: `MODO_INSTALACAO=empresa|revenda`.
- Modelo por função com provedor próprio: `MODELO_CONVERSA`, `MODELO_FALLBACK`, `MODELO_VISAO`, `MODELO_TRANSCRICAO` (openai, anthropic, gemini, groq). Fallback com `FallbackModel`. Visão e transcrição usadas desde a v0.3.0.
- Setup cria o Agent Bot no Chatwoot com token de administrador (não guardado) e opera com o token do bot.
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

## Para a fase 4

- `PATCH` do agente já existe só com `handoff_destino`; completar com os demais campos.
- A pergunta de handoff da atualização pede o token uma vez por agente sem destino; no menu, pedir uma vez por Chatwoot.
- Teste de dois clientes precisa de um segundo Agent Bot e uma segunda caixa no Chatwoot.
- `modelo_auxiliar` hoje é igual ao `modelo_conversa` (padrão em `ia/provedores.py`): no teste, o resumo com `gpt-5.5` custou cerca de US$ 0,0125 e 3,5 s por handoff. Permitir escolher um modelo mais barato no editar agente ou no setup.
- Log `handoff_retomado` do webhook sai sem `conversa_id` (`conversas/webhook.py`, `_retoma`); os do worker têm.

## Fluxo de publicação combinado com o operador

1. Branch nova a partir de `main`.
2. Testes (`backend`), `shellcheck` e, se mexeu no setup, `setup/testes/simula_onboarding.sh`.
3. Commit com autor `Vitor Paim <vitor.paim@asimov.academy>` via `git -c user.name=... -c user.email=...` (a máquina não tem identidade git global).
4. PR, merge com `--delete-branch` e tag `vX.Y.Z` quando muda o setup ou o backend. Subir `VERSAO` em `setup/lib/base.sh` e o padrão em `setup/install.sh` antes da tag.
5. Dizer ao operador o comando de atualização da VPS.

## Nunca no repositório (é público)

Nome de cliente real, URL de Chatwoot de cliente, domínio ou IP da VPS de teste, tokens. Exemplos usam Loja Exemplo, agente Ana e `exemplo.com.br`.
