# Etapa 6: Plano de fases

Cada fase entrega algo que o operador usa de ponta a ponta numa VPS real: script, API, banco e serviço no ar. Referências: funções em spec/visao.md, telas em spec/telas.md, entidades em spec/dados.md, decisões técnicas em spec/arquitetura.md.

Ação mais importante: sair de uma VPS vazia com um agente respondendo. Primeiro canal: Chatwoot, porque é o canal que o operador já usa hoje e permite testar handoff sem template da Meta.

Ambiente de teste de todas as fases: uma VPS Ubuntu 24.04 descartável (com snapshot do estado vazio para reinstalar em minutos) e um subdomínio de teste apontado para ela.

## Fase 1: Setup de ponta a ponta com um agente de texto no Chatwoot

Situação: concluída e validada em VPS real (v0.2.0).

Objetivo: rodar um comando numa VPS vazia e terminar com um agente respondendo texto numa inbox do Chatwoot.

O que entra:
- Repositório iniciado com `setup/`, `backend/`, `prompts/`, `deploy/`, `modelos/`, `.gitignore` e `.env.example`.
- Telas 1 a 7 de spec/telas.md, com canal só Chatwoot na tela 6: boas-vindas e aceite, iniciando com passos numerados, dados da instalação com escolha de agente de código e provedor de IA (chaves testadas), checagem de DNS, instalação, primeiro agente, resumo final.
- Tratamento de erro do setup: repetição de falha passageira, `[ ERRO ]` com instrução, log e retomada por `$HOME/.asimov/estado`.
- Docker Compose com caddy, api, worker, postgres (pgvector) e redis; firewall 22, 80 e 443.
- Entidades: Cliente, Agente, Contato, Conversa, Mensagem, Turno, Falha.
- API: `GET /health`, criar e listar cliente, criar e listar agente, testar credenciais, `POST /webhook/chatwoot/{token}`.
- Worker: buffer por conversa, turno com PydanticAI no provedor escolhido, divisão em até 3 mensagens, digitando, registro de Turno.
- Credenciais criptografadas; `X-Admin-Key`; `/admin` fora do Caddy.
- Geração de `AGENTS.md` e `CLAUDE.md` do projeto instalado a partir de `modelos/` (spec/arquitetura.md, seção 11), primeiro commit do projeto, `deploy/publicar.sh`.
- Fixture de teste com o agente de exemplo (spec/dados.md, Exemplos).
- Testes: isolamento por cliente nos repositórios e nas rotas admin; assinatura do Chatwoot (válida, inválida com 200, formato `timestamp.corpo`); deduplicação; buffer juntando mensagens; divisão; credenciais nunca em resposta ou log; `shellcheck` sem erros.

Dependências: nenhuma.

Critério de aceite:
- Rodo o comando numa VPS vazia, aceito os termos, respondo as perguntas e chego ao resumo final sem editar nenhum arquivo.
- Colo o webhook no bot do Chatwoot, mando três mensagens seguidas e recebo uma resposta só, dividida em mensagens curtas, com digitando antes.
- Derrubo a conexão SSH no meio da instalação, rodo o comando de novo e ele continua de onde parou.
- Abro `https://bot.<meu-dominio>/health` e vejo tudo ok; `https://bot.<meu-dominio>/admin/clientes` não responde de fora.
- Entro na pasta do projeto, abro o Claude Code ou o Codex e ele já conhece os comandos de teste e publicação.

O que o operador precisa fazer:
- Criar a VPS de teste e o snapshot vazio; apontar o subdomínio de teste.
- Ter a chave do provedor de IA escolhido.
- Criar o Agent Bot no Chatwoot, colar a URL do webhook e ligar o bot numa inbox de teste.

Commit: `feat: setup de ponta a ponta com agente de texto no Chatwoot`

## Fase 2: Áudio, imagem e documento

Situação: construída (v0.3.0), falta validar o critério de aceite em VPS real.

