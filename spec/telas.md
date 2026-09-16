# Etapa 3: Telas e ações da primeira versão

As telas são telas de terminal do setup, exibidas via SSH. Não existe front nesta versão. Funções de referência: ver spec/visao.md, Funções essenciais da primeira versão. Papéis: ver spec/usuarios.md.

## Telas da primeira versão

### 1. Boas-vindas

- Objetivo: apresentar o script e obter o aceite antes de qualquer alteração na VPS.
- Quem acessa: operador.
- Mostra: nome "Asimov Academy" em ASCII grande, versão do script, moldura com texto curto sobre o que o setup instala, licença e crédito à Asimov Academy.
- Ações: `Y` aceita e segue; `N` sai sem alterar nada.
- Licença: MIT, arquivo `LICENSE` na raiz, copyright Asimov Academy.

### 2. Iniciando

- Objetivo: preparar a VPS vazia sem perguntar nada.
- Quem acessa: operador.
- Mostra: banner "INICIANDO" com a versão e a lista de passos no formato `N/T - [ OK ] - descrição`, um por linha, conforme executam. Passo que já estava pronto aparece como `[ OK ]` sem refazer; passo que falha aparece como `[ ERRO ]`.
- Passos: conferir Ubuntu 24.04, conferir memória e disco mínimos, update, upgrade, instalar sudo, apt-utils, dialog, jq, git, python3, Docker e demais utilitários do setup.
- Ações: nenhuma; só acompanhar.

### 3. Dados da instalação

- Objetivo: coletar tudo que a instalação precisa de uma vez.
- Quem acessa: operador.
- Mostra: uma pergunta por vez.
- Ações:
  - Informar o domínio base (o setup usa `bot.<dominio>`).
  - Informar o e-mail para o SSL.
  - Escolher o agente de código: Claude Code ou Codex.
  - Escolher o provedor de IA: OpenAI, Anthropic ou Gemini. O setup mostra os modelos padrão que vão ser usados em conversa, auxiliar, visão, transcrição e embeddings.
  - Colar a chave do provedor escolhido. Se for Anthropic, colar também a chave de OpenAI ou Gemini para áudio e embeddings. Cada chave é testada na hora; chave inválida é pedida de novo com o motivo.
  - Revisar o resumo das respostas e confirmar ou corrigir antes de seguir.

### 4. Checagem do domínio

- Objetivo: garantir que `bot.<dominio>` aponta para a VPS antes de emitir o SSL.
- Quem acessa: operador.
- Mostra: IP público da VPS, IP para o qual o domínio resolve hoje e o status.
- Ações: se não aponta, mostra antes de tudo o registro a criar (tipo A, nome bot, valor IP da VPS, TTL 300) e onde fica no painel dos registradores mais comuns; verifica sozinho a cada 15 s, com Enter para verificar na hora e S para sair (a retomada volta para esta tela). Avisa quando o registro aponta para outro IP, quando passa pelo proxy da Cloudflare e quando existe AAAA (IPv6), que atrapalha o certificado.

### 5. Instalação

- Objetivo: instalar e subir a estrutura do agente.
- Quem acessa: operador.
- Mostra: passos numerados `N/T - [ OK ] - descrição` (firewall, Node, Python e uv, agente de código escolhido, SDK do provedor de IA escolhido, banco, proxy com SSL, projeto base, serviços no ar, health check da API em `https://bot.<dominio>`).
- Ações: nenhuma; só acompanhar.

### 6. Primeiro agente

- Objetivo: deixar um agente funcionando num canal ao final da primeira execução.
- Quem acessa: operador.
- Ações:
  - Informar o cliente (empresa) e o nome do agente.
  - Escolher o canal: WhatsApp oficial, Telegram ou Chatwoot.
  - Chatwoot: colar a URL do Chatwoot e o token de acesso de um administrador; escolher a conta e a caixa de entrada num menu. O setup cria o Agent Bot já com a URL do webhook e liga o bot na caixa. O token do administrador não é guardado.
  - WhatsApp ou Telegram direto (fase 5): colar as credenciais do canal (testadas na hora) e informar o número ou grupo que recebe o handoff.
  - Opcional: informar a pasta na VPS com documentos da base de conhecimento (assumido: arquivos enviados antes para a VPS). Pode pular e subir depois pelo menu.
