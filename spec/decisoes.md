# Decisões

Log de mudanças na spec. Cada entrada: data, o que mudou, por quê e quais arquivos de `spec/` foram atualizados. Entrada mais nova no topo.

## 2026-09-17: Digitação humanizada, ferramentas por agente e consumo por empresa (v0.7.0)

- **Digitando pelo ritmo de uma pessoa**, pedido do operador: caracteres / velocidade do agente (padrão 6 por segundo, editável de 1 a 30), variação de 15%, entre 1 s e o teto por mensagem (padrão 20 s). O tempo que o turno já levou (mídia, modelo) conta como digitação da primeira mensagem. A soma fica em até 90 s, abaixo do lock de 240 s que também cobre mídia e modelo. Substitui o atraso fixo de 1 a 4 s. spec/dados.md, spec/arquitetura.md.
- **Ferramentas por agente** (`Agente.ferramentas`, catálogo em `ia/ferramentas.py`), lista de marcar no menu, com calculadora e busca na web por padrão, inclusive nos agentes existentes (padrão da migração). `transferir_para_humano` continua em todo agente, fora da lista.
- **Calculadora sem `eval`**: árvore sintática com números, operadores e parênteses; expoente até 100.
- **Busca na web: nativa do provedor, com DuckDuckGo quando o modelo não tem**, decisão do operador (ele também citou Firecrawl instalado na VPS: pesado para 4 GB junto do resto; SearXNG fica como opção futura de busca própria). Capability `WebSearch` da PydanticAI escolhe por modelo, inclusive dentro do fallback. OpenAI passou para `OpenAIResponsesModel` (só nela há busca nativa). O perfil da Groq anuncia busca nativa em todo modelo, mas só os `compound` têm: nos outros o setup tira do perfil para cair na local. Busca nativa cobra por uso na conta do provedor.
- **Consumo pergunta a empresa** (ou todas) quando há mais de uma. spec/telas.md.

## 2026-09-17: Enter duplo do terminal no navegador (v0.6.3)

- **Causa do bot na caixa errada**: o terminal do navegador da Hostinger manda Enter como `\r\n`. O Enter da URL do Chatwoot sobrava e escolhia sozinho a primeira caixa da lista seguinte. Conferido no Chatwoot do operador: o bot novo estava na caixa 1 e a do Instagram (2) sem bot. Reproduzido num pty.
- **Também explica o "voltou ao menu" da v0.5.x**: o Enter que sobrava fechava a pausa antes de o operador ler a mensagem.
- **Cada pergunta, escolha, confirmação e pausa descarta o que chegou antes de aparecer** (`descarta_pendentes`, 0,05 s), com terminal e bash 4+.

## 2026-09-17: Bot conferido na caixa e caixa ligada pelo Chatwoot aceita (v0.6.2)

- **Achado no teste com uma caixa do Instagram**: o setup disse que o agente estava no ar, mas o bot não ficou ligado na caixa escolhida. O operador ligou o bot na caixa pelo Chatwoot, e o webhook passou a ignorar o evento porque a caixa não estava em `inbox_ids`.
- **Criar agente confere a ligação** (`GET /inboxes/{id}/agent_bot`): se o bot não ficou na caixa, apaga o bot e mostra o erro. Chatwoot sem essa rota (404) não impede. spec/arquitetura.md.
- **Webhook não filtra mais por caixa.** O Chatwoot só chama o bot a partir das caixas em que ele está ligado e a assinatura prova qual bot é: ligar o bot em outra caixa pelo Chatwoot passa a valer, e as conversas continuam separadas por agente. Substitui a regra "inbox está em `inbox_ids`" da fase 1.

## 2026-09-16: Token de administrador do Chatwoot guardado (v0.6.0)

