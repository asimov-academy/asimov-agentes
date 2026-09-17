# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-17.

## Versão publicada

- `v0.8.1` em `asimov-academy/asimov-agentes` (público): agente nativo, primeira parte da fase 5, com ajustes de ritmo, ferramentas e modelo na criação.
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `asimov atualizar` (ou `ASIMOV_ATUALIZAR=1` antes do comando de instalação).
- Verificação local na última revisão: 116 testes passando, `shellcheck` sem erro, `simula_onboarding.sh` completo no bash 3.2 e no 5, conversa no terminal testada num pty com bash 5.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real |
| 2. Áudio, imagem e documento | Concluída e validada em VPS real (v0.3.2) |
| 3. Handoff no Chatwoot | Concluída e validada em VPS real (v0.4.1) |
| 4. Menu do operador | Concluída e validada em VPS real (confirmado pelo operador em 2026-09-17) |
| 5. WhatsApp direto (oficial e WAHA) e agente nativo | **Em construção**, uma versão por parte. Nativo construído (v0.8.1), falta validar na VPS; **próxima: WAHA**, depois o oficial. Ver "Para a fase 5" abaixo |
| 6. Base de conhecimento | Não iniciada |
| 7. Polimento e distribuição | Parcial: repositório público, README, licença MIT, `install.sh` pelo GitHub; faltam backup, limpeza de mídia de 90 dias e domínio próprio do setup |

## Ambiente do operador

- VPS Hostinger com Ubuntu 24.04, acessada pelo terminal no navegador do painel da Hostinger. Esse terminal manda Enter como `\r\n` (resolvido na v0.6.3 com `descarta_pendentes`).
- Chatwoot próprio do operador (a URL nunca entra no repositório), com caixas de WhatsApp e Instagram.
- Modo revenda, com mais de uma empresa.

## O que existe hoje

### Setup e comando `asimov`

- Instalação guiada: modo de uso, domínio, e-mail do SSL, agente de código, modelo por função com provedor próprio (`MODELO_CONVERSA`, `MODELO_FALLBACK`, `MODELO_VISAO`, `MODELO_TRANSCRICAO`; openai, anthropic, gemini, groq), DNS, instalação com retomada, primeiro agente e resumo.
- Setup rodado de novo numa instalação concluída pede o que faltar de versões novas, reconstrói se o código mudou, mostra o resumo e abre o menu. `asimov atualizar` para no resumo.
- Menu (`setup/lib/menu.sh`, `asimov` sem argumento): criar agente (começa pelo canal: Chatwoot ou nativo), conversar com agente nativo (`setup/lib/conversa.sh`), listar, editar e remover agente, ver consumo e falhas (escolhe a empresa), token do Chatwoot (esquecer) e sair. Subcomandos: `novo-agente`, `conversar`, `agentes`, `editar`, `remover`, `consumo`, `handoff`, `atualizar`, `ajuda`.
- Editar agente: nome (renomeia o bot no Chatwoot também), buffer, mensagens por resposta, digitação, ferramentas (lista de marcar), modelos (inclui o do resumo do handoff) e destino do handoff.
- Tela: escolhas com setas e Enter (números como atalho), Sim/Não com setas, lista de marcar com Espaço, cada seção limpa a tela e redesenha o banner, Esc volta à tela anterior (cada ação do menu roda em `com_voltar`), pausa com Enter antes de o menu limpar o que precisa ser lido.
- Token de administrador do Chatwoot pedido uma vez por URL e guardado cifrado (`acessos/`); a API responde 428 quando falta ou foi recusado e o menu pergunta (`api_com_token` em `setup/lib/agente.sh`).

### Plataforma

- Canal nativo (`canais/nativo/`): sem conexão nem webhook; rotas `POST` e `GET .../terminal` em `canais/nativo/rotas.py`; envio, digitando e humano conduzindo no Redis (`memoria.py`); a leitura diz se o turno ainda está em andamento. Handoff mostra motivo, resumo e código no terminal e `/retomar` usa a retomada do operador.
- Canal Chatwoot (`canais/chatwoot/`): cria o Agent Bot e confere na caixa que ele ficou ligado; aceita evento de qualquer caixa em que o bot esteja ligado (a assinatura prova o bot).
- Turno (`conversas/turno.py`): buffer por conversa, lock de 240 s, mídia antes do modelo, resposta descartada se chegar mensagem nova antes do envio, digitando com o tempo de uma pessoa digitar (6 caracteres/s, variação de 15%, teto de 20 s por mensagem, soma até 90 s; editável por agente).
- Mídia: transcrição, visão e PDF com texto, cache por cliente e hash, limites de 20 MB e 5 minutos.
- Handoff no Chatwoot: nota privada curta, atribuição, status aberto; retomada pelo status pendente; falha do modelo e arquivo grande também transferem. Retomada pelo operador existe na API (`POST .../conversas/{id}/retomar`), sem opção no menu.
- Ferramentas por agente (`ia/ferramentas.py`): calculadora (sem `eval`) e busca na web (`WebSearch` da PydanticAI: nativa do provedor, DuckDuckGo quando o modelo não tem), ligadas por padrão. OpenAI pela `OpenAIResponsesModel`; Groq sem busca nativa fora dos modelos `compound`.
- Consumo por agente e empresa (`GET /admin/consumo`), falhas registradas, log `webhook_ignorado` com motivo em nível info.
- Exclusão lógica de agente (apaga o bot no Chatwoot, invalida o webhook, apaga credenciais, libera o slug) e de empresa sem agentes.
- Migrações até `0007` (acesso ao canal; digitação e ferramentas do agente).

## Pendências conhecidas

