# Etapa 4: O que o app guarda

Unidade de agrupamento: **cliente** (ver spec/usuarios.md, Implicações técnicas). Papéis e telas: ver spec/usuarios.md e spec/telas.md.

## Entidades

### Instalação

Configuração única da VPS. Não fica no banco: segredos em `.env` com permissão 600 e progresso do setup em arquivo de estado na VPS (derivado).

| Atributo | Tipo | Obrigatório |
|---|---|---|
| dominio_base | texto | sim |
| subdominio_bot | texto, `bot.<dominio_base>` | sim |
| email_ssl | e-mail | sim |
| agente_codigo | `claude_code` ou `codex` | sim |
| modo_instalacao | `empresa` ou `revenda` | sim |
| modelo_conversa, modelo_fallback, modelo_visao, modelo_transcricao | `provedor:modelo`; padrões para agentes novos; fallback opcional | sim, exceto fallback |
| provedores | provedores usados pelos modelos, para instalar os SDKs | sim |
| chaves de IA (OpenAI, Anthropic, Gemini, Groq) | segredo | as dos provedores escolhidos |
| modelo_embeddings | texto; único na instalação, porque define a dimensão do vetor | sim |
| chave_criptografia | segredo gerado pelo setup, para as credenciais de canal | sim |
| chave_api_admin | segredo gerado pelo setup, para as rotas administrativas | sim |
| versao_setup | texto | sim |
| passo_atual e passos_concluidos | lista | sim |

### Cliente

A empresa atendida pelo operador.

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| nome | texto | sim |
| slug | texto único | sim |
| ativo | booleano | sim |
| criado_em, removido_em | data e hora | criado sim, removido não |

### Agente (entidade principal)

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| nome | texto | sim |
| slug | texto único dentro do cliente | sim |
| canal | `chatwoot`, `whatsapp` (oficial), `waha` (não oficial) ou `nativo` (só terminal) | sim |
| credenciais_canal | segredo estruturado por canal (ver abaixo), criptografado | sim |
| token_webhook | segredo único gerado, compõe a URL do webhook | sim |
| arquivo_prompt | caminho do prompt da persona no repositório | sim |
| arquivo_prompt_handoff | caminho do prompt de resumo de handoff | sim |
| modelo_conversa | texto (provedor e modelo) | sim |
| modelo_fallback | texto (provedor e modelo); usado se modelo_conversa falhar | não |
| modelo_auxiliar | texto (resumo de handoff, classificação) | sim |
| modelo_visao | texto | sim |
| modelo_transcricao | texto | sim |
| buffer_segundos | inteiro | sim, padrão 8 |
| max_mensagens_por_resposta | inteiro | sim, padrão 3 (derivado) |
| digitacao_caracteres_por_segundo | inteiro, 1 a 30 | sim, padrão 6 |
| digitacao_maximo_segundos | inteiro, 1 a 30; teto do digitando por mensagem | sim, padrão 20 |
| ferramentas | lista de nomes do catálogo (`calculadora`, `busca_web`) | sim; o agente novo nasce só com as marcadas na criação (vazia sem escolha, desde a v0.8.11) |
| contatos_permitidos | telefones que o agente atende, só dígitos; lista vazia (o normal) atende qualquer pessoa. Serve para testar um número novo sem responder a quem escrever para ele | sim, `[]` |
| handoff_destino | estruturado por canal: no WhatsApp oficial `{tipo: numero, telefone, template: {nome, idioma}}` (o template leva o aviso fora da janela de 24 horas); na WAHA `{tipo: numero ou grupo, chat_id, telefone, nome}` (o número é normalizado para `<dígitos>@c.us`); no nativo, vazio; no Chatwoot `{tipo: usuario, time ou caixa, id, nome}` (caixa abre sem atribuir) | sim; vazio em agente anterior à v0.4.0 se comporta como caixa |
| retomada_automatica_horas | inteiro | não; padrão 4 no WhatsApp direto (assumido); vazio no Chatwoot (retomada é devolver a conversa para pendente) |
| ativo | booleano | sim |
| criado_em, atualizado_em, removido_em | data e hora | criado e atualizado sim |

