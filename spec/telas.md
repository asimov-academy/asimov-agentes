# Etapa 3: Telas e ações da primeira versão

As telas são telas de terminal do setup, exibidas via SSH. Não existe front nesta versão. Toda escolha e todo Sim/Não andam com as setas e confirmam com Enter (números de 1 a 9 e S/N como atalho). No menu e nos comandos `asimov`, Esc em qualquer pergunta volta à tela anterior sem salvar: da ação para o menu, da mudança para a ficha do agente, e do menu para fora; na primeira instalação não há tela anterior e o Esc não faz nada. Cada tela nova limpa o terminal e redesenha o banner; o que o operador precisa ler antes de voltar ao menu (listagem, consumo, resultado de criar ou remover) espera um Enter. Funções de referência: ver spec/visao.md, Funções essenciais da primeira versão. Papéis: ver spec/usuarios.md.

## Telas da primeira versão

### 1. Boas-vindas

- Objetivo: apresentar o script e obter o aceite antes de qualquer alteração na VPS.
- Quem acessa: operador.
- Mostra: nome "Asimov Academy" em ASCII grande, versão do script, moldura com texto curto sobre o que o setup instala, licença e crédito à Asimov Academy.
- Ações: `Y` aceita e segue; `N` sai sem alterar nada.
- Licença: MIT, arquivo `LICENSE` na raiz, copyright Asimov Academy.

### 1b. Uso

- Objetivo: definir antes de instalar se a instalação atende só a empresa do operador ou empresas clientes (revenda).
- Quem acessa: operador.
- Ações: escolher "Só para a minha empresa" ou "Para empresas clientes".
- Efeito: modo empresa cria uma empresa só no primeiro agente e todo agente novo vai para ela; modo revenda pergunta, a cada agente novo, empresa existente ou nova. Internamente a plataforma é sempre multitenant.

### 2. Iniciando

- Objetivo: preparar a VPS vazia sem perguntar nada.
- Quem acessa: operador.
- Mostra: banner "INICIANDO" com a versão e a lista de passos no formato `N/T - [ OK ] - descrição`, um por linha, conforme executam. Passo que já estava pronto aparece como `[ OK ]` sem refazer; passo que falha aparece como `[ ERRO ]`.
- Passos: conferir Ubuntu 24.04, conferir memória e disco mínimos, update, upgrade, instalar sudo, apt-utils, dialog, jq, git, python3, Docker e demais utilitários do setup.
- Ações: nenhuma; só acompanhar.

### 3. Configuração e modelos de IA

- Objetivo: coletar domínio, e-mail do SSL, agente de código e os modelos de IA padrão da instalação.
- Quem acessa: operador.
- Ações:
  - Informar o domínio (aceita colar com `https://`, `bot.` ou barra) e o e-mail do SSL.
  - Escolher o agente de código: Claude Code ou Codex.
  - Para cada função, escolher provedor e modelo: resposta ao contato, fallback (opcional, usado se a resposta falhar), visão (imagens e PDF) e transcrição de áudio. Provedores: OpenAI, Anthropic, Gemini e Groq (transcrição: OpenAI, Groq ou Gemini).
  - A chave de cada provedor é pedida uma vez e testada na hora.
  - Os modelos aparecem num menu listado pela API do próprio provedor, com sugestões primeiro e opção de digitar outro.
  - Conferir o resumo dos modelos e confirmar.

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

### 6. Agente no Chatwoot (primeiro agente e `asimov novo-agente`)

- Objetivo: deixar um agente respondendo numa caixa do Chatwoot.
- Quem acessa: operador.
- Ações, nesta ordem:
  - URL do Chatwoot (lembrada da última vez). O token de acesso de um administrador é pedido só se não houver um guardado para essa URL, ou se o Chatwoot recusar o guardado; o que funcionar fica guardado criptografado.
  - Conta e caixa de entrada em menu; com uma opção só, escolhe sozinho.
  - Quem recebe o handoff: times e atendentes da conta, ou quem estiver na caixa (sem atribuir).
  - Nome do agente.
  - Empresa: no modo empresa, a primeira vez pede o nome da empresa (sugere o nome da conta do Chatwoot) e depois usa sempre a mesma; no modo revenda, menu com as empresas existentes e "nova empresa".
- Mostra ao final: uma linha confirmando o agente no ar, a caixa e a empresa, e outra com o destino do handoff. A API cria o Agent Bot já com a URL do webhook e liga na caixa.
- A partir da fase 5 a tela começa pelo canal: Chatwoot (este fluxo), WhatsApp oficial (credenciais da Meta e template de handoff), WhatsApp não oficial pela WAHA (número ou grupo do handoff, QR code desenhado no terminal até conectar, aviso de risco de bloqueio do número) ou nativo (só nome e empresa).

### 7. Resumo final