- v0.8.1 não conferida na VPS (na v0.8.0 o operador criou e conversou, mas lento pelo ritmo padrão): criar agente nativo pelo menu com ritmo rápido e conversar com digitando, ferramentas, consumo e handoff (critério 1 da fase 5).
- v0.7.0 ainda não conferida na VPS com modelo real: busca na web, calculadora e mídia depois da troca da OpenAI para a Responses.
- `INSTRUCAO_DE_MIDIA` ajustada na v0.4.0 para o agente não citar a mecânica ("recebi a transcrição"): não conferido na VPS.
- Causa de o Chatwoot não ligar o bot: era o Enter duplo escolhendo a primeira caixa (v0.6.3). Se voltar a acontecer, a criação agora falha com mensagem clara.
- Retomada pelo operador sem opção no menu para o Chatwoot (falta listar conversas em handoff); no nativo, `/retomar` na conversa.
- Web fetch (ler link) oferecido como terceira ferramenta; o operador não decidiu.

## Para a fase 5

Critério de aceite e o que entra: spec/fases.md, Fase 5. Decisão e comparação de APIs: spec/decisoes.md (2026-09-17). Ordem: **nativo (feito, v0.8.0), WAHA, WhatsApp oficial**, uma versão por parte, com validação na VPS entre elas.

O que reaproveitar:
- Contrato do canal em `canais/base.py` (`pede_acesso_do_operador`, `descobrir`, `conectar`, `desconectar`, `renomear`, `verificar`, `interpretar`, `agente_pode_falar`, `digitando`, `enviar_texto`, `valida_destino_handoff`, `transferir`, `devolver_ao_agente`, `baixar_midia`, `retoma_por_tempo`, `acesso_do_operador`, `endereco`) e registro em `canais/registro.py`. O webhook genérico `POST /webhook/{canal}/{token}` já serve para a WAHA.
- `Handoff` já tem `codigo` e `retomar_em`; falta o job `retomada_automatica` no `worker.py` (hoje só `processar_turno`).
- No menu: `com_voltar`, `api_com_token`, `escolha`, `marca`, `pergunta_numero`, `pausa`. A escolha do canal está em `fluxo_novo_agente` (`agente.sh`): WAHA e oficial entram como opções novas ali; `escolhe_agente [canal]` filtra por canal; editar monta as opções por canal (`fluxo_editar_agente`).
- `le_tecla VAR segundos` devolve `nada` sem tecla no tempo: serve para desenhar o QR code e consultar o status da sessão enquanto espera.

WAHA (conferido na documentação em 2026-09-17):
- Imagem `devlikeapro/waha` com `WHATSAPP_DEFAULT_ENGINE=GOWS` (conferir a tag para amd64 e arm e fixar a versão). Variáveis: `WAHA_API_KEY` (gerada pelo setup no `.env`), `WAHA_DISABLE_DASHBOARD`, `WAHA_DISABLE_SWAGGER`, `WHATSAPP_DOWNLOAD_MEDIA`, `WHATSAPP_FILES_LIFETIME`. Header `X-Api-Key`. Volume para as sessões.
- Sessões: `POST /api/sessions` com `{"name", "config": {"webhooks": [{"url", "events", "hmac": {"key"}, "retries"}]}}`, `POST /api/sessions/{s}/start|stop|logout`, `DELETE /api/sessions/{s}`, `GET /api/sessions/{s}` (status `STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED`, `STOPPED`), `GET /api/{s}/auth/qr?format=raw` (texto para o `qrencode` desenhar no terminal), `POST /api/{s}/auth/request-code` com `phoneNumber` (código de pareamento), `GET /api/sessions/{s}/me`.
- Webhook: eventos `message` (só recebidas) e `session.status`; corpo com `event`, `session` e `payload` (`id`, `from`, `fromMe`, `to`, `body`, `hasMedia`, `media.url`, `media.mimetype`, `media.filename`, `participant`). Assinatura `X-Webhook-Hmac` = HMAC SHA-512 do corpo cru, `X-Webhook-Hmac-Algorithm: sha512`.
- Envio: `POST /api/sendText` com `session`, `chatId`, `text` (devolve `id`); `POST /api/startTyping` e `/api/stopTyping` com `session` e `chatId`; `POST /api/sendSeen`. `chatId`: `@c.us` (número), `@lid` (id oculto), `@g.us` (grupo).
- Webhook pela rede interna do Docker (`http://api:8000/webhook/waha/{token}`), sem passar pelo Caddy. Container subido pelo setup só no primeiro agente WAHA (perfil do Compose). Setup instala `qrencode`.

O operador precisa preparar: número de WhatsApp de teste para a WAHA (chip que possa ser bloqueado), número ou grupo que recebe o handoff, app na Meta com token permanente e app secret, e pedir a aprovação do template de aviso de handoff.

## Fluxo de publicação combinado com o operador

1. Branch nova a partir de `main`.
2. Testes (`backend`), `shellcheck` e, se mexeu no setup, `setup/testes/simula_onboarding.sh`. Mudança em leitura de tecla: teste num pty com bash 5 (AGENTS.md, armadilhas).
3. Commit com autor `Vitor Paim <vitor.paim@asimov.academy>` via `git -c user.name=... -c user.email=...` (a máquina não tem identidade git global).
4. PR, merge com `--delete-branch` e tag `vX.Y.Z` quando muda o setup ou o backend (o operador autorizou fazer os três). Subir `VERSAO` em `setup/lib/base.sh` e o padrão em `setup/install.sh` antes da tag.
5. Dizer ao operador o comando de atualização da VPS (`asimov atualizar`).

## Nunca no repositório (é público)

Nome de cliente real, URL de Chatwoot de cliente, domínio ou IP da VPS de teste, tokens. Exemplos usam Loja Exemplo, agente Ana e `exemplo.com.br`.
