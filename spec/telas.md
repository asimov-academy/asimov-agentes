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

### 3. Configuração

- Objetivo: coletar domínio, e-mail do SSL e o assistente de código. Nada de IA aqui (v0.20.0): modelo e chave são de cada agente, na tela 6.
- Quem acessa: operador.
- Ações:
  - Informar o domínio dos agentes. Aceita colado de qualquer jeito (`https://`, `www.`, `bot.`, `app.`, porta, caminho, barra ou ponto no fim, maiúsculas) e mostra o que entendeu.
  - Informar o e-mail do SSL.
  - Escolher o assistente para evoluir os agentes: Claude Code ou Codex.

### 4. Checagem do domínio

- Objetivo: garantir que `bot.<dominio>` aponta para a VPS antes de emitir o SSL.
- Quem acessa: operador.
- Mostra: IP público da VPS, IP para o qual o domínio resolve hoje e o status.
- Ações: se não aponta, mostra antes de tudo o registro a criar (tipo A, nome bot, valor IP da VPS, TTL 300) e onde fica no painel dos registradores mais comuns; verifica sozinho a cada 15 s, com Enter para verificar na hora e S para sair (a retomada volta para esta tela). Avisa quando o registro aponta para outro IP, quando passa pelo proxy da Cloudflare e quando existe AAAA (IPv6), que atrapalha o certificado.

### 5. Instalação

- Objetivo: instalar e subir a estrutura do agente.
- Quem acessa: operador.
- Mostra: os onze passos numerados `N/T ✓ descrição` (firewall, Node, uv, assistente de código escolhido, senhas e chaves, plataforma, banco e Redis, tabelas, API e worker com HTTPS, API respondendo e certificado em `https://bot.<dominio>`). A imagem leva os SDKs dos quatro provedores de IA: nada de SDK escolhido na instalação desde a v0.20.0.
- Ações: nenhuma; só acompanhar.

### 5a. Conta de IA (vínculo)

- Objetivo: com a plataforma no ar, entrar na conta do assistente escolhido na tela 3, que é o que liga o copiloto do painel.
- Mostra: o ganho em duas linhas (o copiloto cria e ajusta agente conversando no painel) e que ele roda pela assinatura do operador (Claude Pro ou Max, ChatGPT Plus ou Pro), sem chave de API e sem custo por token.
- Ações: Sim roda o login do CLI no próprio terminal (Codex por device code, Claude Code pelo endereço que ele mostra) e confere no fim. Não deixa `asimov ia` para depois, e a instalação segue inteira, só sem copiloto. Perguntada uma vez.
- O segredo do login fica onde o CLI oficial guarda; o `.env` só registra que existe vínculo, com qual CLI e em que conta.
- `asimov ia` depois: vincular, trocar de assistente, ver a situação e desvincular. Também é item do menu ("Conta de IA").

### 5b. Painel no navegador (oferta)

- Objetivo: com o essencial no ar, oferecer o painel antes do primeiro agente, para o operador poder criá-lo por lá.
- Mostra: o que o painel faz e o registro DNS que ele exige, com o subdomínio (`app.<dominio>`) e o IP da VPS.
- Ações: Sim liga o painel (subdomínio explicado com o domínio real, aceita o endereço colado, recusa `bot`; espera o DNS; mostra o código de primeiro acesso e espera um Enter antes de limpar a tela). Não deixa o comando `asimov painel` para depois. Perguntada uma vez.
- Com o painel ligado, a tela 6 começa perguntando onde criar o primeiro agente: no painel ou no terminal. O resumo final mostra um código de primeiro acesso enquanto o painel não tiver conta.

### 6. Agente no Chatwoot (primeiro agente e `asimov novo-agente`)

- Todo canal, logo depois da escolha do canal (v0.20.0): a IA que responde o contato. Provedor (OpenAI, Anthropic, Gemini ou Groq), chave só se a instalação ainda não tiver a desse provedor (testada e guardada cifrada pela API, vale para todo agente) e modelo, numa lista que vem do provedor com as sugestões primeiro e a opção de digitar. Resumo, imagem e áudio nascem no mesmo provedor; com Anthropic e nenhum outro provedor com chave, pergunta também quem transcreve áudio.