- Objetivo: fechar a instalação e orientar o próximo passo.
- Quem acessa: operador.
- Antes de mostrar: gera `AGENTS.md` e `CLAUDE.md` na raiz do projeto instalado (regras em spec/arquitetura.md, seção 11) e faz o primeiro commit do projeto.
- Mostra: o que foi instalado, provedor de IA e modelos, URL da API, agentes criados com canal e webhook, caminho do projeto, caminho do log e os próximos passos (entrar na pasta do projeto e abrir Claude Code ou Codex, que já leem o `CLAUDE.md` ou `AGENTS.md`).
- Ações: nenhuma.

### 8. Comando `asimov` e setup rodado de novo

- Objetivo: operar os agentes sem front.
- Quem acessa: operador.
- Rodar o setup de novo numa instalação concluída pergunta o que faltar de versões novas (modo, modelos), reconstrói se o código mudou, mostra o resumo e abre o menu. `asimov atualizar` para no resumo.
- `asimov` sem argumento abre o mesmo menu. Cada ação também existe como subcomando: `novo-agente`, `agentes`, `editar`, `remover`, `consumo`, `handoff` (desde a v0.4.0), `atualizar` e `ajuda`.
- Atualizar para a v0.4.0 pergunta uma vez o destino do handoff dos agentes que não têm.
- Ações do menu:
  - Criar agente (mesmo fluxo da tela 6).
  - Conversar com agente (fase 5): escolhe um agente nativo e conversa no terminal; cada linha é uma mensagem do contato, a resposta aparece depois do digitando; `/nova` começa outra conversa e Esc volta.
  - Listar agentes: por empresa, nome, canal, modelo de resposta, destino do handoff, status e URL do webhook.
  - Editar agente: escolhe o agente, vê a configuração e muda nome (também o nome do bot no Chatwoot; se o Chatwoot estiver fora, oferece salvar só na plataforma), tempo de buffer, mensagens por resposta, digitação (caracteres por segundo e teto por mensagem), ferramentas (lista de marcar: calculadora e busca na web), modelos (resposta, fallback, resumo do handoff, visão, áudio; só provedores com chave) ou destino do handoff. Vale na próxima mensagem. Credenciais do canal e tempo de retomada automática entram com os canais diretos (fase 5): no Chatwoot as credenciais são do bot criado pelo setup e a retomada é devolver a conversa para pendente.
  - Remover agente: pede o nome do agente para confirmar e apaga o bot no Chatwoot junto; se o Chatwoot estiver fora, oferece remover deixando o bot lá. No modo revenda, empresa que ficou sem agentes pode ser removida junto.
  - Token do Chatwoot: mostra onde há token guardado e permite esquecê-lo.
  - Subir base de conhecimento (fase 6): escolher o agente e a pasta ou arquivo; listar e remover documentos já carregados.
  - Ver consumo e falhas: escolhe uma empresa ou todas; por empresa e agente, últimos 7 e 30 dias lado a lado, com turnos, tokens e custo estimado em dólar, e as últimas falhas (derivado).
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

Um aluno parte de uma VPS Ubuntu 24.04 vazia com domínio e, em menos de 1 hora e sem editar código, tem um agente respondendo no WhatsApp (oficial ou WAHA) ou no Chatwoot, com áudio, imagem, base de conhecimento e handoff funcionando (assumido). Uma semana depois, está evoluindo o agente em vibecoding no projeto gerado.

## Implicações técnicas

- Operações que o backend expõe na API (rotas administrativas protegidas conforme spec/usuarios.md; o setup e o menu chamam a API, não o banco):
  - verificar saúde da API
  - criar cliente; listar clientes
  - criar agente; listar agentes; ver agente com URL de webhook; editar agente; remover agente
  - descobrir o que o acesso do operador enxerga no canal (contas e caixas de entrada no Chatwoot)
  - conectar o canal ao criar o agente (criar e ligar o Agent Bot no Chatwoot)
  - criar sessão na WAHA e mostrar o QR code até conectar
  - conversar com agente nativo pelo terminal
  - enviar documento para a base de conhecimento; listar documentos; remover documento
  - ver consumo e falhas por cliente e agente
  - receber webhook do WhatsApp oficial (incluindo o GET de verificação da Meta), da WAHA e do Chatwoot
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
  - digitando: enviado ao canal durante o processamento (WAHA `startTyping`, WhatsApp oficial indicador de digitação, Chatwoot `toggle_typing`, nativo no terminal)
- Uploads: documentos da base de conhecimento enviados pelo operador a partir de arquivos na VPS; mídias recebidas dos contatos (áudio, imagem, documento) baixadas das APIs dos canais para processamento.
- Tempo real: nenhuma tela exige atualização em tempo real. O setup mostra progresso local do script.
- Script: estado de progresso gravado em arquivo na VPS para permitir retomada; toda etapa idempotente; saída de log completa em arquivo, tela mostra só o resumo por passo.