Objetivo: o agente entende áudio, imagem e PDF enviados pelo contato.

O que entra:
- Entidade Mídia com cache por cliente e hash.
- Download de anexo pelo canal Chatwoot, transcrição e leitura com visão conforme o provedor, limites de 20 MB e 5 minutos.
- Conteúdo extraído rotulado como dado do contato; turno com mídia sem tools que alteram estado.
- Falha de transcrição vira pedido para o contato escrever e registro em Falha.
- Testes: cache não reaproveitado entre clientes; mídia repetida processada uma vez; arquivo acima do limite não processado.

Dependências: Fase 1.

Critério de aceite:
- Mando um áudio perguntando algo e o agente responde ao que eu falei.
- Mando a foto de um documento e um PDF e o agente responde sobre o conteúdo.
- Reenvio o mesmo áudio e o consumo em "Turno" não mostra nova transcrição.

O que o operador precisa fazer:
- Se o provedor escolhido foi Anthropic, ter a chave do provedor de apoio.
- Testar com áudios e arquivos reais.

Commit: `feat: agente entende áudio, imagem e documento`

## Fase 3: Handoff no Chatwoot

Objetivo: o agente passa a conversa para um humano no Chatwoot e volta quando devolvida.

O que entra:
- Entidade Handoff.
- Tool `transferir_para_humano` com resumo pelo modelo auxiliar em nota privada, atribuição ao usuário ou time de `handoff_destino` e status `open`.
- Evento `conversation_updated`: volta para `pending` fecha o handoff e retoma o agente.
- Falha no turno (modelo fora do ar, erro de tool) após 2 tentativas vira mensagem de expectativa e handoff.
- Prompt padrão `resumo_handoff.md` criado junto com o agente.
- Testes: conversa com humano não gera resposta; retomada pelo status; handoff idempotente.

Dependências: Fase 1.

Critério de aceite:
- Peço para falar com uma pessoa e a conversa aparece atribuída no Chatwoot com um resumo em nota privada.
- Enquanto está com o humano, mando mensagens e o agente não responde.
- Devolvo a conversa para pendente, mando mensagem e o agente volta a responder.

O que o operador precisa fazer:
- Informar o usuário ou time do Chatwoot que recebe o handoff.

Commit: `feat: handoff para humano no Chatwoot`

## Fase 4: Menu do operador

Situação: parcial, `asimov novo-agente` e `asimov agentes` prontos.

Objetivo: rodar o setup de novo abre um menu para operar agentes e ver consumo.

O que entra:
- Tela 8 de spec/telas.md sem a opção de base de conhecimento: criar agente, listar agentes e webhooks, editar agente, remover agente com confirmação, ver consumo e falhas.
- API: ver, editar e remover agente; ver consumo e falhas; retomar conversa.
- Exclusão lógica de Cliente e Agente; remoção invalida o webhook e apaga credenciais.
- Testes: rota admin com agente de outro cliente devolve 404; agente removido não processa webhook; consumo filtrado por cliente.

Dependências: Fases 1 e 3.

Critério de aceite:
- Rodo o comando de novo e aparece o menu em vez da instalação.
- Crio um segundo cliente com outro agente no Chatwoot e os dois respondem cada um na sua inbox, sem misturar conversas.
- Troco o tempo de buffer de um agente pelo menu e a mudança vale na próxima mensagem.
- Removo um agente e ele para de responder.
- Vejo quanto cada cliente consumiu nos últimos 7 dias.

O que o operador precisa fazer:
- Criar um segundo Agent Bot e uma segunda inbox no Chatwoot para o teste de dois clientes.

Commit: `feat: menu do operador com agentes e consumo`

## Fase 5: WhatsApp oficial e Telegram diretos

Objetivo: agentes ligados direto no WhatsApp Cloud API e no Telegram, com handoff por aviso.