Credenciais por canal:

- WhatsApp oficial: waba_id (conta de WhatsApp Business), phone_number_id, app_id, access_token (permanente), app_secret, numero e nome_verificado (como a Meta mostra, só para o menu). Não há verify_token guardado: a verificação da Meta é respondida pelo próprio `token_webhook` da URL.
- WAHA: sessao (nome da sessão na WAHA), hmac_key (gerada). Endereço e chave da WAHA são da Instalação (`WAHA_API_KEY` no `.env`).
- Nativo: nenhuma.
- Chatwoot: url, account_id, inbox_ids, api_access_token (token do Agent Bot), bot_id, bot_secret. O token do administrador não fica nas credenciais do agente: fica em Acesso ao canal.

### Acesso ao canal

Acesso do operador a um canal, pedido uma vez e reaproveitado (no Chatwoot, o token de administrador, usado para criar, renomear e apagar bots e para listar contas, caixas e atendentes). É da instalação, não de um cliente: o mesmo Chatwoot atende empresas diferentes na revenda.

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| canal | `chatwoot` | sim |
| endereco | URL do Chatwoot | sim, único por canal |
| acesso | segredo estruturado (token_admin), criptografado | sim |
| criado_em, atualizado_em | data e hora | sim |

### Contato

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| agente_id | referência a Agente | sim |
| id_externo | texto (telefone na Cloud API, chat id `@c.us`/`@lid` na WAHA, contact id do Chatwoot, `terminal` no nativo) | sim, único por agente |
| nome | texto | não |
| telefone | texto | não |
| ultima_mensagem_em | data e hora | sim (controla a janela de 24 horas do WhatsApp) |
| criado_em | data e hora | sim |

### Conversa

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| agente_id | referência a Agente | sim |
| contato_id | referência a Contato | sim |
| id_externo | texto (display_id no Chatwoot, telefone na Cloud API, chat id na WAHA, id da conversa do terminal no nativo) | sim |
| canal | por onde a conversa acontece: o canal do agente, ou `nativo` na conversa de teste do terminal (vale para agente de qualquer canal) | sim |
| status | `agente` ou `humano` | sim |
| respondido_ate | data e hora da última mensagem do contato respondida por um turno | não |
| criado_em, atualizado_em | data e hora | sim |

### Mensagem (repetida ao longo do tempo, pertence a Conversa)

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| conversa_id | referência a Conversa | sim |
| direcao | `entrada` ou `saida` | sim |
| autor | `contato`, `agente` ou `humano` | sim |
| tipo | `texto`, `audio`, `imagem`, `documento`, `video` | sim |
| texto | texto | não |
| texto_extraido | texto (transcrição ou leitura da mídia) | não |
| anexo | estruturado: tipo, referência do canal para baixar, tamanho, nome e `situacao` da leitura (`lido`, `acima_do_limite`, `nao_suportado`, `falhou`) | não |
| midia_id | referência a Mídia | não |
| id_externo | texto, único por agente (deduplica reentrega de webhook) | sim na entrada |
| criado_em | data e hora | sim |

### Mídia

Arquivo recebido de contato, com o cache do processamento.

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| hash_sha256 | texto, único por cliente | sim |
| tipo_mime | texto | sim |
| tamanho_bytes | inteiro | sim |
| caminho_arquivo | texto | sim |
| arquivo_apagado_em | quando o arquivo saiu do disco (na limpeza diária, um dia depois de lido). O texto fica | não |
| resultado | texto extraído (transcrição ou leitura) | sim; só existe registro de mídia lida com sucesso |
| metadados | estruturado: modelo, páginas lidas, forma de leitura | sim |
| criado_em | data e hora | sim |

