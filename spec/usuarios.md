# Etapa 2: Quem usa

## Tipos de usuário

### Operador

Quem roda o setup numa VPS: o dono do projeto, alunos da metodologia e clientes da metodologia. Familiaridade alta com tecnologia: usa SSH, terminal, domínio e DNS, e desenvolve com vibecoding.

No app:
- Roda o setup, escolhe Claude Code ou Codex e informa domínio, e-mail do SSL e chaves.
- Cria os agentes de cada cliente (empresa), escolhe o canal de cada agente (Chatwoot, WhatsApp oficial, WhatsApp não oficial pela WAHA ou nativo no terminal) e informa as credenciais.
- Cola a URL de webhook gerada no canal.
- Sobe a base de conhecimento de cada agente.
- Depois do setup, evolui prompts, tools e comportamento em vibecoding direto no projeto.

### Contato

O público de cada cliente (empresa) que conversa com o agente. Familiaridade variável; só usa o WhatsApp (direto ou por uma caixa do Chatwoot).

No app:
- Manda texto, áudio, imagem e documento pelo canal e recebe as respostas do agente.
- Não sabe da existência da instalação e não acessa nada fora da própria conversa.

### Atendente humano

Pessoa da empresa cliente que assume a conversa no handoff. Familiaridade média.

No app:
- **Canal Chatwoot:** recebe a conversa transferida pelo agente e responde dentro do próprio Chatwoot.
- **WhatsApp direto (oficial ou WAHA):** recebe no número ou grupo da empresa um aviso com o resumo da conversa, fala com o contato pelo próprio telefone e manda um comando para o agente voltar a responder àquele contato. Sem o comando, o agente volta sozinho depois de um tempo configurável, com padrão de algumas horas (assumido).
- Não configura agentes nem acessa a VPS.

## Regras de visibilidade

- Operador: vê e altera tudo da instalação, de todos os clientes.
- Atendente humano: só as conversas do agente do próprio cliente. No Chatwoot, as da caixa onde o bot está; no canal direto, só os avisos de handoff do próprio cliente. O comando de retomada só é aceito vindo do número ou grupo de handoff cadastrado para aquele agente.
- Contato: só a própria conversa. O agente nunca usa dados de outro contato nem a base de conhecimento de outro cliente.
- Empresas clientes não entram na instalação.

## Quem administra

O operador, sozinho. Não existe outro papel administrativo.

## Forma de entrada

- Operador: acesso SSH à VPS. Não há login de usuário no app nesta versão.
- Contato: sem login; identificado pelo ID do canal (telefone ou chat id no WhatsApp, contato no Chatwoot; no nativo, a conversa do operador no terminal).
- Atendente humano: pelo login do próprio Chatwoot, ou pelo número ou grupo cadastrado para o handoff no canal direto.

## Escala e dispositivo principal

- Um operador por instalação.
- Até uns 10 agentes por instalação (assumido); cada operador atende poucas empresas (o dono do projeto atende 3).
- Volume de contatos: de centenas a alguns milhares de conversas por dia por instalação (assumido).
- Operador no computador, pelo terminal via SSH. Contato e atendente no celular.

## Implicações técnicas

- Autenticação de pessoas: nenhuma dentro do app. O acesso administrativo é o SSH da VPS. Qualquer rota administrativa da API (criar agente, subir base de conhecimento) escuta só em localhost ou exige chave de API guardada em variável de ambiente (derivado).
- Autenticação de entrada dos canais: todo webhook é verificado antes de processar. WhatsApp pela assinatura `X-Hub-Signature-256` com o app secret; WAHA pela assinatura `X-Webhook-Hmac` (HMAC SHA-512 do corpo) com a chave do agente, chegando só pela rede interna do Docker; Chatwoot pela assinatura HMAC `X-Chatwoot-Signature` com o secret do Agent Bot, além do token secreto único por agente na URL do webhook (derivado). Webhook sem verificação válida é rejeitado.
- Autorização por papel:

| Ação | Operador | Atendente | Contato |
|---|---|---|---|
| Rodar setup e configurar VPS | sim | não | não |
| Criar e editar agente, canal e credenciais | sim | não | não |
| Subir base de conhecimento | sim | não | não |
| Conversar com o agente | não | não | sim, só a própria conversa |
| Receber handoff | não | sim, só do próprio cliente | não |
| Retomar agente após handoff | sim | sim, só do número ou grupo cadastrado | não |

- Acesso anônimo: o contato é anônimo para o app, identificado só pelo ID do canal, e enxerga apenas as respostas da própria conversa.
- Isolamento: multitenant com unidade de agrupamento **cliente** (empresa). Agente, credenciais de canal, contatos, conversas, mensagens, estado de handoff e base de conhecimento pertencem a um cliente, e toda consulta filtra por ele. A busca do RAG também filtra por cliente e agente.
- Credenciais de canal por agente são segredos: guardadas criptografadas no banco ou em variáveis de ambiente, nunca no código nem em log (derivado).
- Hospedagem: uma VPS única dá conta da escala. Processamento de mensagem assíncrono (buffer, transcrição, visão) para responder rápido ao webhook e não perder mensagem em pico (derivado).