- **Pedido do operador: não digitar o token a cada ação do menu.** Substitui "o token do administrador não é guardado" (v0.1.3). O token é pedido uma vez por URL do Chatwoot e fica criptografado no banco, na entidade Acesso ao canal (`backend/app/acessos/`). Custo aceito: quem tiver a VPS passa a ter também esse token. spec/dados.md, spec/arquitetura.md.
- **Acesso ao canal não tem `cliente_id`**: é da instalação, porque um Chatwoot atende várias empresas na revenda. Única exceção à regra de toda consulta filtrar por cliente; não guarda dado de contato.
- **A API decide quando falta token**: sem token guardado nem informado, ou com o Chatwoot recusando, responde 428 e o menu pede (`api_com_token`). Token informado que funcionou é guardado; guardado que o Chatwoot recusou é apagado. Recusa vem de `AcessoRecusado` (401 e 403), separada de Chatwoot fora do ar.
- **Remover sempre apaga o bot e renomear sempre renomeia no Chatwoot.** Sem a pergunta, o bot não fica esquecido na caixa. Com o Chatwoot fora, o menu oferece remover deixando o bot (`desconectar_canal: false`) ou salvar o nome só na plataforma (`renomear_no_canal: false`).
- **Menu ganhou "Token do Chatwoot"** para ver onde há token guardado e esquecê-lo. spec/telas.md, tela 8.

## 2026-09-16: Remover agente renomeado e nome do bot no Chatwoot (v0.5.4)

- **Agente renomeado não podia ser removido**: a confirmação comparava com o slug, que guarda o nome de quando o agente foi criado. Agora vale o nome atual ou o original. O menu mostra o nome a digitar e, se não conferir, o que foi digitado.
- **Renomear pelo menu pode trocar o nome do bot no Chatwoot**, com o token de administrador (opcional). `PATCH` do agente aceita `conexao`; o canal ganhou `renomear`. Se o Chatwoot recusar, nada é salvo. Substitui "o bot mantém o nome antigo" da v0.5.0. spec/arquitetura.md.
- **O Shift não era a causa.** Lido no terminal do navegador da Hostinger: Shift sozinho não manda nada, Shift+T manda `T` e setas chegam inteiras. A volta ao menu era a confirmação recusada seguida da pausa. O diagnóstico de teclas usado para descobrir isso saiu na v0.5.5.

## 2026-09-16: Shift não volta mais ao menu (v0.5.3)

- **Achado pelo operador no terminal do navegador da Hostinger**: ao usar Shift para digitar o nome do agente na remoção, o menu voltava. Reproduzido no bash 5: quando a sequência de escape da tecla chega mais de 0,1 s depois do Esc, era lida como Esc sozinho.
- **`le_tecla` lê a sequência inteira** até o byte final e espera até 0,4 s pelo resto. Shift+letra nos formatos kitty (`CSI código;mod u`) e xterm (`CSI 27;mod;código ~`) vira a letra; Esc nesses formatos continua voltando. Sequência desconhecida é ignorada e registrada no log do setup como `tecla ignorada`.

## 2026-09-16: Esc volta à tela anterior (v0.5.2)

- **Pedido do operador.** Cada ação do menu roda num subshell (`com_voltar` em `setup/lib/base.sh`); Esc em qualquer pergunta encerra só a ação, sem salvar, e volta para quem chamou. Na ficha de edição cada mudança é uma ação; na ficha e no menu o Esc escolhe Voltar ou Sair. spec/telas.md.
- **Perguntas digitadas passaram a ser lidas tecla a tecla** com terminal (`ler_linha`), para o Esc chegar antes do Enter. Backspace apaga; setas e teclas de controle são ignoradas.
- **Erro no meio de uma ação do menu volta ao menu** depois de mostrar o motivo, em vez de fechar o comando.
- **O que a ação muda e a tela precisa** (ficha do agente, resultado) sai do subshell por `devolve`.

## 2026-09-16: Setas e telas limpas (v0.5.1)

- **Escolhas com setas e Enter**, pedido do operador, em todo o setup: listas (`escolha`) e Sim/Não (`confirma`), inclusive o aceite da tela 1. Números de 1 a 9 e S/N continuam como atalho. A lista escolhida vira uma linha com a resposta.
- **Cada tela nova limpa o terminal e redesenha o banner** (`secao`). Listagem, consumo e resultado de criar ou remover esperam Enter antes de o menu limpar; a edição de agente redesenha a ficha com o resultado da última mudança.
- **Sem terminal, a leitura continua por linha** (número ou S/N): é o que `simula_onboarding.sh` usa com o arquivo de respostas. spec/telas.md.