- Objetivo: deixar um agente respondendo numa caixa do Chatwoot.
- Quem acessa: operador.
- Ações, nesta ordem:
  - URL do Chatwoot (lembrada da última vez). O token de acesso de um administrador é pedido só se não houver um guardado para essa URL, ou se o Chatwoot recusar o guardado; o que funcionar fica guardado criptografado.
  - Conta e caixa de entrada em menu; com uma opção só, escolhe sozinho.
  - Quem recebe o handoff: times e atendentes da conta, ou quem estiver na caixa (sem atribuir).
  - Nome do agente.
  - Empresa: no modo empresa, a primeira vez pede o nome da empresa (sugere o nome da conta do Chatwoot) e depois usa sempre a mesma; no modo revenda, menu com as empresas existentes e "nova empresa".
- Mostra ao final: uma linha confirmando o agente no ar, a caixa e a empresa, e outra com o destino do handoff. A API cria o Agent Bot já com a URL do webhook e liga na caixa.
- A partir da fase 5 a tela começa pelo canal: Chatwoot (este fluxo), WhatsApp pela WAHA (v0.9.0: aviso de que a API é não oficial, com confirmação antes de qualquer coisa, sobe a WAHA na primeira vez, pede nome, empresa, ferramentas e horas até o agente voltar sozinho, cria a sessão, desenha o QR code no terminal até o número parear, com o aparelho aparecendo no celular como `Agente (Empresa)` e só então pergunta quem recebe o handoff: um número digitado ou um grupo do próprio número, escolhido numa lista que aceita busca pelo nome quando há muitos; avisa do risco de bloqueio e sugere um chip separado), WhatsApp oficial (v0.15.0: explica que é a Cloud API, homologada e cobrada por conversa, e que o número não roda no celular; pede a conta de WhatsApp Business, o token permanente e o segredo do app, lista os números da conta para escolher, pergunta nome, empresa, ferramentas, horas até voltar sozinho e quem o agente atende, e por fim o número que recebe o handoff e o template aprovado que leva o aviso, mostrando o texto sugerido quando não há nenhum; a criação aponta o webhook no próprio número, sem colar URL no painel da Meta) ou nativo (nome, empresa e ritmo das respostas: "Rápido, para testar" com buffer de 2 s e 1 s de digitando por mensagem, "Como no WhatsApp" com os padrões dos canais, ou tempos escolhidos; mostra onde fica o prompt). Todo canal termina na lista de ferramentas, toda desmarcada, e no nível de emoji das respostas (nenhum, pouco, médio ou muito; nenhum por padrão): o agente nasce cru, com `persona.md` de uma linha, e se ajusta depois em Editar agente ou em vibecoding (v0.8.11).

### 7. Resumo final

- Objetivo: fechar a instalação e orientar o próximo passo.
- Quem acessa: operador.
- Antes de mostrar: gera `AGENTS.md` e `CLAUDE.md` na raiz do projeto instalado (regras em spec/arquitetura.md, seção 11) e faz o primeiro commit do projeto.
- Mostra: o que foi instalado, URL da API, endereço e código de primeiro acesso do painel (se ligado e sem conta), agentes criados com canal e webhook, caminho do projeto, caminho do log, a conta de IA vinculada quando existe, e os próximos passos (entrar na pasta do projeto e abrir Claude Code ou Codex, que já leem o `CLAUDE.md` ou `AGENTS.md`).
- Ações: nenhuma.

### 8. Comando `asimov` e setup rodado de novo

