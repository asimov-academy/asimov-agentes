# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-17.

## Versão publicada

- `v0.13.3` em `asimov-academy/asimov-agentes` (público): o log do webhook passa a dizer de qual conversa é cada mensagem aceita ou ignorada.
- `v0.13.2`: o aviso de handoff passa a chamar o contato por nome e telefone de verdade (antes mostrava o id oculto como se fosse número), e o `/retomar` funciona quando o destino escreve por trás de um `@lid`.
- `v0.13.1`: o arquivo de áudio, imagem e documento sai do disco na limpeza diária (um a dois dias depois de lido); o texto lido dele fica.
- `v0.12.3`: áudio, imagem e PDF voltam a ser lidos (o arquivo era anunciado em `localhost`, que no contêiner do worker é o próprio worker), e pedir QR code novo deixou de disparar alarme de número fora do ar.
- `v0.12.2`: o aparelho conectado aparece no celular como `Agente (Empresa)`, em vez de "Ubuntu Firefox".
- `v0.12.1`: o id do número do handoff passa a ser o que o próprio WhatsApp devolve (nono dígito, `@lid`), conferido na escolha e corrigido no envio.
- `v0.12.0`: número desconectado do WhatsApp vira falha visível e aviso no menu, pelo evento da WAHA e por uma ronda de dez em dez minutos.
- `v0.11.2`: áudio e imagem voltam a ser baixados da WAHA (o `Accept: application/json` do QR code tinha ido parar no download do arquivo).
- `v0.11.1`: contato que chega por `@lid` (número escondido pelo WhatsApp) passa a ser reconhecido pelo telefone de verdade, o nono dígito deixou de separar o mesmo número, e contato barrado pela lista vira falha visível.
- `v0.11.0`: no Chatwoot, atendente que responde fica com a conversa (aberta e atribuída a ele) e o agente volta sozinho no prazo do onboarding, com a conversa de volta para Pendente e sem atribuição.
- `v0.10.0`: no WhatsApp, responder pelo aparelho cala o agente na hora (handoff sem IA e sem aviso, com o prazo do agente) e reagir com 👍 na conversa o traz de volta. O que a equipe respondeu entra na memória do agente marcado como fala de atendente, em todo canal que tem atendente.
- `v0.9.3`: destino do handoff da WAHA em dois passos (número ou grupo), com busca pelo nome do grupo.
- `v0.9.2`: o agente pode atender só os números listados (`contatos_permitidos`), escolhido na criação e em Editar agente; grupos continuam sempre ignorados.
- `v0.9.1`: aviso de API não oficial com confirmação antes de parear, correção do fluxo que voltava ao menu quando o systemd recusava o timer, e nomes dos passos da instalação do WhatsApp.
- `v0.9.0`: **WhatsApp direto pela WAHA**, segunda parte da fase 5. A WAHA sobe sob demanda (perfil do Compose, no primeiro agente WhatsApp), o número é pareado por QR code no terminal, o handoff avisa um número ou grupo com resumo e código, e a conversa volta com `/retomar <código>` ou sozinha pelo prazo do agente.
- `v0.8.11`: agente nativo, primeira parte da fase 5, com ajustes na criação, conexão posterior a um canal, feedback de etapa e turno na conversa, busca na web com instrução de uso e raciocínio baixo, handoff no histórico do modelo, teto de chamadas por turno, calculadora completa no formato brasileiro, uma ferramenta por arquivo, resposta no formato estruturado nativo, mensagem sem markdown, data de Brasília no turno e agente que nasce cru (sem ferramentas marcadas e prompt de uma linha).
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `asimov atualizar` (ou `ASIMOV_ATUALIZAR=1` antes do comando de instalação).
- Verificação local na última revisão: 194 testes passando, `shellcheck` sem erro, `simula_onboarding.sh` completo (inclui o fluxo do WhatsApp), conversa no terminal testada num pty com bash 5.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real |
| 2. Áudio, imagem e documento | Concluída e validada em VPS real (v0.3.2) |
| 3. Handoff no Chatwoot | Concluída e validada em VPS real (v0.4.1) |
| 4. Menu do operador | Concluída e validada em VPS real (confirmado pelo operador em 2026-09-17) |
| 5. WhatsApp direto (oficial e WAHA) e agente nativo | **Em construção**, uma versão por parte. Parte 1 (agente nativo) concluída e validada em VPS real na v0.8.11. **Parte 2 (WAHA) construída na v0.9.0, aguardando o critério de aceite numa VPS real.** Próxima: WhatsApp oficial. Ver "Para a fase 5" abaixo |
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
- Menu (`setup/lib/menu.sh`, `asimov` sem argumento): criar agente (começa pelo canal: Chatwoot, WhatsApp pela WAHA ou nativo), conversar com agente nativo (`setup/lib/conversa.sh`), listar, editar e remover agente, ver consumo e falhas (escolhe a empresa), token do Chatwoot (esquecer) e sair. Subcomandos: `novo-agente`, `conversar`, `agentes`, `editar`, `remover`, `consumo`, `handoff`, `atualizar`, `ajuda`.
- Editar agente: nome (renomeia o bot no Chatwoot também), buffer, mensagens por resposta, digitação, ferramentas (lista de marcar), modelos (inclui o do resumo do handoff) e, conforme o canal, destino do handoff, "Conectar a um canal" (nativo) ou "WhatsApp" (WAHA: número pareado, destino e horas até voltar sozinho).
- WhatsApp pela WAHA (`setup/lib/waha.sh`, v0.9.0): o contêiner sobe na primeira vez que o operador escolhe o canal (`garante_waha`), o QR code é desenhado com `qrencode` até o número parear e o destino do handoff é escolhido depois (número digitado ou grupo do próprio número). A imagem se atualiza sozinha: `asimov-waha.timer` (domingo de madrugada) roda `deploy/atualiza_waha.sh`, que volta para a versão anterior se algum número não reconectar em 2 minutos e deixa o aviso no menu. Item "WhatsApp (WAHA)" no menu: versão, última conferida, ligar ou desligar a automática e procurar versão nova agora.
- Tela: escolhas com setas e Enter (números como atalho), Sim/Não com setas, lista de marcar com Espaço, cada seção limpa a tela e redesenha o banner, Esc volta à tela anterior (cada ação do menu roda em `com_voltar`), pausa com Enter antes de o menu limpar o que precisa ser lido.
- Token de administrador do Chatwoot pedido uma vez por URL e guardado cifrado (`acessos/`); a API responde 428 quando falta ou foi recusado e o menu pergunta (`api_com_token` em `setup/lib/agente.sh`).

