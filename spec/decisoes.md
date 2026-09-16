# Decisões

Log de mudanças na spec. Cada entrada: data, o que mudou, por quê e quais arquivos de `spec/` foram atualizados. Entrada mais nova no topo.

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