O que entra:
- Implementações de `canais/whatsapp/` e `canais/telegram/` na mesma interface do Chatwoot: verificação de assinatura, verificação da Meta, normalização, envio, digitando, download de mídia.
- Registro automático do webhook no Telegram ao criar e remoção ao apagar agente.
- Handoff direto: pausa por contato, aviso com resumo e código para o `handoff_destino` (template `handoff_template` no WhatsApp), comando `/retomar <código>` só aceito do destino.
- Job `retomada_automatica` a cada minuto e aviso de retomada.
- Canal escolhível nas telas 6 e 8.
- Testes: assinaturas dos dois canais; `/retomar` de outro número vira mensagem comum; retomada automática no horário; deduplicação por canal.

Dependências: Fases 2, 3 e 4.

Critério de aceite:
- Crio pelo menu um agente no Telegram e outro no WhatsApp oficial, e os dois respondem texto, áudio e imagem.
- Peço humano no Telegram, o grupo da empresa recebe o aviso com o resumo, o agente para de responder e volta quando mando `/retomar` com o código.
- Peço humano no WhatsApp, o número da empresa recebe o aviso e, sem comando, o agente volta sozinho depois do tempo configurado.

O que o operador precisa fazer:
- Criar o bot no BotFather e o grupo de handoff com o bot dentro.
- Criar o app na Meta, número de teste, token permanente, app secret e o template de aviso de handoff aprovado.

Commit: `feat: canais diretos WhatsApp oficial e Telegram com handoff`

## Fase 6: Base de conhecimento

Objetivo: cada agente responde com base nos documentos do próprio cliente.

O que entra:
- Entidades Documento e Trecho; modelo de embeddings da Instalação.
- API: enviar, listar e remover documento.
- Job `ingerir_documento`: PDF, DOCX, TXT e MD, trechos de cerca de 800 tokens, embeddings em lote.
- Tool `buscar_base_conhecimento` registrada em todo agente.
- Opção "Subir base de conhecimento" no menu e passo opcional na tela 6.
- Testes: busca de um agente nunca devolve trecho de outro agente ou cliente; documento removido some da busca; hash repetido recusado.

Dependências: Fase 4.

Critério de aceite:
- Subo pelo menu a tabela de preços de um cliente e o agente dele responde o preço certo.
- Pergunto a mesma coisa ao agente de outro cliente e ele não sabe.
- Removo o documento e o agente deixa de citar o preço.

O que o operador precisa fazer:
- Enviar para a VPS documentos reais de teste.

Commit: `feat: base de conhecimento com RAG por agente`

## Fase 7: Polimento e distribuição

Situação: parcial, repositório público, README e licença prontos.

Objetivo: qualquer aluno instala pelo comando público e o critério de sucesso é verificado.

O que entra:
- `install.sh` publicado em página estática em `setup.<dominio>`, baixando a release marcada e conferindo checksum.
- Backup diário com timer do systemd e retenção de 14 dias; job `limpar_midia` de 90 dias.
- Checagens finais do setup: memória e disco mínimos, aviso de proxy da Cloudflare, `.env` com permissão 600.
- Revisão do texto da licença e do banner com o nome definitivo.
- Revisão do `modelos/AGENTS.md.tmpl` contra o critério de até 100 linhas e só conteúdo não descobrível.
- Lista do que ficou adiado, gravada em spec/decisoes.md.

Dependências: Fases 1 a 6.

Critério de aceite:
- Numa VPS vazia nova, rodo `bash <(curl -sSL setup.<dominio>)` e em menos de 1 hora, sem editar código, tenho um agente respondendo com áudio, imagem, base de conhecimento e handoff.
- Vejo o arquivo de backup do dia na VPS e consigo restaurar o banco numa VPS nova seguindo o resumo final.
- Um aluno que não participou do desenvolvimento repete a instalação sozinho.

O que o operador precisa fazer:
- Definir o domínio público do setup e a licença.
- Pedir para um aluno testar a instalação.

Commit: `chore: distribuição pública, backup e polimento da primeira versão`