### Plataforma

- Canal WAHA (`canais/waha/`, v0.9.0): uma sessão por agente com webhook interno assinado (HMAC SHA-512), QR code lido pelo setup (`GET .../waha`, `POST .../waha/reiniciar`, `GET .../waha/grupos`), envio, digitando e marcar como lida, download de mídia com a chave da instalação, remoção com logout. Ignora grupos (menos o do handoff) e sessão de outro agente; o que sai do número é lido pelo `source` (`api` é o agente, `app` é gente no aparelho, que pausa o agente). Sessão que sai do ar (`session.status` e ronda `confere_whatsapp`) vira falha e aviso no menu. Handoff: pausa pelo status da conversa, aviso ao número ou grupo com resumo e código, `/retomar <código>` só do destino, job `retomada_automatica` no worker (cron de um minuto) e aviso de que o agente voltou.
- Conversa de teste no terminal para agente de qualquer canal (`Conversa.canal` nativo; `canal_da_conversa`). Agente nativo pode ser conectado depois a um canal externo (`POST .../canal`: Chatwoot ou WAHA).
- Canal nativo (`canais/nativo/`): sem conexão nem webhook; rotas `POST` e `GET .../terminal` em `canais/nativo/rotas.py`; envio, digitando e humano conduzindo no Redis (`memoria.py`); a leitura diz se o turno ainda está em andamento. Handoff mostra motivo, resumo e código no terminal e `/retomar` usa a retomada do operador.
- Canal Chatwoot (`canais/chatwoot/`): cria o Agent Bot e confere na caixa que ele ficou ligado; aceita evento de qualquer caixa em que o bot esteja ligado (a assinatura prova o bot).
- Turno (`conversas/turno.py`): buffer por conversa, lock de 240 s, mídia antes do modelo, resposta descartada se chegar mensagem nova antes do envio, digitando com o tempo de uma pessoa digitar (6 caracteres/s, variação de 15%, teto de 20 s por mensagem, soma até 90 s; editável por agente).
- Mídia: transcrição, visão e PDF com texto, cache por cliente e hash, limites de 20 MB e 5 minutos. O arquivo sai do disco na limpeza diária, um dia depois de lido (`limpar_midia`); o texto lido fica com a conversa.
- Handoff no Chatwoot: nota privada curta, atribuição, status aberto; retomada pelo status pendente ou pelo prazo do agente (que devolve para pendente e desatribui); atendente que responde por lá pausa o agente e fica com a conversa; falha do modelo e arquivo grande também transferem. Retomada pelo operador existe na API (`POST .../conversas/{id}/retomar`), sem opção no menu.
- Ferramentas por agente, uma por arquivo em `ia/ferramentas/` (ficha em `base.py`, catálogo em `registro.py`): calculadora (`ia/ferramentas/calculadora.py`, sem `eval`, formato brasileiro, funções de porcentagem, parcela, juros e datas) e busca na web (`WebSearch` da PydanticAI: nativa do provedor, DuckDuckGo quando o modelo não tem), escolhidas na criação (nenhuma por padrão desde a v0.8.11). OpenAI pela `OpenAIResponsesModel`; Groq sem busca nativa fora dos modelos `compound`.
- Consumo por agente e empresa (`GET /admin/consumo`), falhas registradas, log `webhook_ignorado` com motivo em nível info.
- Exclusão lógica de agente (apaga o bot no Chatwoot, invalida o webhook, apaga credenciais, libera o slug) e de empresa sem agentes.
- Migrações até `0011` (canal da conversa; agente novo sem ferramentas; contatos permitidos; arquivo de mídia apagado).