## 2026-09-16: Menu do operador (fase 4, v0.5.0)

- **O menu abre ao rodar o setup de novo e com `asimov` sem argumento.** Cada ação também é subcomando (`editar`, `remover`, `consumo`), para quem prefere ir direto. `asimov atualizar` para no resumo, sem menu. spec/telas.md, tela 8.
- **Editar não troca credenciais do canal nem retomada por tempo no Chatwoot.** As credenciais do Chatwoot são do bot que o setup cria, e a retomada é devolver a conversa para pendente. Trocar de Chatwoot ou de caixa é remover e criar de novo; o prompt volta junto (item abaixo). A edição de credenciais entra com os canais diretos (fase 5). A API recusa `retomada_automatica_horas` em canal que não retoma por tempo (`retoma_por_tempo` em `canais/base.py`). spec/arquitetura.md.
- **Nome editado não muda slug nem pasta de prompts.** Até a v0.5.3 o bot no Chatwoot mantinha o nome antigo (ver v0.5.4).
- **Modelo do resumo do handoff escolhível no menu**, com sugestões baratas primeiro. Só aparecem provedores com chave no `.env`: chave nova só vale depois de reconstruir a plataforma.
- **Remover pede o nome do agente e, opcionalmente, o token de administrador do Chatwoot para apagar o Agent Bot.** Sem o token, o bot fica ligado na caixa e o webhook dele cai em Falha `webhook_token_desconhecido`; o menu avisa para tirar o bot da caixa. Se o Chatwoot recusar o token, nada é removido. O contrato pedia confirmação pelo slug; a API compara o slug do nome digitado.
- **Slug do removido ganha `~removido-<id>`**: cliente e agente novos com o mesmo nome podem ser criados, e o agente novo reaproveita a pasta de prompts do removido (o setup nunca sobrescreve prompt). spec/dados.md.
- **Empresa só sai sem agentes** (`DELETE /admin/clientes/{id}`, 409 com agentes). No modo revenda o menu oferece remover a empresa que ficou sem agentes. Rota nova no contrato.
- **Consumo agrupado por agente**, com `turnos` (só `resposta`), `chamadas` (inclui leitura de mídia e resumo), tokens, custo e `sem_custo` (chamadas sem preço conhecido, marcadas com `*` no menu). Turno não tem `agente_id`: a consulta junta pela Conversa filtrando `cliente_id` nos dois lados.
- **Retomar pelo operador devolve no canal antes de fechar o handoff** (Chatwoot: status pendente com o token do bot), com `retomado_por` `operador`. Sem opção no menu por enquanto: falta listar conversas em handoff.
- **Fim da entrada (Ctrl+D) encerra o setup**: as perguntas repetiam sem parar quando a leitura voltava vazia.

## 2026-09-16: Nota de handoff curta (v0.4.1)

- **Primeiro teste na VPS: nota longa demais** para o atendente ler no meio da conversa. Agora é só `Motivo:` e o resumo, sem título nem instrução de devolver. O prompt padrão `resumo_handoff.md` pede até 2 linhas e não repete o motivo. Agentes já criados mantêm o próprio arquivo: o setup nunca sobrescreve prompt.

## 2026-09-16: Handoff no Chatwoot (fase 3, v0.4.0)

