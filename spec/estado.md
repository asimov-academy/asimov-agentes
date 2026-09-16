# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-16.

## Versão publicada

- `v0.2.0` em `asimov-academy/asimov-agentes` (público). `main` tem também o README.
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `ASIMOV_ATUALIZAR=1` antes do mesmo comando, ou `asimov atualizar`.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real (texto respondido pelo Chatwoot com WhatsApp) |
| 2. Áudio, imagem e documento | **Próxima.** Hoje mensagem só com anexo é gravada como `anexo sem texto` e não gera turno |
| 3. Handoff no Chatwoot | Não iniciada |
| 4. Menu do operador | Parcial: `asimov novo-agente` e `asimov agentes` prontos; faltam editar, remover e consumo |
| 5. WhatsApp oficial e Telegram diretos | Não iniciada |
| 6. Base de conhecimento | Não iniciada |
| 7. Polimento e distribuição | Parcial: repositório público, README, licença MIT, `install.sh` pelo GitHub; faltam backup e domínio próprio do setup |

## O que já existe além da fase 1

- Modo de uso perguntado antes de instalar: `MODO_INSTALACAO=empresa|revenda`.
- Modelo por função com provedor próprio: `MODELO_CONVERSA`, `MODELO_FALLBACK`, `MODELO_VISAO`, `MODELO_TRANSCRICAO` (openai, anthropic, gemini, groq). Fallback com `FallbackModel`. Visão e transcrição estão configuradas mas ainda não são usadas: é a fase 2.
- Setup cria o Agent Bot no Chatwoot com token de administrador (não guardado) e opera com o token do bot.
- Setup rodado de novo numa instalação concluída pede o que faltar de versões novas e reconstrói.

## Para a fase 2

- Anexo chega no payload do Chatwoot em `attachments[]` (`file_type`, `data_url`); hoje `canais/chatwoot/canal.py` só usa `file_type` para o `tipo`.
- Download do anexo precisa entrar no contrato do canal (`canais/base.py`), não direto no turno.
- Transcrição por provedor: OpenAI e Groq têm endpoint de áudio (não é chat); Gemini recebe áudio no próprio modelo. Visão entra como conteúdo multimodal na PydanticAI.
- Entidade Mídia e cache por `cliente_id` + hash estão em spec/dados.md. Criar migração nova.
- Atualizar este arquivo, spec/fases.md e o README (seção "O que vem por aí") ao terminar.

## Fluxo de publicação combinado com o operador

1. Branch nova a partir de `main`.
2. Testes (`backend`), `shellcheck` e, se mexeu no setup, `setup/testes/simula_onboarding.sh`.
3. Commit com autor `Vitor Paim <vitor.paim@asimov.academy>` via `git -c user.name=... -c user.email=...` (a máquina não tem identidade git global).
4. PR, merge com `--delete-branch` e tag `vX.Y.Z` quando muda o setup ou o backend. Subir `VERSAO` em `setup/lib/base.sh` e o padrão em `setup/install.sh` antes da tag.
5. Dizer ao operador o comando de atualização da VPS.

## Nunca no repositório (é público)

Nome de cliente real, URL de Chatwoot de cliente, domínio ou IP da VPS de teste, tokens. Exemplos usam Loja Exemplo, agente Ana e `exemplo.com.br`.