### Handoff (repetido ao longo do tempo, pertence a Conversa)

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| agente_id | referência a Agente | sim |
| conversa_id | referência a Conversa | sim; no máximo um handoff aberto (sem `retomado_em`) por conversa |
| motivo | texto | sim |
| resumo | texto | sim |
| codigo | texto curto único por agente, usado em `/retomar <código>` | sim |
| destino | cópia do handoff_destino no momento | sim |
| iniciado_em | data e hora | sim |
| retomar_em | data e hora (retomada automática agendada) | não |
| retomado_em | data e hora | não |
| retomado_por | `comando`, `tempo`, `chatwoot` ou `operador` (menu) | não |

### Documento (base de conhecimento)

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| agente_id | referência a Agente | sim |
| nome_arquivo | texto | sim |
| caminho_arquivo | texto | sim |
| hash_sha256 | texto, único por agente | sim |
| tipo_mime | texto | sim |
| status | `processando`, `pronto` ou `erro` | sim |
| total_trechos | inteiro | não |
| criado_em, removido_em | data e hora | criado sim |

### Trecho (pertence a Documento)

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| agente_id | referência a Agente | sim |
| documento_id | referência a Documento | sim |
| ordem | inteiro | sim |
| texto | texto | sim |
| embedding | vetor | sim |

### Turno (assumido; repetido ao longo do tempo, pertence a Conversa)

Um ciclo de processamento após o buffer.

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | sim |
| conversa_id | referência a Conversa | sim |
| modelo | texto | sim |
| funcao | `resposta`, `transcricao`, `visao` ou `resumo_handoff` | sim |
| tokens_entrada, tokens_saida | inteiro | sim |
| custo_estimado | decimal | sim |
| latencia_ms | inteiro | sim |
| tools_chamadas | lista | não |
| erro | texto | não |
| criado_em | data e hora | sim |

### Falha

Falha fora de um turno (webhook inválido, canal fora do ar, envio recusado).

| Atributo | Tipo | Obrigatório |
|---|---|---|
| id | identificador | sim |
| cliente_id | referência a Cliente | não (webhook sem agente identificado) |
| agente_id | referência a Agente | não |
| tipo | texto | sim |
| detalhe | estruturado | sim |
| criado_em | data e hora | sim |

## Relacionamentos

- Cliente 1 para muitos Agente.
- Agente 1 para muitos Contato, Conversa e Documento.
- Contato 1 para muitos Conversa.
- Conversa 1 para muitos Mensagem, Handoff e Turno.
- Mensagem muitos para 1 Mídia (a mesma mídia reenviada aponta para o mesmo registro).
- Documento 1 para muitos Trecho.

## Exemplos

### Agente (exemplo)

| Atributo | Valor |
|---|---|
| cliente | Loja Exemplo |
| nome | Ana |
| slug | ana |
| canal | chatwoot (inbox com WhatsApp Cloud API ligada no Chatwoot) |
| credenciais_canal | url `https://chatwoot.exemplo.com.br` (informada pelo operador no setup), account_id `1`, inbox_ids `3`, api_access_token `xxx` (do bot), bot_id `42`, bot_secret `xxx` |
| arquivo_prompt | `loja-exemplo/ana/persona.md` |
| arquivo_prompt_handoff | `loja-exemplo/ana/resumo_handoff.md` |
| modelo_conversa | `openai:gpt-5.5` |
| modelo_fallback | `groq:llama-3.3-70b-versatile` |
| modelo_auxiliar | `openai:gpt-5-mini` |
| modelo_visao | `openai:gpt-5-mini` |
| modelo_transcricao | `openai:whisper-1` |
| buffer_segundos | 8 |
| max_mensagens_por_resposta | 3 |
| handoff_destino | `{tipo: usuario, id: 7, nome: Joana}` |
| handoff_template | vazio (canal Chatwoot) |
| retomada_automatica_horas | vazio (retomada devolvendo a conversa para pendente no Chatwoot) |
| ativo | sim |

### Demais entidades (derivado)