- **A tool só registra o pedido; a transferência roda no fim do turno, depois do envio.** Se o contato mandar mensagem nova antes do envio, resposta e pedido são descartados juntos e o turno seguinte decide de novo. Transferir antes de enviar deixaria o contato sem o aviso de que alguém vai continuar. Mesma regra para tools futuras que alteram estado. spec/arquitetura.md, Tools padrão.
- **Ordem no Chatwoot: nota privada, atribuição, status aberto.** Atribuir antes de abrir evita a distribuição automática da caixa escolher outra pessoa; `toggle_status` de pendente para aberto pelo bot é o `bot_handoff` do Chatwoot. Conferido no código do Chatwoot: o token do bot alcança os três. Nota e atribuição que falham viram Falha `handoff_incompleto`, sem impedir a pausa; pausa que falha não grava Handoff e registra `handoff_falhou`.
- **Handoff só é gravado depois que o canal aceitou a transferência.** Um índice único parcial (um handoff aberto por conversa) garante a idempotência.
- **Retomada por `conversation_status_changed` ou `conversation_updated` só quando `changed_attributes` traz status e o status atual é pendente.** A atribuição feita no próprio handoff chega como `conversation_updated` ainda pendente e fecharia o handoff recém aberto. Conversa resolvida que o contato reabre volta pendente (caixa com bot) e também retoma.
- **Devolução perdida é fechada no turno**: se o Chatwoot diz pendente e a conversa ainda está com handoff aberto, o turno fecha com `retomado_por` `chatwoot` antes de responder.
- **Destino de handoff no Chatwoot**: `{"tipo": "usuario"|"time"|"caixa", "id", "nome"}`. `caixa` (e agente sem destino) abre a conversa sem atribuição. A descoberta do canal passou a listar atendentes e times da conta. spec/dados.md, spec/telas.md.
- **`PATCH` do agente antecipado da fase 4, só com `handoff_destino`**, e comando `asimov handoff`: agentes criados antes da v0.4.0 não têm destino. A atualização pergunta uma vez. spec/arquitetura.md, spec/telas.md.
- **Falha do modelo depois das tentativas**: mensagem fixa de expectativa, conversa marcada como respondida e handoff com o motivo. Resumo com o modelo fora do ar cai para as últimas falas do contato na nota, com Falha `resumo_handoff_falhou`.
- **Arquivo acima do limite vai para humano**: o modelo é instruído a avisar e transferir; se não pedir, o turno transfere mesmo assim.
- **Resumo registra Turno com `funcao` `resumo_handoff`** no modelo auxiliar. spec/dados.md, Turno.
- **Handoff ganhou `agente_id`** para o código ser único por agente. `retomado_por` usa o nome do canal (`chatwoot`).

## 2026-09-16: Mensagem enviada durante o turno ficava sem resposta (v0.3.2)

- **Achado no teste da fase 2 em VPS**: dois áudios com 10 s de diferença; o segundo chegou enquanto o primeiro era transcrito e respondido e nunca teve turno. Pendente era "fala do contato depois da última fala do agente", e a resposta é gravada no fim do turno, depois da mensagem nova. Existia desde a fase 1; leitura de mídia deixou o turno longo o bastante para acontecer.
- **Conversa ganhou `respondido_ate`**: hora da última mensagem do contato que um turno respondeu. Pendente é fala do contato depois dela; fala de atendente humano encerra as anteriores. Turno com erro no modelo não avança, como antes. spec/dados.md, Conversa.
- **Mensagem nova antes do envio descarta a resposta** e o turno dela responde tudo junto. A checagem roda depois da leitura de mídia e depois do modelo; a resposta descartada fica em Turno com `erro` começando por `descartada`, porque consumiu. Depois que o envio começou, o que chegar vai para o turno seguinte. Por quê: o Chatwoot baixa a mídia do WhatsApp antes de chamar o webhook, então dois áudios mandados no mesmo segundo chegaram com 10 s de diferença, mais que o buffer de 8 s.

## 2026-09-16: `asimov atualizar` baixa o instalador da main (v0.3.1)

- **`asimov atualizar` não atualizava**: rodava o `install.sh` da própria VPS, que tem fixa a versão já instalada, e baixava de novo a mesma versão. Agora baixa o `install.sh` da `main`, que aponta para a última tag. Resumo final mostra a versão instalada.
- **Repositório continua público**: com ele privado, o download do pacote sem login devolve 404.

## 2026-09-16: Áudio, imagem e documento (fase 2, v0.3.0)