- Mostra ao final: confirmação de que o canal foi conectado. Chatwoot e Telegram não exigem colar nada; no WhatsApp oficial, a URL do webhook e onde colar na Meta.

### 7. Resumo final

- Objetivo: fechar a instalação e orientar o próximo passo.
- Quem acessa: operador.
- Antes de mostrar: gera `AGENTS.md` e `CLAUDE.md` na raiz do projeto instalado (regras em spec/arquitetura.md, seção 11) e faz o primeiro commit do projeto.
- Mostra: o que foi instalado, provedor de IA e modelos, URL da API, agentes criados com canal e webhook, caminho do projeto, caminho do log e os próximos passos (entrar na pasta do projeto e abrir Claude Code ou Codex, que já leem o `CLAUDE.md` ou `AGENTS.md`).
- Ações: nenhuma.

### 8. Menu (ao rodar o setup de novo com a instalação concluída)

- Objetivo: operar os agentes sem front.
- Quem acessa: operador.
- Mostra: banner com o nome e a versão, e as opções numeradas.
- Ações:
  - Criar agente (mesmo fluxo da tela 6).
  - Listar agentes: cliente, nome, canal, destino do handoff, URL do webhook e status.
  - Editar agente: nome, credenciais do canal, destino do handoff, tempo de retomada automática.
  - Remover agente: pede confirmação digitando o nome do agente.
  - Subir base de conhecimento: escolher o agente e a pasta ou arquivo; listar e remover documentos já carregados.
  - Ver consumo e falhas: por cliente e agente, nos últimos 7 e 30 dias, total de turnos, tokens, custo estimado e últimas falhas (derivado).
  - Sair.

### Tratamento de erro (vale para todas as telas)

- Falha passageira (apt travado por atualização automática, rede, DNS, API fora) é repetida sozinha algumas vezes com espera crescente.
- Se persistir: linha `[ ERRO ]`, motivo em português, o que fazer e caminho do log. O setup para.
- Ao rodar de novo o mesmo comando, o setup retoma do passo que falhou, sem refazer os concluídos e sem perguntar de novo o que já foi respondido.

## Fluxos sem tela

Estes não têm tela no terminal, mas fazem parte da primeira versão:

- **Conversa (contato):** manda texto, áudio, imagem ou documento no canal; o agente aguarda o buffer, transcreve áudio, lê imagem e documento, consulta a base de conhecimento, mostra digitando e responde em uma ou mais mensagens.
- **Handoff (atendente):** no Chatwoot, recebe a conversa transferida e responde lá; devolver a conversa para pendente retoma o agente. No canal direto, recebe o aviso com o resumo e um código curto no número ou grupo cadastrado, e retoma o agente respondendo `/retomar <código>` (derivado).

## Fluxo de primeiro acesso

1. Operador aponta `bot.<dominio>` para o IP da VPS (pode fazer depois, a tela 4 espera).
2. Roda `bash <(curl -sSL setup.dominio.art.br)` na VPS vazia.
3. Boas-vindas e aceite (tela 1).
4. Iniciando (tela 2).
5. Dados da instalação (tela 3).
6. Checagem do domínio (tela 4).
7. Instalação (tela 5).
8. Primeiro agente (tela 6) e cola o webhook no canal.
9. Resumo final (tela 7). Manda uma mensagem de teste no canal.

## Fluxo de uso diário

- **Operador:** roda o setup de novo para abrir o menu quando precisa criar, editar ou remover agente, ou atualizar a base de conhecimento. O resto do tempo evolui o projeto em vibecoding com Claude Code ou Codex.
- **Contato:** conversa com o agente no canal.
- **Atendente humano:** atende as conversas passadas pelo handoff e devolve ao agente.

## Mudanças em relação a spec/visao.md