- Objetivo: operar os agentes sem front.
- Quem acessa: operador.
- Rodar o setup de novo numa instalação concluída pergunta o que faltar de versões novas (modo), reconstrói se o código mudou, mostra o resumo e abre o menu. `asimov atualizar` para no resumo.
- `asimov` sem argumento abre o mesmo menu. Cada ação também existe como subcomando: `novo-agente`, `conversar` (desde a v0.8.0), `agentes`, `editar`, `remover`, `consumo`, `handoff` (desde a v0.4.0), `painel`, `ia` (desde a v0.25.0), `diagnostico`, `atualizar` e `ajuda`.
- Atualizar para a v0.4.0 pergunta uma vez o destino do handoff dos agentes que não têm.
- Ações do menu:
  - Criar agente (mesmo fluxo da tela 6).
  - Conversar com agente (v0.8.0; qualquer canal desde a v0.8.2): escolhe um agente e conversa no terminal; com agente de outro canal, avisa que é conversa de teste e nada vai para o canal. Cada linha é uma mensagem do contato. Acima da linha em edição, uma linha animada mostra a etapa (esperando você terminar, com contagem do buffer; na fila; pensando, com segundos; digitando; terminando o turno). A resposta chega sem apagar o que já foi digitado e, no fim de cada turno, uma linha resume tempo total, modelo e quanto pensou, tokens, custo e ferramentas usadas (ou o erro do modelo). Handoff mostra motivo, resumo e código, e o agente fica calado; `/retomar` devolve a conversa ao agente, `/nova` começa outra conversa, `/sair` ou Esc volta. Criar um agente nativo pelo menu oferece conversar na hora.
  - Listar agentes: por empresa, nome, canal, modelo de resposta, destino do handoff, status e URL do webhook.
  - Criação e edição no Chatwoot perguntam também em quantas horas o agente volta sozinho se o atendente esquecer de devolver a conversa (v0.11.0).
  - Editar agente: escolhe o agente, vê a configuração. Agente nativo tem "Conectar a um canal" no lugar de Handoff (v0.8.2): escolhe o canal (Chatwoot, WhatsApp oficial ou WhatsApp pela WAHA), caixa ou pareamento e destino do handoff; se o ritmo for o de teste, oferece o do WhatsApp. Agente do WhatsApp oficial tem "WhatsApp" no lugar de Handoff (v0.15.0): confere o número na Meta, troca quem recebe o handoff junto com o template do aviso, as horas até o agente voltar sozinho, quem pode falar com ele e refaz o webhook na Meta (para quando alguém mexe na configuração pelo painel). Agente da WAHA tem "WhatsApp" no lugar de Handoff (v0.9.0): mostra o número pareado, pareia de novo (trocar de número), troca quem recebe o handoff, as horas até o agente voltar sozinho e quem pode falar com ele. A tela explica que responder pelo aparelho cala o agente e que 👍 na conversa o traz de volta (v0.10.0). Muda nome (também o nome do bot no Chatwoot; se o Chatwoot estiver fora, oferece salvar só na plataforma), tempo de buffer, mensagens por resposta, digitação (caracteres por segundo e teto por mensagem), ferramentas (lista de marcar: calculadora e busca na web), emoji, modelos (resposta, fallback, resumo do handoff, visão, áudio; provedor sem chave pede a chave na hora) ou destino do handoff. Vale na próxima mensagem. No Chatwoot as credenciais são do bot criado pelo setup e a retomada é devolver a conversa para pendente; por isso lá não há tempo de retomada.
  - Remover agente: pede o nome do agente para confirmar e apaga o bot no Chatwoot junto; se o Chatwoot estiver fora, oferece remover deixando o bot lá. No modo revenda, empresa que ficou sem agentes pode ser removida junto.
  - Painel no navegador: liga ou desliga o painel e gera o código de primeiro acesso.
  - Conta de IA (v0.25.0): mostra o assistente, a conta vinculada e se o copiloto do painel está ligado; vincula, troca de assistente e desvincula. Trocar de assistente pede o login do novo, porque a imagem do copiloto leva o CLI dentro.
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
8. Oferta do painel (tela 5b).
9. Primeiro agente (tela 6), no painel ou no terminal, com a IA dele.
10. Resumo final (tela 7). Manda uma mensagem de teste no canal.

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