- **Download no turno, não no webhook**, pelo contrato do canal (`baixar_midia` em `canais/base.py`). O webhook grava o anexo como dado estruturado na Mensagem. Mensagem com vários anexos vira uma Mensagem por anexo; a partir da segunda, `id_externo` recebe o sufixo `:n` para a deduplicação continuar valendo. Mensagem só com anexo agora gera turno.
- **Situação da leitura gravada no anexo** (`lido`, `acima_do_limite`, `nao_suportado`, `falhou`), para o modelo saber por que um arquivo não foi lido, inclusive no histórico. spec/dados.md, Mensagem.
- **Mídia só é gravada depois de lida com sucesso**, com `resultado` (texto) e `metadados`. Falha não entra no cache: reenviar tenta de novo.
- **Turno ganhou `funcao`** (`resposta`, `transcricao`, `visao`): leitura de mídia registra o próprio Turno, e mídia vinda do cache não registra. É o que o critério de aceite confere. spec/dados.md, Turno.
- **Acima do limite não faz handoff ainda**: registra Falha e o agente pede para escrever. Handoff é da fase 3.
- **PDF com texto lido com `pypdf`** antes da visão; só PDF escaneado vai para o modelo, limitado às 10 primeiras páginas. Texto extraído cortado em 12 mil caracteres. Groq não lê PDF: escaneado com visão na Groq vira `falhou`. Vídeo e tipos desconhecidos viram `nao_suportado`, sem Falha. spec/arquitetura.md.
- **Duração do áudio com `tinytag`** (MIT) em vez de ffmpeg na imagem. Se o cabeçalho não disser a duração, o áudio é processado; o limite de 20 MB continua valendo.
- **Transcrição da OpenAI e da Groq por httpx** no endpoint de áudio, sem depender da assinatura do SDK; Gemini pelo próprio modelo. Anthropic recusada para transcrição também na validação da API.
- **Link de anexo do Chatwoot baixado sem o token do bot**: o link já é assinado e o httpx repassaria o header no redirect para o armazenamento.
- **Lock da conversa de 90 para 240 s**: leitura de mídia e resposta rodam no mesmo turno.
- **"Turno com mídia sem tools que alteram estado"** fica para quando existir a primeira tool (fase 3): hoje o agente não tem tools. Anotado em spec/estado.md.

## 2026-09-16: Modo de uso, modelos por função e comando asimov (v0.2.0)

- **Modo de uso perguntado antes de instalar**: só a própria empresa ou revenda para empresas clientes. A plataforma segue multitenant nos dois; muda só o fluxo de criação de agente. spec/telas.md, tela 1b.
- **Modelo por função com provedor próprio** (resposta, fallback, visão, transcrição) e **Groq** entre os provedores. Substitui o provedor único com provedor de apoio. Modelos listados pela API do provedor em vez de nomes fixos, que envelhecem. Novo campo `modelo_fallback` no Agente. spec/telas.md, spec/dados.md, spec/arquitetura.md.
- **Comando `asimov`** (`novo-agente`, `agentes`, `atualizar`) antecipado da fase 4, porque criar agente para empresa nova ou existente não pode depender de rodar o setup inteiro. spec/visao.md, função 15.
- **Onboarding enxuto e colorido**: seções de uma linha, ✓ ▲ ✗, valores em destaque, espera do DNS numa linha só, nome da empresa sugerido pela conta do Chatwoot.
- **Setup rodado de novo numa instalação concluída** pergunta o que versões novas exigem (modo, modelos) e reconstrói.

## 2026-09-16: Setup cria o bot do Chatwoot sozinho (v0.1.3)

- **O onboarding do Chatwoot estava complexo demais**: criar o bot à mão com URL provisória, copiar secret, token de usuário, ID de conta e de caixa, e trocar a URL no fim. Agora o operador cola só a URL do Chatwoot e o token de um administrador, escolhe conta e caixa num menu e digita o nome do agente. A API cria o Agent Bot já com a URL do webhook e liga o bot na caixa.
- **Em operação usa o token do próprio bot**, não o de usuário. Conferido no código do Chatwoot (`BOT_ACCESSIBLE_ENDPOINTS`): o bot vê a conversa, muda status, envia digitando, atribui e cria mensagem. O token do administrador não é guardado. Substitui a decisão de "Agent Bot criado antes com URL provisória". Atualizados spec/telas.md, spec/dados.md e spec/arquitetura.md.