- Cliente: nome `Loja Exemplo`, slug `loja-exemplo`, ativo sim.
- Contato: agente Ana, id_externo `4812`, nome `Maria`, telefone `5511999990000`.
- Conversa: id_externo `1532`, status `agente` (vira `humano` enquanto há handoff aberto).
- Mensagem: direcao `entrada`, autor `contato`, tipo `audio`, texto_extraido `quero trocar um produto`.
- Mídia: tipo_mime `audio/ogg`, tamanho_bytes `48213`, resultado com a transcrição.
- Handoff: motivo `contato pediu para falar com uma pessoa`, resumo `Maria quer trocar um produto com defeito e já enviou o número do pedido`, retomado_por `chatwoot`.
- Documento: agente de outro cliente, nome_arquivo `tabela-precos-2026.pdf`, status `pronto`, total_trechos `42`.
- Turno: modelo `openai:gpt-5.5`, tokens_entrada `6120`, tokens_saida `180`, latencia_ms `11800`.

## Dados sensíveis

- Chaves de IA, chave de criptografia, chave administrativa e credenciais de canal.
- Conteúdo de conversas, mensagens, mídias e resumos de handoff: dados pessoais de contatos (nome, telefone e, em alguns negócios, CPF e dados financeiros). Sujeito à LGPD.
- Documentos da base de conhecimento: podem conter informação comercial interna do cliente.

## Dados com arquivos ou imagens

- Mídia: áudios, imagens, PDFs e vídeos recebidos de contatos.
- Documento: arquivos da base de conhecimento enviados pelo operador.

## Implicações técnicas

- Dono dos dados: toda entidade do banco carrega `cliente_id` (exceto Acesso ao canal, que é da instalação), inclusive as filhas (Mensagem, Trecho, Turno), para que o filtro por cliente seja direto em toda consulta sem depender de join. Entidades de agente carregam também `agente_id`. Instalação não pertence a cliente.
- Isolamento: toda consulta de repositório exige `cliente_id`. A busca vetorial do RAG filtra por `cliente_id` e `agente_id` antes da similaridade. O cache de Mídia é por cliente: o mesmo hash em clientes diferentes gera registros separados, para que o resultado extraído de um cliente nunca apareça em outro.
- Resolução do dono no webhook: a URL do webhook contém o `token_webhook` do agente, que identifica agente e cliente antes de qualquer leitura; a verificação de assinatura usa a credencial desse agente.
- Proteção de dados sensíveis: credenciais de canal criptografadas na aplicação com a chave da Instalação; segredos nunca em log; logs de mensagens sem conteúdo integral em nível informativo (derivado); `.env` com permissão 600.
- Armazenamento de arquivos: volume local na VPS, separado por `cliente/agente`, fora do diretório servido publicamente. Limite de 20 MB por arquivo e 5 minutos de áudio (assumido); acima disso, não processa, registra Falha e o agente pede para o contato escrever (handoff a partir da fase 3). Volume estimado: um agente ativo gera na ordem de 150 mensagens por dia; com 10 agentes, na ordem de 1.500 mensagens por dia e poucos GB de mídia por ano (assumido).
- Retenção: mídia de contato guardada por 90 dias e depois apagada do disco, mantendo `texto_extraido` na mensagem (assumido).
- Histórico: Mensagem, Handoff, Turno e Falha são somente inserção. Agente e Cliente guardam só o estado atual; o histórico dos prompts fica no git do projeto.
- Exclusão lógica: Cliente, Agente e Documento (`removido_em`). Ao remover Documento, seus Trechos são apagados fisicamente. Ao remover Agente, o webhook deixa de responder e as credenciais são apagadas. Cliente só é removido sem agentes. O slug removido ganha o sufixo `~removido-<id>`, para um cadastro novo com o mesmo nome; agente novo com o nome de um removido reaproveita a pasta de prompts.
- Backup obrigatório: banco completo, `.env`, prompts e arquivos da base de conhecimento, diário, com retenção de 14 dias e cópia remota opcional (assumido).
- Importação inicial: nenhuma. Base de conhecimento carregada pelo menu a partir de arquivos na VPS (PDF, DOCX, TXT, MD) (assumido).
- Modelos por agente: provedor e modelo são configuração, nunca constante no código; a Instalação precisa ter a chave do provedor de cada modelo escolhido. O modelo de embeddings é da Instalação, não do agente: trocar exige reprocessar todos os Trechos.