## Pendências conhecidas

- Teste de ponta a ponta na VPS (2026-09-17, agente Spencer, VPS reinstalada do zero): instalação, pareamento e conversa de texto funcionando. Barrado antes pelo `@lid` (v0.11.1) e áudio não baixado (v0.11.2). Falta conferir áudio e imagem depois da correção, handoff, `/retomar`, joinha, pausa por resposta pelo aparelho e remoção.
- **Parte 2 (WAHA) ainda não rodou inteira numa VPS**: falta parear um número de verdade, conferir texto, áudio e imagem, o aviso de handoff e o `/retomar`, a remoção tirando o aparelho da lista do WhatsApp e o timer de atualização (`systemctl list-timers asimov-waha.timer`). O que o operador precisa: um chip de teste que possa ser bloqueado e o número ou grupo que recebe o handoff.
- Da parte 1, não conferido na VPS depois das correções: contas pela calculadora nova (v0.8.7: ponto de milhar, porcentagem, parcela, datas), citação da busca sem markdown (v0.8.10) e `/retomar` no terminal. Cobertos por teste automatizado.
- Mídia (visão e PDF) na OpenAI Responses ainda não conferida na VPS.
- Uma mensagem digitada no terminal da VPS chegou como "Ol�a" (byte inválido antes do "a"). Suspeita: apagar uma letra acentuada; não reproduzido local com bash 5.
- `INSTRUCAO_DE_MIDIA` ajustada na v0.4.0 para o agente não citar a mecânica ("recebi a transcrição"): não conferido na VPS.
- Causa de o Chatwoot não ligar o bot: era o Enter duplo escolhendo a primeira caixa (v0.6.3). Se voltar a acontecer, a criação agora falha com mensagem clara.
- Retomada pelo operador sem opção no menu para o Chatwoot (falta listar conversas em handoff); no nativo, `/retomar` na conversa.
- Web fetch (ler link) oferecido como terceira ferramenta; o operador não decidiu.

## Para a fase 5

Critério de aceite e o que entra: spec/fases.md, Fase 5. Decisão e comparação de APIs: spec/decisoes.md (2026-09-17). Ordem: **nativo (feito, v0.8.0 a v0.8.11), WAHA (construída, v0.9.0), WhatsApp oficial**, uma versão por parte, com validação na VPS entre elas.

Validado na VPS na parte 1 (2026-09-17): conversa no terminal com ritmo rápido e etapas; nativo conectado ao Chatwoot com as conversas de teste separadas; handoff e devolução no Chatwoot; busca na web usada quando precisa (v0.8.5) e sem o erro de JSON (v0.8.9); data do dia respondida sem ferramenta (v0.8.10); agente novo cru, sem ferramentas e com prompt de uma linha, gastando uns 550 tokens por turno contra uns 5.600 com busca ligada (v0.8.11).

O que reaproveitar:
- WAHA e oficial entram também em "Conectar a um canal" (`conecta_canal` em `menu.sh`, hoje fixo no Chatwoot) e precisam de `externo = True`.
- Contrato do canal em `canais/base.py` (`pede_acesso_do_operador`, `descobrir`, `conectar`, `desconectar`, `renomear`, `verificar`, `interpretar`, `agente_pode_falar`, `digitando`, `enviar_texto`, `valida_destino_handoff`, `transferir`, `devolver_ao_agente`, `baixar_midia`, `retoma_por_tempo`, `acesso_do_operador`, `endereco`) e registro em `canais/registro.py`. O webhook genérico `POST /webhook/{canal}/{token}` já serve para a WAHA.
- `Handoff` já tem `codigo` e `retomar_em`; falta o job `retomada_automatica` no `worker.py` (hoje só `processar_turno`).
- No menu: `com_voltar`, `api_com_token`, `escolha`, `marca`, `pergunta_numero`, `pausa`. A escolha do canal está em `fluxo_novo_agente` (`agente.sh`): WAHA e oficial entram como opções novas ali; `escolhe_agente [canal]` filtra por canal; editar monta as opções por canal (`fluxo_editar_agente`).
- `le_tecla VAR segundos` devolve `nada` sem tecla no tempo: serve para desenhar o QR code e consultar o status da sessão enquanto espera.

WAHA (construída na v0.9.0; conferido na documentação em 2026-09-17):
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