Adicionadas nesta etapa (já refletidas na lista de spec/visao.md):

- Tela de boas-vindas com nome, versão, licença e aceite (função 2).
- Preparação automática da VPS com passos numerados (função 3).
- Checagem do domínio antes do SSL (função 5).
- Tratamento de erro com repetição automática e retomada (função 14).
- Menu ao rodar de novo (função 15).
- Resumo final (função 16).
- Nome provisório definido: Asimov Academy.

Adicionadas depois da etapa 4, a pedido do operador:

- Escolha do provedor de IA com instalação do SDK (função 4, telas 3 e 5).
- Geração de `CLAUDE.md` e `AGENTS.md` no projeto instalado (função 18, tela 7).

Adicionada na verificação de consistência da etapa 5:

- Opção de menu "Ver consumo e falhas" (função 17 não tinha tela).

## Critério de sucesso

Um aluno parte de uma VPS Ubuntu 24.04 vazia com domínio e, em menos de 1 hora e sem editar código, tem um agente respondendo no WhatsApp, Telegram ou Chatwoot, com áudio, imagem, base de conhecimento e handoff funcionando (assumido). Uma semana depois, está evoluindo o agente em vibecoding no projeto gerado.

## Implicações técnicas

- Operações que o backend expõe na API (rotas administrativas protegidas conforme spec/usuarios.md; o setup e o menu chamam a API, não o banco):
  - verificar saúde da API
  - criar cliente; listar clientes
  - criar agente; listar agentes; ver agente com URL de webhook; editar agente; remover agente
  - descobrir o que o acesso do operador enxerga no canal (contas e caixas de entrada no Chatwoot)
  - conectar o canal ao criar o agente (criar e ligar o Agent Bot no Chatwoot)
  - registrar webhook no Telegram
  - enviar documento para a base de conhecimento; listar documentos; remover documento
  - ver consumo e falhas por cliente e agente
  - receber webhook do WhatsApp (incluindo o GET de verificação da Meta), do Telegram e do Chatwoot
  - pausar agente para um contato (handoff); retomar agente para um contato
- Operações do próprio script (sem API, pois a API ainda não existe nesse momento): checar sistema, instalar pacotes, testar chaves de IA, checar DNS, emitir SSL, subir serviços, gerar `CLAUDE.md` e `AGENTS.md`, iniciar o git do projeto.
- Regras de negócio verificadas no backend:
  - toda operação filtra por cliente; agente de um cliente nunca acessa dados de outro
  - criar e editar agente valida credenciais e canal antes de gravar
  - remover agente remove ou desativa webhook, credenciais e base de conhecimento dele
  - webhook só processa com verificação de origem válida e para agente ativo
  - mensagem de contato com agente pausado não gera resposta
  - comando de retomada só é aceito do número ou grupo de handoff cadastrado
  - mensagens repetidas pelo canal (reentrega de webhook) não geram resposta duplicada
- Avisos e processamento agendado:
  - aviso de handoff: disparado quando o agente decide transferir; enviado pelo canal do agente ao número ou grupo cadastrado (WhatsApp exige mensagem de template fora da janela de 24 horas) ou pela API do Chatwoot
  - fim do buffer: processamento atrasado por alguns segundos após a última mensagem do contato, reiniciado a cada nova mensagem
  - retomada automática após handoff: agendada pelo tempo configurado no agente
  - renovação do SSL: automática pelo proxy, sem job próprio
  - digitando: enviado ao canal durante o processamento (Telegram `sendChatAction`, WhatsApp indicador de digitação, Chatwoot `toggle_typing`)
- Uploads: documentos da base de conhecimento enviados pelo operador a partir de arquivos na VPS; mídias recebidas dos contatos (áudio, imagem, documento) baixadas das APIs dos canais para processamento.
- Tempo real: nenhuma tela exige atualização em tempo real. O setup mostra progresso local do script.
- Script: estado de progresso gravado em arquivo na VPS para permitir retomada; toda etapa idempotente; saída de log completa em arquivo, tela mostra só o resumo por passo.