## 2026-09-16: Checagem de DNS nos servidores oficiais do domínio (v0.1.2)

- **A checagem consultava só o 1.1.1.1**, que seguiu respondendo "domínio não existe" por mais de 10 minutos depois de o registro existir, enquanto Google e Quad9 já viam o IP. Agora consulta primeiro os servidores oficiais do domínio (onde o registro aparece na hora e onde o Let's Encrypt confere) e, se não houver resposta, 8.8.8.8, 1.1.1.1 e 9.9.9.9.

## 2026-09-16: Correções do primeiro teste em VPS (v0.1.1)

- **Setup caía em silêncio na checagem do domínio** quando `bot.<domínio>` ainda não tinha registro: consulta de DNS vazia com `set -e` encerrava o script antes de mostrar as instruções. Consultas passaram a tolerar resultado vazio, e o setup ganhou um tratamento de erro geral: nenhuma queda sem mensagem, linha e caminho do log.
- **Instruções de DNS aparecem antes da checagem**, com o registro exato e onde criar; checagem automática a cada 15 s; aviso de AAAA. spec/telas.md, tela 4.
- **`ASIMOV_ATUALIZAR=1`** no `install.sh` atualiza o código de uma instalação existente sem perder `.env`, prompts e progresso.
- **Licença MIT confirmada** pelo operador; arquivo `LICENSE` adicionado. spec/telas.md, tela 1.
- **Repositório público `asimov-academy/asimov-agentes`**, sem nenhum dado de cliente real: exemplos da spec e dos testes trocados por um agente fictício (Loja Exemplo, Ana). A URL do Chatwoot é sempre informada no setup.

## 2026-09-16: Ajustes da Fase 1 na construção

- **Estado do setup em arquivo CHAVE=VALOR (`~/.asimov/estado`), não JSON.** A tela 1 roda antes de o `jq` ser instalado; um formato que o Bash lê sozinho evita dependência. Atualizados spec/arquitetura.md e spec/fases.md.
- **Token do webhook guardado duas vezes: hash SHA-256 (busca pela URL) e cifrado (o menu mostra a URL de novo).** spec/dados.md fala só em "segredo único"; nenhum dos dois fica em claro.
- **Deduplicação de Mensagem por `(conversa_id, id_externo)`**, não por agente. O id de mensagem do Chatwoot é único na instância, então o efeito é o mesmo com um índice mais simples.
- **`conversation_updated` do Chatwoot é aceito e ignorado na Fase 1.** Retomada e transferência são da Fase 3. Conversa fora de `pending` já não recebe resposta: o turno relê o status no Chatwoot antes de falar.
- **Mensagem só com anexo é gravada sem gerar turno.** Áudio, imagem e documento são da Fase 2.
- **Scripts `deploy/testar.sh` e `deploy/nova_migracao.sh` criados** além de `deploy/publicar.sh`, porque o `AGENTS.md` gerado precisa de comandos exatos e curtos para o agente de código.
- **Agent Bot do Chatwoot criado antes com URL provisória.** O Chatwoot só mostra o secret ao criar o bot, e a URL definitiva só existe depois que o agente é criado. A tela 6 orienta criar com `https://bot.<dominio>/aguardando` e trocar no fim.
- **Pacote baixado pelo `install.sh` exclui `spec/`, `AGENTS.md` e `CLAUDE.md`** (`.gitattributes` com `export-ignore`). O setup gera os arquivos do operador e não sobrescreve os de desenvolvimento quando encontra `spec/`.

## 2026-09-16: Spec inicial concluída

- Seis etapas concluídas: spec/visao.md, spec/usuarios.md, spec/telas.md, spec/dados.md, spec/arquitetura.md e spec/fases.md.
- Arquivos de contexto deste repositório seguem a mesma regra definida para o projeto gerado (spec/arquitetura.md, seção 11): `AGENTS.md` é a fonte única e `CLAUDE.md` contém só `@AGENTS.md`, em vez de duas cópias do mesmo conteúdo.
- Primeiro canal construído: Chatwoot (spec/fases.md, Fase 1).
