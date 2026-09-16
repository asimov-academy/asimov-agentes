# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-16.

## Versão publicada

- `v0.3.1` em `asimov-academy/asimov-agentes` (público). `main` tem também o README.
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `ASIMOV_ATUALIZAR=1` antes do mesmo comando, ou `asimov atualizar`.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real (texto respondido pelo Chatwoot com WhatsApp) |
| 2. Áudio, imagem e documento | **Construída em v0.3.0**, falta validar em VPS real (áudio, foto de documento, PDF e reenvio do mesmo áudio) |
| 3. Handoff no Chatwoot | Não iniciada |
| 4. Menu do operador | Parcial: `asimov novo-agente` e `asimov agentes` prontos; faltam editar, remover e consumo |
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
- Para validar na VPS: `asimov atualizar`, mandar áudio, foto de documento e PDF, reenviar o mesmo áudio e conferir que não há novo Turno de `transcricao`.

## Para a fase 3

- Tools que alteram estado não existem ainda. Ao criar a primeira, turno com mídia pendente roda sem elas (exceto handoff): spec/arquitetura.md, seção de segurança.
- Arquivo acima do limite hoje só pede para o contato escrever; a spec prevê handoff.

## Fluxo de publicação combinado com o operador

1. Branch nova a partir de `main`.
2. Testes (`backend`), `shellcheck` e, se mexeu no setup, `setup/testes/simula_onboarding.sh`.
3. Commit com autor `Vitor Paim <vitor.paim@asimov.academy>` via `git -c user.name=... -c user.email=...` (a máquina não tem identidade git global).
4. PR, merge com `--delete-branch` e tag `vX.Y.Z` quando muda o setup ou o backend. Subir `VERSAO` em `setup/lib/base.sh` e o padrão em `setup/install.sh` antes da tag.
5. Dizer ao operador o comando de atualização da VPS.

## Nunca no repositório (é público)

Nome de cliente real, URL de Chatwoot de cliente, domínio ou IP da VPS de teste, tokens. Exemplos usam Loja Exemplo, agente Ana e `exemplo.com.br`.
