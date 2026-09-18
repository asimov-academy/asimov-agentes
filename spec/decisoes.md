# Decisões

Log de mudanças na spec. Cada entrada: data, o que mudou, por quê e quais arquivos de `spec/` foram atualizados. Entrada mais nova no topo.

## 2026-09-18: O painel ganha a aba Canais

O operador não achava onde ligar um agente a um canal, e não achava porque não existia. Desde a
v0.24.0 todo agente nasce no nativo e conectar virou "um passo depois, na ficha", mas esse passo só
foi construído no terminal: o painel mostrava o canal na ficha como fato e não deixava mudá-lo.
Quem criava um agente pelo navegador ficava com um agente que não atendia ninguém.

Entram duas rotas no painel, as mesmas do menu com a sessão no lugar da chave de administrador
(`POST /painel/api/canais/{canal}/descobrir` e `POST /painel/api/agentes/{id}/canal`), e a aba
**Canais** na ficha, que é a segunda, logo depois do Perfil.

Um limite que a aba conta em vez de esconder: o contêiner da WAHA sobe sob demanda, e subir
contêiner é da VPS, não do navegador. Em instalação que nunca teve agente WhatsApp pelo aparelho, o
primeiro ainda precisa do terminal.

Atualizados: `spec/frontend.md` (5.x, as abas da ficha).

## 2026-09-18: O painel para de prometer o que não é dele

Três cortes no painel, todos vindos de o operador olhar a tela e perguntar o que aquilo faz ali.

**Conhecimento sai do menu.** Era um item apagado com selo de "em breve" e prometia uma base da
instalação. A base é de cada agente e mora na aba Treinamento da ficha dele. A tela `EmBreve` saiu
junto; o arquivo virou `NaoEncontrada.tsx`, que era a outra metade dele.

**Configurações deixa de ser o painel de controle da instalação.** Saíram as chaves de IA (a IA é de
cada agente: a chave agora é pedida e trocada no `EscolheIA`, onde o modelo é escolhido) e o cartão
de Instalação (endereço e contagem não se configuram; são fato, e fato é Visão geral). Ficaram a
conta, o espaço de trabalho, os dados do negócio e um cartão novo, **Assistente de código**, que diz
qual CLI está vinculado e em que conta. Esse sim é escolha da instalação, e é o que move o copiloto.

**O copiloto vira coluna da direita.** Era um botão redondo flutuante que abria o popup grande sobre
tudo. Pedir "deixe a Bella mais objetiva" sem poder olhar a Bella é pedir de memória. Agora ele abre
ao lado do conteúdo, com alargar e estreitar, e o botão mora no rodapé do menu. No celular ele toma a
tela, porque lá não existe "ao lado".

Atualizados: `spec/frontend.md` (menu, 5.0 Configurações e 5.8 Copiloto).

## 2026-09-18: O passo Jeito depois de o operador usar

Três correções vindas de olhar o passo 5 da criação numa instalação de verdade.

**Emoji vira faixa.** Eram quatro botões lado a lado, e botão não mostra que existe ordem entre as
opções: o operador lia os quatro rótulos para descobrir que "pouco" é menos que "médio". Virou uma
faixa que se arrasta, como o volume, no componente novo `frontend/src/design/Faixa.tsx`, que serve
toda escolha de grau (o ritmo da fase 10 vai usar o mesmo). Agente criado antes de a escolha existir
(`emojis: livre`) ganha "Como quiser" como primeira posição, senão salvar outro campo da aba trocaria
o emoji dele sem ninguém pedir.

**Falar só de assuntos da empresa nasce ligado.** Quem contrata um agente de atendimento não quer o
modelo respondendo qualquer coisa em nome da empresa, e quem queria o contrário desliga num toque. O
`server_default` continua `false`, como o do emoji: agente que já existe não muda de comportamento
sozinho, e só o agente novo nasce com a restrição.

**A IA que responde sai da criação.** Mesmo motivo da ferramenta, que saiu na v0.26.0: escolher
provedor e modelo antes de ver o agente falar é decidir sem informação. O nome do campo também não
ajudava ninguém. Agora o agente nasce com a IA que a instalação já tem (o primeiro provedor com
chave, em `ia/chaves.completa`) e o operador troca na aba Configurações da ficha. Instalação sem
chave nenhuma é a única exceção: aí o passo pede uma, senão o agente nasceria sem conseguir falar.
O terminal continua perguntando na criação, e isso é divergência a resolver.

Atualizados: `spec/frontend.md` (passo 5 e aba Comunicação).

## 2026-09-18: Humanização vira a fase 10

O operador trouxe três pesquisas sobre humanização de agentes de atendimento (práticas de mercado,
o que os líderes expõem na interface e o que a PydanticAI oferece) e pediu um plano. A leitura do
código mostrou que boa parte do que elas chamam de estado da arte já está no ar desde a fase 5:
buffer com lock, digitando no ritmo de uma pessoa, resposta em bolhas sem markdown, tom, emoji,
assunto restrito e transferência opcional. O plano ficou com o que falta, em
`docs/plano-humanizacao.md`: ritmo com nome, persona com o que nunca dizer, memória do contato,
sentimento com gatilhos e aviso de IA, e regressão de persona quando a IA reescreve o prompt.

**Vira uma fase, a 10, depois da fase 6.** A alternativa era soltar as duas primeiras etapas como
versão de polimento agora, no molde das v0.21 a v0.24. O operador preferiu a fase inteira: a memória
do contato encosta na base de conhecimento, e as duas mexem no que o agente sabe além da conversa.

**O aviso de que é uma IA nasce desligado**, e o operador marca. Pela lei europeia ele seria
obrigatório desde 2 de agosto de 2026, mas quem atende só no Brasil não está nesse caso, e a fase
entrega a escolha com a frase que explica quando marcar, não a regra ligada por padrão.

**A memória do contato nasce ligada.** Lembrar do que ficou combinado é o que o contato espera de
quem já falou com ele, e é o item com mais efeito na percepção de atendimento humano. Agente criado
antes da fase nasce sem memória e só lembra do que vier depois de ligada.

**O validador de preço e prazo fica para a fase 6.** Recusar a resposta que fala de preço sem
nenhuma ferramenta chamada só funciona quando existe de onde tirar o preço. Hoje quase todo agente
tem zero ferramenta e o preço mora no "sobre a empresa" escrito pelo operador: o validador recusaria
a resposta certa. Na fase 10 a regra é só texto no prompt ("não afirme preço ou prazo que não esteja
no que você recebeu"); o validador entra com a base de conhecimento, ligado em agente com base.

Atualizados: `spec/fases.md` (fase 10), `spec/estado.md` (tabela de fases).

## 2026-09-18: O jeito do agente vira escolha, e o treinamento ganha lugar (v0.26.0)

Primeiro refino depois do copiloto no ar, com o operador usando o painel e apontando o que faltava.

**"Melhorar com IA" passa a rodar pela assinatura.** O botão do passo "Sobre" morria com "nenhum
provedor de IA tem chave nesta instalação" numa instalação que tinha conta de IA vinculada e nenhuma
chave de provedor, que é exatamente o que a v0.25.0 tornou comum. Agora, com vínculo, quem reescreve
é o CLI do operador; sem vínculo, segue a chave. A API não executa o CLI: ela enfileira no worker do
copiloto, que é quem tem o binário e a credencial, e espera o resultado.

**O agente ganha tom, e a transferência para humano vira opcional** (migração `0020`, aditiva):

- **tom**: formal, normal ou descontraído. Muda o jeito, nunca o conteúdo.
- **transfere_para_humano**: desligado, a tool nem é oferecida ao modelo, e nenhum caminho
  automático transfere (falha no turno, arquivo grande). Quem vende sem equipe de atendimento não
  quer o agente prometendo uma pessoa que não existe. Antes, o onboarding dizia "sempre ligada".
- **restringe_temas**: o agente só fala do que é da empresa e devolve o resto ao atendimento.

As três escolhas ficam no mesmo lugar no painel (passo "Jeito" da criação e aba Comunicação da
ficha) e no terminal (`asimov editar` > Jeito de falar), que é a regra de nascer na API e ser
consumido pelos dois.

**Ferramenta sai da criação.** O agente nasce cru, o operador vê como ele fala, e ferramenta e
material entram depois. Escolher calculadora e busca antes de existir uma conversa é pedir uma
decisão sem nenhuma informação.

**O treinamento ganha lugar antes de existir.** Aba nova na ficha, desenhada e vazia, com as cinco
formas de ensinar: texto, site, vídeo, documento e base de conhecimento compartilhada. É onde a
fase 6 vai morar, e é para lá que o fim do onboarding aponta. Sem um lugar combinado, cada tipo de
material nasceria num canto diferente do painel. Referência trazida pelo operador: a tela de
treinamentos do GPT Maker.

Atualizados: spec/dados.md, spec/frontend.md, spec/telas.md, spec/fases.md e spec/estado.md.

## 2026-09-18: Fase 9 validada em VPS, e a spec inteira revisada

O operador percorreu a instalação numa VPS real: atualização para a v0.25.x, login do Claude Code na
tela da instalação, vínculo reconhecido, painel no ar em `app.<dominio>` e o copiloto respondendo
pela assinatura. **Fase 9 concluída e validada**; a fase 8 passou a constar como no ar em VPS, com o
critério de aceite dela ainda por percorrer inteiro (criar e editar agente pelo navegador).

Na mesma passada, a spec foi conferida de ponta a ponta e o que estava velho saiu:

- `spec/visao.md` ainda pedia modelo de IA na instalação (saiu na v0.20.0), não citava a conta de IA
  nem o painel, e listava a atualização da plataforma como fora de escopo, sendo que `asimov
  atualizar` existe desde a v0.1.1.
- `spec/usuarios.md` dizia que não havia autenticação de pessoas no app, o que deixou de valer com o
  painel: hoje há uma conta de operador, com senha em scrypt e primeiro acesso por código.
- `spec/telas.md` descrevia a tela de instalação com um passo de "SDK do provedor escolhido" que não
  existe mais, e o menu sem os itens de painel e conta de IA.
- `spec/frontend.md` dizia `SameSite=Lax`, e o cookie é `Strict` desde a v0.18.0.
- `spec/dados.md` não tinha as chaves do vínculo na entidade Instalação, nem o login do CLI entre os
  dados sensíveis.
- `README.md` prometia um onboarding de agente em oito passos, que virou cinco na v0.24.0.

## 2026-09-18: O copiloto enxerga a credencial do operador (v0.25.2)

Primeiro teste em VPS real. O copiloto apareceu no painel e respondeu "o copiloto não conseguiu
responder desta vez" a qualquer pedido. Três coisas estavam erradas, e nenhuma delas dava para ver
de fora.

**O contêiner subia com os volumes padrão.** O `docker inspect` mostrava
`asimov-agentes/modelos -> /tmp/sem-credencial`, que é o default do Compose para quem nunca
vinculou conta. Contêiner que já existe não pega volume novo, e `copiloto_sobe` saía cedo quando
`COPILOTO_ATIVO` já era 1. Agora ele sempre recria: o que muda entre uma vinculação e outra são
justamente os volumes e o usuário.

**O usuário do contêiner não conseguiria abrir o arquivo.** O login do operador é `600` do dono
dele, e numa VPS Hostinger esse dono é o root; o contêiner rodava como o `app` da imagem (uid
1000). O `user:` do serviço passou a ser o dono da pasta de credencial, gravado no `.env` pelo
vínculo (`CREDENCIAL_IA_UID`).

**Faltava o `~/.claude.json`.** O Claude Code guarda o login em `~/.claude/` e o estado de primeiro
uso num arquivo fora dessa pasta. Sem ele, o CLI no contêiner se acha em primeira execução e sai
sem responder. Ele entra como um segundo volume.

**E o erro chegava cego:** o CLI sai com código 1, stderr vazio e o recado no stdout, que o
`servico.py` descartava. Agora o stdout entra no log e na classificação da mensagem.

## 2026-09-18: O painel sobrevive a `asimov atualizar` (v0.25.1)

`deploy/caddy/painel.caddy` é versionado, com o conteúdo de painel desligado, e o pacote da
atualização passa por cima do bloco que `asimov painel` tinha escrito na VPS. Quem estava com o
painel ligado perdia o host `app.<dominio>` a cada atualização: o `bot` seguia respondendo e o
painel dava falha de TLS, porque o Caddy não conhecia mais aquele host. Só voltava desligando e
ligando o painel de novo.

A atualização passou a reescrever o bloco quando ele sumiu (`painel_garante_caddy`, chamado em
`atualiza()`), e a armadilha virou linha no `AGENTS.md`: arquivo versionado que o setup reescreve
na VPS volta ao conteúdo do repositório a cada atualização.

## 2026-09-18: Conta de IA vinculada na instalação e copiloto no painel (v0.25.0)

O setup instalava o Claude Code ou o Codex e parava aí. Quem nunca abria o CLI ficava com um binário
morto na VPS, e o painel não tinha como ajudar a configurar nada. A conta de IA passa a ser parte da
instalação, e é ela que liga o copiloto do painel.

**A instalação pede o login do CLI escolhido**, logo depois de a plataforma subir e antes da oferta
do painel (`setup/lib/vinculo.sh`, tela `tela_vinculo_ia`). Quem quiser pular pula: a instalação
segue inteira e o painel também, só sem copiloto. Depois, `asimov ia` vincula, troca de assistente,
mostra a situação e desvincula. O menu do operador ganhou "Conta de IA".

**A assinatura é a única forma de pagar o copiloto.** Claude Pro ou Max, ChatGPT Plus ou Pro. Chave
de API não liga o copiloto: quem assina já pagou, e cobrar por token do lado de cá seria cobrar duas
vezes. A contrapartida é o limite por janela da assinatura, que o painel diz com todas as letras
quando acontece.

**A credencial não entra no banco nem no `.env`.** Ela nasce e vive onde o CLI oficial guarda
(`~/.claude/.credentials.json` ou `~/.codex/auth.json`, com a permissão dele), e o contêiner do
copiloto monta essa pasta. O `.env` guarda só `IA_VINCULADA`, `IA_CLI`, `IA_CONTA` e o caminho da
pasta, que é o que o painel precisa para mostrar ou esconder o copiloto. É a regra de credencial do
projeto cumprida pelo caminho mais curto: o segredo não passa por nós.

**O copiloto roda num contêiner próprio, com perfil, no molde da WAHA** (`COPILOTO_ATIVO=1` no
`.env`, lido pelo `dc`). Só ele leva o CLI dentro, e ele só sobe com conta vinculada **e** painel
ligado: quem administra pelo terminal não paga o build. A API enfileira e o worker do copiloto
executa; os dois nunca dividem processo, porque um turno de atendimento precisa ser rápido e um
turno de copiloto pensa por minutos.

**O CLI não escreve na plataforma.** A fronteira é um servidor MCP nosso (`app/copiloto/mcp.py`),
com ferramentas de leitura que respondem na hora e ferramentas `propor_` que só registram uma
proposta. Quem aplica é o backend, no clique do operador. Sem isso, uma frase escondida num prompt
ou numa conversa de contato poderia mudar a configuração de um agente sozinha. As ferramentas de
código do CLI ficam desligadas: o copiloto opera a plataforma, não a VPS.

**Agente novo pelo copiloto nasce no canal nativo.** Conectar a um WhatsApp ou Chatwoot continua no
passo a passo do painel, que é onde se cola token e se lê QR code.

**Bug achado no caminho:** `asimov painel` desligando o painel gravava `PAINEL_ATIVO=` no `.env`, e
a API não subia com um booleano vazio. O `Config` passou a tratar chave vazia como desligada.

Atualizados: spec/arquitetura.md, spec/telas.md, spec/frontend.md, spec/fases.md, spec/dados.md e
spec/estado.md.

## 2026-09-18: A IA vira escolha de cada agente, e a instalação fica só com o essencial (v0.20.0)

O operador instalou numa VPS e apontou o que não fazia sentido. Tudo abaixo veio dessa rodada.

**Modelos saem da instalação.** A tela "Modelos de IA" pedia provedor, chave e modelo de quatro
funções antes de existir agente, e agentes diferentes usam IAs diferentes. Agora a instalação não
pergunta nada de IA. Criar agente, no terminal ou no painel, pergunta a IA que responde o contato;
resumo, imagem e áudio nascem no mesmo provedor (primeira sugestão de `ia/chaves.py`) e mudam em
Editar agente ou na ficha. Anthropic não transcreve: o áudio cai em outro provedor com chave, e sem
nenhum o terminal pergunta quem transcreve.

**Chave de provedor vai para o banco, cifrada** (tabela `chave_provedor`, migração `0017`, em
`acessos/`). O `.env` só é lido no boot, e a chave informada ao criar um agente precisa valer na
hora, sem reiniciar a API. A API testa a chave no provedor antes de guardar e nunca a devolve. API e
worker são processos separados: cada um relê as chaves antes de validar modelo e no começo do turno.
`MODELO_*` e `*_API_KEY` do `.env` de instalação antiga seguem valendo de padrão e de reserva. Isto
muda a regra "segredos só em `.env`": chave de provedor entra na mesma exceção das credenciais de
canal. A imagem passa a levar o SDK dos quatro provedores (`PROVEDORES` fixo). O catálogo de modelos
(filtro por função e sugestões) saiu do Bash e foi para `ia/chaves.py`; o terminal lista pela API
(`/admin/ia/modelos/<provedor>`), porque depois de guardada a chave o setup não a tem mais.

**Ordem da instalação.** O painel era oferecido depois do primeiro agente, quando já não ajudava a
criá-lo. Agora: essencial instalado, oferta do painel e só então o primeiro agente, com a escolha
"no painel" ou "aqui no terminal" quando o painel está ligado.

**Código de primeiro acesso sumia.** `painel_liga` mostrava o código e a tela seguinte limpava o
terminal. Entrou uma pausa depois do código, e o resumo final gera e mostra um código enquanto o
painel não tiver conta.

**Textos.** Boas-vindas sem "Chatwoot" (a plataforma tem vários canais). "Webhooks ficam em
bot.<domínio>" virou "Domínio dos agentes". "Agente de código" virou "Assistente para evoluir os
agentes". A oferta do painel diz o IP do registro DNS. O subdomínio do painel explica com o domínio
real (`app.<dominio>`), aceita o endereço colado inteiro e recusa `bot`.

**Domínio tolerante.** `limpa_dominio` aceita `https://`, `www.`, `bot.`, `app.`, porta, caminho,
barra e ponto no fim, maiúsculas e espaço, e mostra o que entendeu antes de seguir.

spec/telas.md, spec/dados.md, spec/arquitetura.md, spec/estado.md e AGENTS.md.

## 2026-09-18: Onboarding refeito na ordem do operador (v0.24.0)

O operador mostrou o onboarding de um concorrente, disse que achou perfeito e descreveu a ordem que
queria. O nosso virou isso, e três coisas mudaram de fundo:

**Canal saiu da criação.** Todo agente nasce respondendo no painel e no terminal, e conectar a um
WhatsApp ou a um Chatwoot é um passo depois, na ficha. Escolher canal antes parava o operador num
formulário de credencial (URL do Chatwoot, token da Meta, QR code) antes de ele ter visto o agente
falar uma frase. Foram oito passos para cinco: nome, objetivo, empresa, sobre e ajustes.

**Melhorar com IA.** No passo do "sobre", um botão pede à IA da instalação para reescrever o que o
operador digitou (`ia/redacao.py`, rota `POST /painel/api/texto/melhorar`). Nenhum agente existe
ainda nessa hora, então o modelo sai do provedor que tem chave, na sugestão mais barata. O texto do
operador chega delimitado e o prompt diz para tratá-lo como material, nunca como instrução: sem
isso, "ignore o que foi dito antes" dentro da descrição vira ordem para o modelo. Falhando, o campo
continua com o que ele escreveu.

**A prévia saiu.** A conversa de mentira ocupava um terço do popup, e o fluxo termina numa conversa
de verdade com o agente, que é o que mostra o jeito dele falar. `Previa.tsx` foi removido.

O fim virou três caminhos, com conversar em primeiro.

spec/frontend.md, seção 5.2.1.

## 2026-09-18: Cartão de canal mais visual, e o nome técnico dos dois WhatsApp (v0.23.1)

O operador olhou o passo do canal no onboarding e pediu menos texto e mais desenho. O cartão tinha
título, duas frases, a linha do que exige e o aviso aberto em três linhas laranja: mais aviso do que
descrição. Agora ele é logo num quadrado, nome, uma frase curta, o "Precisa:" e o aviso como ícone,
que abre no hover e no foco (`design/Dica.tsx`, só CSS, sem biblioteca).

**Os dois WhatsApp passaram a usar o nome técnico**: "WhatsApp Cloud API" e "WhatsApp WAHA". A
auditoria de copy tinha recomendado o contrário, e o operador decidiu: quem instala esta plataforma
conhece os dois termos, e o nome de fantasia obrigava a traduzir de volta na cabeça. Vale só para
eles; o canal `nativo` continua como "Conversa de teste".

O logo do Chatwoot era um balão genérico que eu tinha desenhado. Virou a forma da marca.

## 2026-09-18: Funil de oportunidades, com kanban e etiquetas (v0.23.0)

O operador pediu kanban, oportunidades e etiquetas para controle. Entrou o módulo
`backend/app/oportunidades/` com quatro tabelas (migração `0019`, toda aditiva): `etapa_funil` (as
colunas), `oportunidade` (os cartões), `etiqueta` e a ligação entre cartão e etiqueta.

**Por empresa, sem exceção.** Todo método do repo recebe `cliente_id` e filtra por ele, e o
`cliente_id` vem da URL conferida no banco, nunca do corpo. Três testes seguram isso: o funil de uma
empresa não aparece na outra, etiqueta de outra empresa não cola no cartão e cartão de outra empresa
não se move pela URL errada.

**As colunas são do operador**, não fixas no código: kanban com coluna fixa serve para um negócio
só. A primeira visita cria o funil padrão, porque quadro que abre vazio não é kanban. Coluna com
cartão não some: responde 409 dizendo quantos mover antes, senão o cartão iria junto e o operador
descobriria depois.

**Cor de etiqueta é nome de token da paleta**, nunca hexadecimal. É a mesma regra que o teste do
front já aplica ao `src`: etiqueta com cor livre estragaria o quadro inteiro.

**Arrastar é o arrasto nativo do navegador**, sem biblioteca, como manda o `AGENTS.md`. O cartão
aparece na coluna nova antes de o servidor responder, senão a mão chega antes da rede e parece que o
arrasto não pegou.

Junto, saiu a linha de situação de baixo do nome do espaço no menu e o ponto verde de perto do
veredito da Visão geral: o estado já mora no ponto da marca, e colorir de verde uma frase que diz
que nada aconteceu é contraditório.

spec/frontend.md, seções 4 e 5.

## 2026-09-18: Espaço de trabalho, perfil do operador e dados do negócio (v0.22.0)

O painel não guardava nada sobre quem opera nem sobre a instalação: o menu dizia ASIMOV para todo
mundo, e Configurações só mostrava o que vinha do `.env`. Entrou a tabela `espaco_trabalho` (uma
linha, como o operador) com nome, sigla e os dados do negócio, mais `nome` e `email` em
`usuario_painel`. Migração `0018`, aditiva e com padrão vazio: quem não preencher nada continua
vendo o painel como antes.

O nome e a sigla trocam o que o menu mostra, que é o ponto: quem atende várias empresas reconhece
de qual instalação é a aba aberta. Os dados do negócio são de quem opera, nunca das empresas
atendidas, que moram em `clientes/`.

Junto: o texto do ponto de situação passou a ter um formato só nos quatro estados ("0 falhas ·
0 paradas" no verde, em vez de "tudo no ar"), dizendo o que foi contado, e a palavra "handoff" saiu
dele. A Visão geral passou a usar o mesmo `Cabecalho` das outras telas, com o veredito virando a
linha de contexto e o ponto da cor do estado. A tela de Canais ganhou o catálogo das integrações,
que faltava: ela só mostrava quem já tinha canal.

spec/frontend.md, seções 4 e 5.

## 2026-09-18: Nada de caixa nativa do navegador no painel (v0.21.5)

O X do popup do agente não fechava. Ele chamava `window.confirm` antes de sair, e onde o navegador
suprime a caixa nativa (embutida num app, modo quiosque, bloqueio de diálogo) ela devolve "não" sem
aparecer: o popup ficava aberto e o botão parecia morto. O operador achou clicando.

A pergunta saiu inteira, porque não tinha o que proteger: o rascunho é gravado no navegador a cada
mudança e o popup reabre com ele. Um teste novo (`design/dialogos.teste.ts`) recusa `confirm`,
`alert` e `prompt` no `src` inteiro. Quem precisa confirmar usa o `Modal`, quem precisa avisar usa o
`Aviso`: caixa nativa trava a página e ignora o design system.

## 2026-09-18: O painel se afasta do design system em três pontos (v0.21.0)

O operador pediu canto arredondado, Inter na estrutura e o logo das integrações. Os três contrariam
o `designsystem/` original, que é de canto reto e rótulo em mono, e por isso ficam registrados aqui:
quem abrir o design system e o painel vai ver diferença, e ela é de propósito.

**Canto.** Escala curta no `tailwind.config.ts`, e nada fica reto. Saíram com o canto reto os dois
cantos marcados do botão fantasma e do popup: eles eram o desenho de um canto em ângulo, e não sobra
ângulo no painel. O campo deixou de ser só borda de baixo e virou moldura inteira; o interruptor
deixou de ser retângulo e virou cápsula.

**Indicador em cartão.** Os três números do ritmo eram soltos sobre o fundo, em mono e no tamanho de
título. O operador chamou de "negócio atirado com número": sem moldura eles não se leem como grupo,
e a explicação do terceiro não cabia na coluna e cortava. Viraram três cartões no formato que todo
painel usa, com o rótulo em cima e a comparação embaixo.

**Recolher no topo e área de conta no rodapé.** O recolher ficava solto embaixo do sair, no fim do
menu. Subiu para o lado da marca, que é onde se procura por ele. O rodapé virou a área da conta:
situação da instalação, avatar, endereço e a tela `Configurações`, que nasceu junto e é onde as
chaves de IA passaram a se administrar. Elas só existiam dentro da ficha de um agente, e chave é da
instalação.

**Marca na paleta do painel.** A primeira tentativa usou a cor de cada marca (verde do WhatsApp,
azul do Chatwoot e da Meta) como token. O operador reprovou: logo de terceiro segue a paleta do
produto, não a identidade própria. Os três tokens saíram e a `Marca` passou a herdar a cor do texto,
como o `Icone`.

**Título e largura.** O título de seção era `text-5xl` com subtítulo embaixo e régua depois, e comia
um terço da tela antes do conteúdo; a linha da lista usava um terço da largura e deixava o resto
vazio. Entrou o `Cabecalho` compartilhado, em `text-2xl` e com o contexto na mesma linha, e as listas
passaram a distribuir informação pela largura.

**Canto e acento.** O operador reprovou a primeira tentativa: cartão arredondado com `border-l-2`
na cor da situação. No canto, a borda de 2px encontra a de 1px e o raio transforma a junção numa
cunha. Virou regra: canto arredondado nunca anda com borda mais grossa de um lado. O acento de cor
passou a ser uma barra por dentro, afastada dos cantos, no `Aviso`, em Canais, na lista de Conversas
e no aviso das telas de login.

**Tipografia.** A mono era a fonte de todo rótulo, botão, selo e item de menu. Passou a ser só de
dado técnico, na classe `.tecnico`: número de métrica, nome de modelo, endereço, código e
identificador. O resto é Inter. Motivo: em rótulo curto e maiúsculo a mono custa legibilidade sem
dar informação, e o painel é operação, não terminal.

**Marcas.** `design/marcas.ts` e `design/Marca.tsx`, separados de `icones.ts`: marca é preenchida,
tem cor própria e é de outra empresa, enquanto ícone é traçado e herda a cor do texto. As três cores
de marca entraram como token para o teste que proíbe hexadecimal solto continuar valendo. Nenhuma
biblioteca de fora, como manda o `AGENTS.md`.

Junto vieram as correções de copy que a auditoria tinha deixado para decisão, o menu em dois grupos
e os avisos de limitação que o painel escondia e o terminal contava (bloqueio do número na API não
oficial, cobrança por mensagem da Meta).

spec/frontend.md, seção 3.

## 2026-09-18: Auditoria de copy do produto inteiro (v0.20.4)

Auditoria de todo texto que alguém lê: documentação, telas do terminal, painel, popups, páginas
servidas, descrições de ferramenta, mensagens dos canais e o banco de ícones. Relatório em
`docs/auditoria-copy-2026-09-18.md`, com o método e a lista completa.

Nove achados foram corrigidos na hora, por serem erro de fato e não questão de gosto: telefone real
no repositório público, aviso que dizia que o WhatsApp oficial ainda não existia, duas datas
escritas no passado antes de acontecerem, instrução de retomada que ninguém no destino consegue
seguir, promessa de uma tela que não existe, caminho do contêiner numa resposta pública, tipagem que
deixava passar nome de ícone inválido, README descrevendo o setup anterior à v0.20.0 e "risco de
bloqueio: nenhum".

O resto (cerca de 180 achados de jargão de tela, verbosidade medida, vocabulário inconsistente entre
terminal e painel, limitação que o painel esconde, ícones mortos e improvisados) ficou no relatório
para o operador decidir, porque é reescrita de voz e ele é quem manda nela.

spec/estado.md.

## 2026-09-18: Contraste do texto do painel na régua da WCAG AA

Na VPS o operador não conseguia ler rótulo de campo nem texto de apoio. Medido: `dim` (#444444)
dava 1,9:1 sobre o preto e `muted` (#525252) dava 2,4:1, contra os 4,5:1 que a WCAG AA pede para
texto normal. São 106 usos de texto entre os dois, mais borda de campo e trilho de interruptor, que
pedem 3:1 por serem componente.

`dim` foi para `#8a8a8a` (5,5:1) e `muted` para `#a3a3a3` (7,5:1), no `tailwind.config.ts` e no
`painel/estaticos/painel.css` do login, que não passa pelo Tailwind. A escala de texto ficou 15:1,
7,5:1 e 5,5:1, com a hierarquia preservada. Os outros tokens já passavam e não mudaram; `borda`
(#222222) também não, porque separa cartão e não carrega texto.

Um teste novo (`design/contraste.teste.ts`) lê os tokens do `tailwind.config.ts`, confere os 4,5:1
de todo token de texto sobre os três fundos, confere a ordem da hierarquia e confere que o CSS do
login repete os mesmos valores. Ele não escreve cor nenhuma, senão o teste que proíbe hexadecimal
solto o reprovaria.

Conferido no painel rodando: visão geral, agentes, canais, contatos, o popup do agente nos oito
passos e as telas de entrar e de primeiro acesso, medindo o contraste no DOM com a transparência
composta. Nenhum texto abaixo de 4,5:1; o menor é 5,47:1.

spec/frontend.md, seção 3, e AGENTS.md.

## 2026-09-18: Cor principal do painel passa de lime para ciano

O operador quis no painel o mesmo ciano que vê no CLI (o ciano ANSI do terminal web). O token `lime`
(`#ccff00`) virou `ciano` (`#29b8db`), com o brilho `rgba(41, 184, 219, 0.5)`, no
`tailwind.config.ts`, em todo o `frontend/src`, no `painel/estaticos/painel.css` (`--ciano`) e no
`designsystem/`. Texto preto sobre o ciano cheio continua legível. O token `ok` não mudou.
Atualizado spec/frontend.md, seção 3.

## 2026-09-18: A instalação passa a oferecer o painel (v0.19.0)

O painel existia e ninguém ligava: a instalação só citava `asimov painel` numa lista de comandos no
fim. Quem termina o setup não sabe que dá para administrar pelo navegador.

Entrou `tela_painel_oferta`, perguntada **uma vez**, na instalação nova e na primeira atualização de
quem já tinha instalado (marcada no estado, como o `handoff_perguntado`). Ela explica o que o painel
faz, avisa do registro DNS de `app.<dominio>` antes de perguntar, e quem disser não recebe o comando
para depois. Dizer sim cai no `painel_liga`, que já existia e cuida de DNS, Caddy, reinício e código
de acesso.

A simulação do onboarding ganhou a tela no fim, com a resposta "não", que é o caminho que não
depende de DNS nem de contêiner. No caminho, uma linha vazia que sobrava no fim do
`setup/testes/respostas.txt` saiu: ela nunca era lida, e o `confirma` novo a leria como "sim",
porque resposta vazia é sim.

spec/fases.md e spec/estado.md.

## 2026-09-18: Um painel só, e três bugs que apareceram ao rodar de verdade

Ao subir a aplicação inteira na máquina (Postgres, Redis, API e worker) para o operador testar, o
que estava escondido apareceu.

- **A tela de entrar era de outro sistema.** Ela vinha da parte 8.1, com fundo claro, cantos de 10 px
  e acento azul, e era a primeira coisa que o operador via. Reescrita com os tokens do design
  system. O `painel.css` é o **único lugar do projeto onde cor se escreve em hexadecimal**, porque
  ele não passa pelo Tailwind; todas ficam no `:root` dele e em nenhum outro lugar. Inter e JetBrains
  Mono passam a ser servidas pela API em `/painel/fontes/...`, de uma lista fechada de nomes, como
  todo o resto: nada de CDN.
- **Existiam dois painéis.** `/painel/inicio` e `/painel/agentes` eram as telas em Jinja2 de antes do
  front, com o mesmo dado que o React mostra com muito mais coisa. Viraram desvio para
  `/painel/app`, e os dois templates saíram. Os cinco testes que olhavam essas páginas passaram a
  olhar a API, que é onde a garantia mora agora.
- **Bug: a folha de estilo ficava em cache para sempre.** O nome do arquivo não muda entre versões,
  então depois de um `asimov atualizar` o operador continuaria vendo o estilo da versão passada. O
  endereço passou a carregar a versão (`painel.css?v=<mtime>`), e aí guardar à vontade é seguro.
- **Bug, e era sério: a API do painel devolvia o detalhe cru da falha.** O `detalhe` guarda o que o
  provedor respondeu, e um corpo de erro já veio com `api_key` dentro: chave de API indo para o
  navegador. Agora sai só o resumo curto, o mesmo do terminal. Quem pegou foi um teste da parte 8.1
  que eu teria apagado junto com a tela se não tivesse lido.
- **Bug: a migração do perfil colidiu de número.** Ela nasceu como `0014`, que já era do
  `usuario_painel`, e o Alembic recusou subir com duas cabeças. Renumerada para `0016`, depois da
  `0015`. Nunca tinha sido aplicada em lugar nenhum, então renomear foi seguro; a regra de nunca
  editar migração aplicada continua de pé.

spec/frontend.md (seção 3.2), spec/arquitetura.md e spec/estado.md.

## 2026-09-18: Painel completo, etapas 3 a 11, com o agente sempre em popup

Construído numa passada só, a pedido do operador. Nada disso rodou em VPS.

**A regra que organizou tudo**: toda configuração de agente acontece num popup grande no meio da
tela, com o que está atrás embaçado e escurecido. Vale para criar e para a ficha inteira, que deixou
de ser página. `Modal` novo em `design/`, montado com as primitivas do design system (o sistema não
traz modal pronto): fundo `surface`, borda de 1px, os dois cantos marcados, `backdrop-blur` no fundo,
Esc e clique no fundo fecham, o Tab não escapa para a lista atrás e a página para de rolar.

O que entrou, por etapa:

- **3. Lista e onboarding.** Onboarding em sete passos, na ordem do terminal, com o stepper do design
  system à esquerda e a **prévia viva** à direita: uma conversa de mentira, montada no navegador, em
  que o agente já responde com o que foi escolhido (emoji, função, partes da resposta, busca). A tela
  diz que é de mentira e que nada foi cobrado. Rascunho no navegador. Só empresa, canal e nome
  travam. O cartão de cada canal diz **o que você vai precisar ter na mão** antes de começar, que é a
  informação que faltava em todo onboarding. A criação é uma chamada só no fim.
- **4 a 7. Ficha em seis abas**, cada seção com o próprio salvar, e o salvar diz o que mudou
  ("salvei o nível de emoji, as partes da resposta"), não um "pronto" genérico.
- **8. Canais.** Uma linha por agente com a resposta do canal agora. Cada canal é perguntado em
  separado no backend: o que não responder vira linha vermelha em vez de derrubar a tela. QR code da
  WAHA desenhado no navegador (a própria WAHA devolve o PNG; o terminal continua com o texto cru e o
  `qrencode`).
- **9. Chat** em duas colunas, com o histórico, quem falou, o custo de cada turno e o devolver ao
  agente. **10. Contatos** com busca por nome ou telefone, inclusive digitado com pontuação.
- **11.** Tela da base de conhecimento dizendo o que ela vai fazer, rota inexistente com caminho de
  volta, e a passada de acessibilidade e celular.

Mudanças de spec no caminho, todas registradas nos arquivos afetados:

- **A migração do `perfil` saiu da etapa 5 para a 3**: o onboarding pergunta sobre a empresa no passo
  4, e sem a coluna ele não teria onde guardar. Migração `0014`, aditiva, com `perfil` (JSONB) e
  `assina_nome` no agente. O `persona.md` passa a ser escrito a partir dela, e editar à mão continua
  valendo.
- **A conversa de teste virou aba do agente**, não da tela de Chat: falar com o agente é como se
  confere uma mudança antes de ela chegar em alguém.
- **`cliente_id` nas rotas de um agente sai da linha do agente lida do banco**, não da URL nem do
  corpo: é a mesma garantia com uma URL curta, que é o que a lista precisa para abrir o popup com um
  clique. Criar continua recebendo a empresa na URL, conferida no banco.

spec/frontend.md, seções 4, 5.1, 5.2.1, 5.3, 5.5 e 6, mais a tabela de etapas.

## 2026-09-18: A Visão geral virou triagem, não relatório

Passagem de direção de arte sobre a tela pronta, com uma regra dura: **o design system é a fonte de
cor, tipografia e espaçamento, e nada disso se toca**. O que mudou foi hierarquia, layout e texto.

- **A pergunta da tela estava errada.** Ela respondia "quais são os números", com seis cartões
  iguais, e o veredito ("está tudo bem?") era um ponto de 2px no rodapé do menu. Quem abre o painel
  é o operador, que já tem `asimov consumo` no terminal: ele vem aqui para triagem. A ordem virou
  veredito, o que espera por ele, o ritmo, e o dinheiro por último.
- **O herói virou uma frase.** "Número grande com rótulo pequeno" é o tratamento padrão de qualquer
  painel. Agora a primeira coisa da tela é uma frase em português direto, com a régua de estado do
  `Aviso` à esquerda, em escala de título. A cor mora na régua, não numa palavra destacada.
- **Cartão só onde separa coisas diferentes.** De seis caixas iguais para quatro tratamentos:
  frase, lista que some quando está vazia, números soltos sobre o fundo com a curva atravessando, e
  cartão nas duas listas e no dinheiro.
- **Texto reescrito do ponto de vista de quem lê.** `turno_modelo_falhou` virou "O modelo não
  respondeu" com o tipo cru embaixo em letra pequena (é por ele que se procura no log). O código do
  handoff virou `/retomar H3K9QP`, que se explica sozinho. Nome de agente e identificador de modelo
  saíram da caixa alta: a caixa alta em mono é do design system para rótulo de dado, e é só para
  isso. Canal virou "no WhatsApp", não "no waha".
- **Saíram os padrões genéricos**: a corda de meta com ponto do meio (`A · B · C`), o rótulo em caixa
  alta acima de cada número, os marcadores numerados de seção (o conteúdo não é sequência), a
  entrada com fade em cada cartão (ficou só a curva que se desenha uma vez) e o selo "passou do
  prazo" repetindo o que a régua vermelha e o tempo em vermelho já diziam.

spec/frontend.md, seção 5.1. `Progresso` ganhou o modo de escrita do rótulo (dado, nome ou token).

## 2026-09-18: A Visão geral refeita, com a espera e a composição do design system

O operador olhou a primeira versão da tela e apontou três coisas, todas certas.

- **A tela carregava com uma roda genérica.** O design system tem dez estados de espera (KINETIC,
  seção 3) e nenhum estava em uso. Agora cada cartão espera com a forma do que vai aparecer nele:
  o ritmo com as barras, o gasto com o anel, a proporção com o porcento, a lista de agentes com os
  pontos, as falhas com o pulso e os handoffs com o digitando. `Carregando` passou a ter seis
  formas, portadas do original com as animações em SMIL e os keyframes `radar` e `anel`.
- **Os dados não estavam apresentados, só listados.** Eram cinco caixas iguais com um número dentro
  cada, sem comparação nenhuma. Passou para a composição da AXIS (seção 2): grade de três colunas,
  gráfico de ritmo ocupando duas, e **todo número com o mesmo número do período anterior ao lado**,
  em por cento. Entraram três leituras novas na API para isso: o período anterior inteiro
  (`variacao`), quantas conversas o agente fechou sem chamar gente (`resolucao`, que virou o
  ponteiro da AXIS) e turnos por agente (`agentes`, que virou barra de proporção). Sem período
  anterior a resposta é "sem comparação", nunca um "+100%" sobre zero.
- **O seletor de empresa não fazia sentido na barra do topo.** Ali ele parecia trocar a instalação
  inteira, e trocava só os números de uma tela. Regra nova: **filtro de tela mora na tela**. Ele foi
  para o cabeçalho da Visão geral, ao lado do período. A barra do topo ficou com o que vale para o
  painel inteiro: busca e situação da plataforma.

Componentes novos: `Progresso` (o "System Health" da AXIS: rótulo, valor e barra sobre trilho de
1px) e o ponteiro (gauge) dentro do `Grafico`. spec/frontend.md, seções 3.1, 4 e 5.1.

**O menu lateral ficou parado de verdade**: a página deixou de rolar e a rolagem passou para o
conteúdo da direita. Com `sticky` o menu grudava no topo mas continuava participando da rolagem da
página; agora ele é um bloco comum de uma linha que não rola, e não tem como se mexer. Altura em
`h-dvh` em vez de `h-screen`, porque no celular a barra do navegador some e volta.

**A barra do topo saiu inteira**, na mesma revisão. Uma faixa fixa atravessando a página só se paga
se carregar algo de uso constante, e ela tinha uma busca desligada e um ponto de situação. A busca
passa a nascer na tela de Agentes, onde existe o que procurar; a situação da plataforma foi para o
rodapé do menu lateral, junto do operador e do sair, porque é informação da instalação; e no celular
sobrou só o abridor da gaveta, solto sobre o conteúdo. A tela agora começa no conteúdo.
spec/frontend.md, seção 4.

## 2026-09-18: O painel usa o design system inteiro, e criar agente vira onboarding

- **O design system é a única fonte de interface**, e o painel passa a usar as seis seções, não só a
  de componentes. Nenhuma biblioteca de interface de fora entra no `frontend/`: sem Radix, shadcn,
  Headless UI, Chart.js, Recharts, Framer Motion, lucide ou heroicons. Peça que o design system não
  traz pronta (Abas, Tabela, Modal) é montada com as primitivas dele. Um teste novo trava a lista de
  dependências do `package.json`. spec/frontend.md, seção 3.1, com o mapa de qual seção alimenta o
  quê: AXIS vira o `Grafico` em SVG puro, KINETIC vira os estados de carregando e as
  microinterações, ONYX decorativo entra em tela vazia e no topo do onboarding.
- **Criar agente deixa de ser um modal e vira onboarding em tela cheia** (`/agentes/novo`): passos à
  esquerda, uma pergunta por vez no meio e prévia viva à direita, em que o agente já responde com as
  escolhas aplicadas. Motivo: no terminal são sete perguntas seguidas em que o operador só descobre
  o efeito de cada resposta depois, conversando em produção. Só empresa, canal e nome travam; o
  resto tem padrão e pode ser pulado, e o passo de conectar pode ficar para depois (agente nasce
  inativo, com "falta conectar" na lista). Termina abrindo a conversa de teste pelo canal nativo, com
  a primeira mensagem sugerida. Criação continua sendo uma chamada só no fim: passo nenhum grava
  pela metade. spec/frontend.md, seção 5.2.1, e a etapa 3 da tabela de etapas.

- **A situação da barra do topo não é o `asimov diagnostico`.** A spec do front pedia "o mesmo
  critério do `asimov diagnostico`", que pergunta o código HTTP de cada endereço da instalação por
  dentro da VPS: coisa que o terminal faz e a API não. A barra responde a mesma pergunta pelo que a
  API sabe: falha `canal_fora_do_ar` no período é vermelho, outra falha recente ou handoff vencido é
  amarelo, nada é verde. Quem quiser o código HTTP de cada endereço continua tendo `asimov
  diagnostico`. spec/frontend.md, seção 4.
- **Dinheiro sai da API como texto, não como número.** A rota da visão geral responde por modelo do
  Pydantic, com `Decimal`: `jsonable_encoder` transformava `0.06` em `0.059999999999999997`, e no
  painel isso viraria custo errado na tela.

## 2026-09-18: Painel do operador ganha front próprio em `frontend/`

O operador pediu o painel com a arquitetura de informação do GPT Maker (menu lateral fixo, lista de
agentes à direita, ficha do agente em abas) e a aparência do design system guardado em
`designsystem/`. Duas decisões saíram daí:

- **O front vira um SPA em `frontend/`** (React, TypeScript, Vite, Tailwind), servido pela própria
  API em `/painel/app` e construído num estágio `node` do `backend/Dockerfile`. A regra do
  `AGENTS.md` "não existe `frontend/` na primeira versão" cai. O que não muda: nada de CDN, nada de
  container novo, `/admin` segue sem sair da VPS e entrar, primeiro acesso e sair continuam nas
  páginas Jinja2 já testadas. A alternativa (seguir em Jinja2 com HTMX) custava menos, mas as telas
  pedidas (chat com histórico, ficha em abas com salvar por seção) valem o SPA.
- **A seção Trabalho vira campo no banco e escreve o `persona.md`.** Migração aditiva com
  `agente.perfil` (função, público, site, sobre a empresa) e `agente.assina_nome`. O arquivo continua
  sendo a fonte do prompt de sistema: o formulário preenche o modelo e grava, e editar à mão segue
  valendo. O `perfil` é por agente, não por empresa, para não repetir o achado A05 da auditoria
  (prompt atravessando de uma empresa para outra).

Spec do front, com telas, contrato da API e as onze etapas de construção: `spec/frontend.md`.
Atualizados spec/fases.md (Fase 8), spec/arquitetura.md (seções 1 e 2), spec/estado.md e `AGENTS.md`.

Ajustes decididos ao construir a Etapa 1:

- **O contexto do `docker build` passou de `backend/` para a raiz**, com `.dockerignore` novo, que é
  o que permite o estágio `node` construir `frontend/` na mesma imagem. O `.env` está na primeira
  linha do `.dockerignore`: com a raiz no contexto, ele chegaria ao daemon sem isso.
- **Entrar e criar o primeiro acesso passam a levar para `/painel/app`**, não mais para a tela Jinja2
  de início. As páginas Jinja2 de `inicio` e `agentes` continuam no ar e testadas até as Etapas 2 e 3
  as substituírem.
- **CSRF derivado da sessão por HMAC**, sem chave nova no Redis. O cookie é `HttpOnly`, então o único
  jeito de o front saber o token é ter lido `GET /painel/api/eu` com a sessão válida.
- **Sessão, origem e CSRF saíram de `rotas.py` para `painel/acesso.py`**, usados tanto pelas páginas
  Jinja2 quanto pelo `painel/api.py`. A regra passou a existir em um lugar só.
- **As fontes vêm dos pacotes `@fontsource`** e entram no build, em vez de arquivos soltos em
  `public/`. Continuam servidas da VPS.

**Correção feita na mesma etapa, depois que o operador apontou:** a primeira versão dos componentes
tinha pegado do design system só as cores e as fontes, e inventado o resto. Três erros concretos:
a hierarquia dos botões estava invertida (lime cheio como principal, quando no original o cheio é
branco e o lime é contorno), o campo tinha moldura inteira em vez de só a borda de baixo, e os 50
ícones do sprite da seção 1 não estavam sendo usados em lugar nenhum. Os componentes foram refeitos
a partir do markup do design system, e a tabela da seção 3 de `spec/frontend.md` passou a registrar
o que cada um copia e de que seção veio, para a próxima etapa não repetir o atalho.

## 2026-09-18: Correções dos P2 e P3 da auditoria, e segurança do painel

Continuação da entrada anterior. Todos os achados com sonda viraram regressão da suíte normal
(`backend/testes/test_auditoria_p1.py` e `test_auditoria_p2.py`), e o arquivo de sondas foi
removido: não sobrou defeito descrito lá.

Segurança:

- **A11, nada do cadastro vira HTML ativo.** Nome de empresa, de agente e contato entram escapados
  na página pública de privacidade. Antes, um `<script>` no nome virava script de verdade.
- **A14, token de webhook não vai para log nenhum.** O caminho é saneado (`/webhook/chatwoot/…`),
  todo erro interno ganha uma referência curta que aparece na resposta e no log, e o access log do
  uvicorn foi desligado no Dockerfile: era ele que registrava a URL inteira, com o token dentro.
- **A13, segredo não passa por argumento de processo.** O corpo do `curl` foi para arquivo com
  permissão 600 e os `jq --arg` com token viraram `env.VAR`: `ps` é legível por qualquer usuário
  da máquina, `/proc/PID/environ` não.
- **`.env` com permissão afrouxada volta para 600** a cada execução do setup, com aviso. A spec
  prometia recusar iniciar, o que trava o operador sem saída; consertar e avisar é mais útil.
- **Painel, conta única garantida pelo banco** (migração `0015`), com a corrida tratada, e o código
  de primeiro acesso passou a ser gasto **depois** de a conta existir: falha no meio não deixava o
  operador sem código e sem conta.

Confiabilidade:

- **A07, entrega recusada pela Meta vira falha visível.** `status: failed` chegava depois do envio
  aceito e era descartado junto com o recibo comum. Virou `Acao.ENTREGA_RECUSADA` com o código do
  erro em Ver consumo e falhas. O reenvio automático por template fora da janela continua pendente:
  exige rastrear a mensagem enviada e o contexto dela.
- **A08, lote da Cloud API.** O contrato do canal ganhou `interpretar_todos`, e o webhook processa
  todos os eventos do envelope. Só a primeira mensagem era lida; a segunda sumia com o webhook
  confirmado.
- **A09, rajada não esconde pergunta.** O histórico continua limitado, mas as falas ainda não
  respondidas vêm por consulta própria, e passar do teto registra falha em vez de sumir.
- **A10, retomada por tempo usa o canal da conversa**, não o do agente: a conversa de teste no
  terminal é nativa até em agente de Chatwoot ou WhatsApp.
- **A12, modelo obrigatório vazio é recusado** com 422. Só o fallback pode ficar sem modelo.
- **A17, limpeza de mídia em lotes até esgotar**, com teto de segurança e falha registrada quando
  sobra fila. Parava em 500 por dia, e o disco enchia devagar.
- **A18, PDF é lido em thread e para no teto de páginas.** Era CPU dentro do laço de eventos: um
  arquivo pesado deixava as outras conversas esperando.
- **A20, `/health` inclui o worker.** Pulso de minuto em minuto no Redis; sem ele a saúde reprova.
  `aguardando` é a instalação que ainda não viu o worker subir, e não derruba nada: é o estado
  normal durante a própria instalação.
- **A19, desistir da criação do primeiro agente** não marca mais a etapa como concluída.
- **A15, atualização guarda o que foi personalizado.** Antes de extrair, `modelos/` e `deploy/`
  vão para `~/.asimov/antes-da-atualizacao/<data>`.

Organização:

- **A22**: CI em `.github/workflows/testes.yml` (testes com Postgres e Redis, ciclo completo das
  migrações, shellcheck e onboarding simulado), barreira que recusa rodar a suíte destrutiva fora
  de banco de teste, e `caixa.bin` (dump de terminal de depuração) removido do repositório.
- **A21**: a regra de camadas no `AGENTS.md` passou a descrever o que o código faz (leitura simples
  pode chamar o repo; orquestração e escrita, não) e as exceções legítimas ao `cliente_id`.
  Mover a orquestração que sobrou nas rotas para os serviços fica para um passo próprio.
- **Nome de empresa que parecia real** (`BecomApp`, `Contour`) saiu da simulação de onboarding.
  O repositório é público e a regra é antiga; ninguém tinha pego.
- **Armadilha nova no `AGENTS.md`**: item novo no menu muda a numeração de `respostas.txt` e
  descarrila a simulação no meio. Conferir que a saída é 0, não só que a tela abriu.

## 2026-09-18: Correções dos seis P1 da auditoria

Auditoria em `docs/auditoria-2026-09-18.md` (22 achados). Os seis P1 foram conferidos um a um no
código antes de mexer, corrigidos e transformados em regressão da suíte normal
(`backend/testes/test_auditoria_p1.py`, 16 testes). As sondas que descreviam esses defeitos saíram
de `backend/testes/auditoria_2026_09_18.py`, que ficou só com os P2 abertos.

- **A01, reentrega recupera turno perdido.** O webhook grava e depois agenda; com o Redis fora do
  ar ele responde 500 de propósito, mas a reentrega caía na deduplicação e voltava 200 sem agendar
  nada, deixando a mensagem gravada e sem turno para sempre. Agora a reentrega reagenda **quando
  não há nada agendado nem rodando** e existe fala do contato sem resposta. Reentrega comum, com o
  turno já na fila, continua não virando segundo job: o canal repete bastante.
- **A02, envio que não saiu não conta como respondido.** `_envia` parava na primeira falha e o
  turno avançava `respondido_ate` mesmo com zero envios, escondendo a pergunta do contato do turno
  seguinte. Zero enviadas agora devolve `nao_enviado` e não marca nada; envio parcial marca (repetir
  duplicaria o que já chegou) e registra `resposta_incompleta` em Ver consumo e falhas.
- **A03, prazo do token não é mensagem nova.** O token do buffer durava 80 s com buffer de 8, e
  fila lenta ou modelo demorado faziam a resposta ser descartada como se tivesse chegado mensagem
  nova, sem ninguém para refazê-la. Chave ausente passou a valer como "não substituído", e o prazo
  virou buffer + lock + 300 s. Só um token **diferente** descarta o turno.
- **A04, humano que assume cala o agente na hora.** O direito de falar era consultado uma vez, no
  início. Agora é conferido antes de cada mensagem e dos dois lados da espera da digitação, lendo o
  status numa sessão nova (quem pausou foi o webhook, noutra transação) e perguntando ao canal.
- **A05, prompt não passa de uma empresa para outra.** O slug volta a ficar livre quando a empresa
  é removida, e os arquivos ficam no disco de propósito; empresa nova com o mesmo nome herdava as
  instruções da anterior. A pasta agora tem dono (`.cliente`) e, quando o dono é outro, **quem sai
  é a pasta antiga**, para `<slug>-<8 do dono antigo>`. A empresa viva fica sempre em
  `<slug>/<agente>` porque esse caminho também é a URL pública da política de privacidade, que
  quebraria se a pasta nova ganhasse sufixo. Pasta sem dono marcado é adotada por quem a usa:
  instalação no ar não muda de caminho.
- **A06, exclusividade durante todo o efeito externo.** O lock durava 240 s e o `job_timeout` do
  worker, 300: existia uma janela em que outro turno entrava na conversa com o primeiro ainda
  enviando. O lock passou a 360 s (maior que o job, quem interrompe job longo é o arq) e o turno
  confere a posse antes de cada mensagem.

Aberto e não tocado aqui: os 14 P2 e 2 P3 do relatório, com as três sondas que restaram.

## 2026-09-18: Nível de emoji por agente (v0.17.0)

- **Pedido do operador, depois do primeiro teste no WhatsApp oficial** (áudio entendido e digitando convincente): uma pergunta em todo canal sobre emoji, com nível, "tipo o seletor de effort". `Agente.emojis` com `nenhum`, `pouco`, `medio` e `muito`, perguntado na criação dos quatro canais (é jeito de escrever, não canal) e editável em Editar agente > Emoji.
- **O nível vira uma instrução da plataforma**, ao lado da de saída, antes da data (que muda a cada minuto e não pode quebrar o cache do prompt fixo). Fora do prompt do agente: quem escolhe é o operador no menu, e o `persona.md` fica livre para o que é da empresa.
- **Agente criado antes disto fica em `livre`** (migração `0013`, `server_default`), e para ele a plataforma não diz nada sobre emoji, como sempre fez. Trocar o padrão deles para `nenhum` mudaria o jeito de responder sem ninguém pedir. `livre` não é oferecido na tela: quem edita escolhe um dos quatro.
- **`ESCOLHA_ATUAL` no `escolha`** (`ui.sh`): o cursor começa na opção de hoje, para a tela de editar não obrigar a contar de novo. Serve a qualquer escolha futura.
- Atualizados spec/dados.md, spec/telas.md e a simulação de onboarding.

## 2026-09-18: Token guarda os ativos de quando nasceu (v0.16.3)

- **O operador tinha a conta atribuída ao usuário do sistema e o setup dizia que o token não enxergava nenhuma.** A causa: token de usuário do sistema guarda os ativos de quando foi gerado, então atribuir a conta depois não vale para um token que já existe. A mensagem antiga mandava conferir o ativo, que estava certo, e não dizia o que fazer.
- **A mensagem passou a começar pela causa provável e pela saída**: gerar o token de novo. Só depois fala em permissão e em ativo, e deixa claro que informar o ID à mão resolve a tela mas não o token: se ele não alcança a conta, a Meta recusa as chamadas seguintes por permissão.
- Atualizados `docs/whatsapp-oficial.md` (seção de onde fica o ID e tabela de erros) e o texto do setup.

## 2026-09-18: O ícone também vem por URL, e `asimov diagnostico` (v0.16.2)

- **O 404 da página, na prática, era o operador estar em `/root`**: `source deploy/compose.sh` não existe fora da pasta do projeto, então o `dc restart caddy` nunca rodou. Toda dica de comando do setup passou a vir com `cd $RAIZ_PROJETO` na frente.
- **`asimov diagnostico`** (e item no menu): versão do código, versão instalada, pasta e o código HTTP de cada endereço que precisa responder (API por dentro, API pelo domínio, política, ícone e WAHA quando ligada), mais os comandos completos de recarregar o servidor web e ver o log. Nasceu de duas rodadas de diagnóstico por mensagem para achar algo que a própria instalação sabia responder.
- **O ícone virou URL pública** (`/icone-app.png`), pedido do operador: baixar pelo navegador e subir no app da Meta, sem `scp`. Para isso o arquivo saiu de `docs/imagens/` e foi para `modelos/`, que já é montado nos contêineres e já é onde ficam os arquivos que o operador ajusta (prompts, `AGENTS.md.tmpl`, `privacidade.html`). O gerador foi junto: `python3 modelos/gerar_icone.py`.
- **A tela que manda o operador ao painel da Meta confere os dois endereços** antes, pelo domínio, que é como a Meta vai abrir. Endereço que não responde vira aviso com o comando de recarregar, em vez de a Meta recusar a URL depois.
- **Arquivo de modelo ausente responde 503 com o caminho**, não erro interno sem explicação: acontece quando a atualização não trouxe `modelos/`.
- Atualizados `docs/whatsapp-oficial.md` (URL do ícone), spec/arquitetura.md e spec/estado.md.

## 2026-09-18: Uma política por agente, e o Caddy recarregando de verdade (v0.16.1)

- **A URL da política respondia 404 numa VPS atualizada.** O Caddyfile é montado no contêiner: `dc up -d caddy` não recria o contêiner quando só o arquivo muda, e o Caddy segue com a configuração que já carregou. `sobe_servicos` passou a rodar `caddy reload` depois do `dc up`, com `dc restart caddy` como reserva. Vale para qualquer caminho público que apareça no futuro, não só este. Virou linha nas armadilhas do AGENTS.md.
- **O caminho no Caddy virou `/privacidade*`**, um padrão só: em matcher do Caddy `path /privacidade/*` não cobre dois níveis de forma óbvia, e `/privacidade*` cobre qualquer profundidade sem ambiguidade.
- **Uma política por agente** (pedido do operador): na Meta existe um app por número, e cada app quer a própria URL. Entrou `GET /privacidade/{empresa}/{agente}`, que nomeia a empresa e o agente. A API passou a devolver `url_privacidade` em cada agente, montada do `arquivo_prompt` (que já carrega os dois slugs, evitando uma consulta só para montar endereço), e o setup mostra a URL pronta no fim da criação e em Editar agente > WhatsApp.
- Atualizados `docs/whatsapp-oficial.md` (três níveis de URL, erro do 404), spec/arquitetura.md e AGENTS.md.

## 2026-09-18: A instalação serve a política de privacidade, e um ícone para o app (v0.16.0)

- **O app precisa ser publicado** para atender número de produção, e a Meta pede política de privacidade e ícone antes. Mandar o operador hospedar uma página em outro lugar é atrito à toa: a instalação já tem domínio com HTTPS. `GET /privacidade` e `GET /privacidade/{slug}` devolvem HTML de `modelos/privacidade.html`, com o nome da empresa, o domínio, o contato (o e-mail do SSL) e a data. É a única rota que devolve HTML, e o Caddy passou a publicar esses dois caminhos. Slug inexistente responde 404 e não há listagem: quem não sabe o slug não descobre os clientes da instalação.
- **O texto é modelo, e a responsabilidade é do operador**: o arquivo cobre o que um agente de atendimento trata (mensagens, nome e telefone, arquivos, envio a provedores de IA, prazo e contato) e o documento diz, em letras claras, que ele deve revisar. É a política dele, não nossa.
- **Ícone pronto em `docs/imagens/icone-app.png`** (1024x1024, A claro sobre fundo escuro), gerado por `docs/imagens/gerar_icone.py`: PNG escrito com `zlib` da biblioteca padrão e borda suave pela distância aos traços, sem dependência nova só para desenhar uma letra.
- **`(#100) The App_id in the input_token did not match the Viewing App`** virou mensagem em português dizendo o que fazer: o ID do app informado não é o do app escolhido em "Gerar token". A mensagem crua da Meta não dizia, e o operador leu como "falta publicar o app", que é outra coisa.
- Atualizados `docs/whatsapp-oficial.md` (passo 9 verificação, passo 10 publicar o app, renumerado até 12), spec/arquitetura.md (rota pública) e o aviso do setup, que mostra a URL da política e o caminho do ícone antes de o operador ir ao painel.

## 2026-09-18: O token precisa de duas permissões, não três

- **O operador mostrou a tela de gerar token**: app criado pelo caso de uso "Conectar-se com clientes pelo WhatsApp" oferece `manage_app_solution`, `whatsapp_business_manage_events`, `whatsapp_business_management` e `whatsapp_business_messaging`. Não oferece `business_management`, que o documento mandava marcar.
- **Conferido endpoint por endpoint: o agente usa duas.** `whatsapp_business_messaging` para enviar e baixar mídia; `whatsapp_business_management` para número, templates, `subscribed_apps` e `webhook_configuration`. A assinatura do webhook do app usa token do app (`{app_id}|{app_secret}`), que não depende de permissão de usuário.
- **`business_management` serve só à descoberta da conta** por `/me/businesses`. Sem ela, `contas_do_token` ainda tenta os `target_ids` do `debug_token` e, se vier vazio, o setup pergunta o ID à mão. O caminho já degradava certo, então nada mudou no código: mudou o documento, que pedia permissão que o app nem lista.
- Atualizados `docs/whatsapp-oficial.md` (duas permissões, com a explicação de por que a terceira não aparece e o que ela faria) e AGENTS.md (armadilha).

## 2026-09-18: O setup descobre a conta de WhatsApp Business (v0.15.2)

- **O operador travou no ID da conta de WhatsApp Business** e disse o essencial: "essa informação não é clara de onde pegar no onboarding". É verdade: o fluxo guiado novo da Meta não mostra o WABA ID em lugar óbvio, e ele se confunde com o ID do app e com o ID do número. Perguntar um dado escondido é errar de propósito.
- **`descobrir` do canal virou dois passos**: sem `waba_id`, devolve `{contas: [...]}` com as contas que o token alcança; com `waba_id`, segue devolvendo números e templates. O setup pede app, token e chave secreta, lista as contas, e só pergunta o ID à mão quando não acha nenhuma (com a explicação de que aí o problema é o token, não o ID).
- **Dois caminhos para descobrir, nesta ordem**: `GET /debug_token` traz, em `granular_scopes`, os `target_ids` dos escopos de WhatsApp (serve para token gerado por conta); token de usuário do sistema com controle do negócio inteiro **não** traz `target_ids`, e aí as contas saem de `/me/businesses` mais `owned_whatsapp_business_accounts` e `client_whatsapp_business_accounts`. O caso do operador é o segundo. Falha no segundo caminho não derruba nada: cai na pergunta à mão.
- **O `debug_token` também confere o token** de graça, no primeiro passo: token de 24 horas ou sem permissão falha ali, com a mensagem da Meta, antes de o operador responder mais nada.
- **O fluxo guiado da Meta pede webhook como primeira coisa, e isso se pula**: quem liga o webhook é a plataforma, e o endereço do agente ainda não existe naquele momento. Ficou escrito no documento, junto de onde o ID da conta fica, para quem quiser conferir.
- Atualizados `docs/whatsapp-oficial.md` (três dados em vez de quatro, seção "onde fica o ID da conta", o que pular no painel) e spec/dados.md.

## 2026-09-18: Painel novo da Meta e as duas mudanças de 2026 no documento (v0.15.1)

- **O painel da Meta trocou "Produtos" por "Casos de uso"** (o operador mandou a tela): a configuração do WhatsApp virou um fluxo guiado em **Casos de uso > Personalizar**, com **Etapa 1. Experimente**, **Etapa 2. Configuração da produção** e **Etapa 3. Verificação da empresa**, e uma escolha entre "Integrar com API" e "Torne-se um parceiro". A documentação da Meta ainda fala em "Produtos" e "Configuração da API" em várias páginas: o painel andou na frente dos docs. `docs/whatsapp-oficial.md` passou a seguir os nomes do painel, na ordem das etapas, e a dar link direto sempre que existe um, que é o que não muda de lugar quando a interface muda. Os docs da Meta também migraram de `/docs/whatsapp/cloud-api/` para `/documentation/business-messaging/whatsapp/`.
- **Desde 1º de outubro de 2026 a mensagem de serviço é cobrada**: a resposta em texto livre dentro da janela de 24 horas, que é justamente o que o agente manda, deixou de ser gratuita. Tarifa de utilidade do país, depois de 1.000 grátis por número por mês, sem acumular. **Conta sem forma de pagamento não tem mensagem de serviço entregue**, o que torna o meio de pagamento pré-requisito para testar, não detalhe de produção. Substitui "cobrança por conversa" nos textos do setup e em spec/arquitetura.md.
- **Desde 15 de janeiro de 2026 a Meta proíbe assistente de IA de propósito geral no WhatsApp.** Não afeta este projeto: agente de atendimento de uma empresa continua permitido, é o caso de uso da plataforma. Ficou registrado no documento como limite a respeitar no prompt, para ninguém transformar o agente em assistente geral.
- Atualizados `docs/whatsapp-oficial.md`, os textos de `setup/lib/whatsapp.sh` e o rótulo do canal, e spec/arquitetura.md (custo).

## 2026-09-18: WhatsApp oficial, parte 3 da fase 5 (v0.15.0)

- **Três camadas de webhook, todas pela API**: o app assina o campo `messages` do objeto `whatsapp_business_account` (`POST /{app_id}/subscriptions`, com o token do app `{app_id}|{app_secret}`), a conta passa a entregar a este app (`POST /{waba_id}/subscribed_apps`) e o número ganha o endereço deste agente (`POST /{phone_number_id}` com `webhook_configuration`). A primeira é o alicerce: sem ela a Meta não entrega nada, nem para um endereço apontado no número. Por isso o setup pede também o **ID do app**.
- **Cada agente tem o próprio endereço de webhook, apontado pela API** (`webhook_configuration` do número, o "webhook override" da Meta). Isso resolve o que parecia obrigar um app da Meta por agente: a URL do app é uma só, mas cada número pode ter a sua. O operador não cola URL nenhuma no painel: a criação do agente confere o token, inscreve o app nos webhooks da conta (`POST /{waba_id}/subscribed_apps`) e aponta o número (`POST /{phone_number_id}`). Remover o agente devolve o webhook do número para a URL do app.
- **A verificação (`hub.challenge`) é respondida pelo próprio token da URL.** A Meta confere o endereço na hora em que ele é apontado, antes de o agente existir no banco; olhar o banco ali falharia sempre. Quem sabe o token já sabe o segredo do webhook, então não há segundo segredo a guardar. Entrou `responde_verificacao` no contrato do canal e uma rota `GET /webhook/{canal}/{token}`, que nos outros canais responde 404. Assinatura do corpo: `X-Hub-Signature-256` (HMAC SHA-256 com o `app_secret`), e webhook inválido recebe 401, como manda spec/arquitetura.md.
- **Webhook de outro número é ignorado**: o `phone_number_id` do corpo é conferido contra o do agente. Um app com vários números continua entregando certo mesmo se um override ficar para trás.
- **O template do aviso virou parte do `handoff_destino`**, e a coluna `handoff_template` saiu (migração `0012`). O template é como se avisa o destino neste canal, junto do número: fora da janela de 24 horas a Meta não aceita outra coisa. Nenhum canal lia a coluna, e assim o template se troca com um PATCH comum, sem campo extra no agente.
- **O aviso tenta texto livre e cai no template**: se o destino escreveu ao agente nas últimas 24 h, o aviso vai inteiro, com quebra de linha; fora disso vai o template, com contato, resumo e código como parâmetros (sem quebra de linha, que a Meta recusa). Sem template aprovado, o handoff acontece do mesmo jeito e a falha diz o que fazer. O aviso de retomada por tempo só chega dentro da janela: template é aviso de handoff, não conversa.
- **Template esperado: três parâmetros** (contato, resumo, código). O setup lista os templates da conta e só deixa escolher os aprovados com essa forma; sem nenhum, mostra o texto sugerido para o operador mandar aprovar e deixa seguir sem template.
- **Digitando preso à mensagem que chegou**: na Cloud API o indicador vai junto do "marcar como lida" (`status: read` com `typing_indicator`) e some ao responder ou em 25 s. `digitando` passou a receber o id da última mensagem recebida; os outros canais ignoram. Sem isso o canal precisaria guardar esse id em algum lugar só dele.
- **Não existe pausa por resposta pelo aparelho**: o número da Cloud API não roda no celular. A devolução é `/retomar` ou 👍 mandados por quem recebeu o aviso, no chat dele com o agente, ou o prazo do agente. Reação do contato não mexe em nada.
- **Uma mensagem por webhook**: a Meta manda uma notificação por mensagem recebida. Se um corpo trouxer mais de uma, só a primeira é lida; o `Evento` do contrato descreve uma mensagem, e mudar isso mexeria em todos os canais por um caso que a Cloud API não produz.
- **`docs/whatsapp-oficial.md`**: passo a passo com links para preparar a Meta (portfólio de negócios, verificação, app, conta e número, pagamento, nome de exibição, usuário do sistema com token permanente, ID e chave secreta do app, template do aviso), erros comuns, caminho rápido com o número de teste e comparação com a WAHA. O repositório é público e os alunos vão pelo mesmo caminho; o setup aponta para o documento na tela das credenciais.
- Atualizados spec/arquitetura.md (contrato do canal, rotas, webhook override), spec/dados.md (destino de handoff do WhatsApp oficial, fim do `handoff_template`), spec/telas.md (telas 6 e 8) e spec/fases.md.

## 2026-09-18: Conversa pessoal não entra no log, e manutenção não dispara alarme (v0.14.2)

- **Achado no relatório da validação**: linhas como `conversa que o agente ainda não atende, de: 80869972770836@lid, texto: "falta só as guria"`. O número pareado é um celular que a pessoa também usa, `message.any` traz tudo que sai dele, e o texto das conversas particulares estava indo para o log da API. O `texto` saiu do log (entrou na v0.13.3 para diagnóstico e não vale o preço); o remetente fica, que é o que resolve o diagnóstico.
- **`canal_fora_do_ar` quatro vezes durante os testes**: era o setup recriando o contêiner (atualização e preparação do nome do aparelho), não número caindo. A janela de silêncio só era marcada quando o operador pedia um QR code novo. Agora o setup avisa a plataforma antes de mexer no contêiner (`POST /admin/canais/waha/manutencao`), e a sessão parada nos minutos seguintes não alarma.
- Regra que fica: o que passa por `message.any` é conversa de quem emprestou o número ao agente. Nada além do necessário para operar sai de lá.

## 2026-09-18: O áudio leva o idioma (v0.14.1)

- **Achado na validação**: um "Boa noite" voltou transcrito como "Боооооооую ночь." O transcritor adivinha o idioma pelo som, e áudio curto ou com ruído cai em outra língua; o mesmo contato mandou outro áudio que saiu certo.
- **`IDIOMA_AUDIO` (padrão `pt`)** vai junto na transcrição: `language` na OpenAI e na Groq, e uma frase no prompt quando quem transcreve é o Gemini. Vazio volta a deixar o transcritor adivinhar, para quem atende em vários idiomas.
- É configuração da instalação, não do agente: quem precisar de agentes em idiomas diferentes na mesma VPS vai pedir, e aí vira campo do agente.

## 2026-09-18: O código do handoff virou opcional (v0.14.0)

- **Pergunta do operador**: "precisa do código?". Na maior parte das vezes não: na conversa do contato ela já está identificada, e no chat de quem recebeu o aviso o código só resolve quando há mais de uma conversa em atendimento.
- **`/retomar` sozinho** passou a valer: na conversa do contato devolve aquela; no chat do destino devolve a única em atendimento. Com duas ou mais, o destino recebe a lista com um código por conversa e o nome de quem está do outro lado, e escolhe. Sem nenhuma, ouve que o agente já está respondendo todas.
- **`/retomar <código>`** continua valendo em qualquer situação, que é o caminho de quem só tem o aviso na mão.
- Pedir um código quando não há dúvida é atrito à toa, ainda mais para quem está com o celular na mão no meio de um atendimento.

## 2026-09-18: `/retomar` do número do agente vale em qualquer conversa (v0.13.5)

- **O log fechou o caso**: `acao: pausar, de: 1100000000000@lid`. O operador escreveu o `/retomar` pelo WhatsApp Web do número do agente, dentro da conversa do contato, e aquilo era lido como ele assumindo a conversa.
- **Quem escreve do número do agente é o operador falando com o sistema**, e o código diz qual conversa devolver: o comando passou a valer em qualquer chat, não só no de quem recebeu o aviso. Conversa comum escrita do aparelho continua sendo intervenção humana, que é o que o operador espera.
- **O aviso de handoff ficou explícito** sobre os dois caminhos, em vez de "reaja com 👍 na conversa ou mande /retomar aqui", que lia como se os dois fossem no mesmo lugar: 1) joinha na conversa com o contato; 2) `/retomar <código>` respondendo o aviso.
- Custou quatro rodadas de teste porque cada versão anterior cobria um caminho que não era o que o operador usava. A lição, já aplicada nas v0.13.3 e v0.13.4: nenhuma saída do webhook sem log, com o remetente.

## 2026-09-18: `/retomar` do aparelho do agente, e nada mais some calado (v0.13.4)

- **Ponto cego achado ao investigar o `/retomar` que não funcionava**: fala de saída numa conversa que o agente ainda não atendeu devolvia 200 sem uma linha de log. A WAHA registrava o envio com 200 e do nosso lado não havia nada, o que torna o diagnóstico impossível. Agora toda saída do webhook tem log.
- **`/retomar <código>` escrito no chat do handoff pelo aparelho do agente** passou a valer como comando. O aviso chega no celular de quem recebe o handoff, mas o operador que tem o aparelho do agente na mão responde dali com a mesma naturalidade, e isso caía na regra de intervenção humana (pausa) em vez de devolver a conversa.

## 2026-09-18: Log do webhook diz de quem é a mensagem (v0.13.3)

- **Um `/retomar` que não funcionava não aparecia no log**: nem como comando, nem como conversa, nem como ignorado. As linhas de ignorado diziam só "mensagem de grupo", sem dizer de qual conversa, o que não permite concluir nada.
- `webhook_ignorado` e `webhook_aceito` passaram a levar a conversa, o telefone resolvido e os primeiros 60 caracteres do texto. Mensagem de grupo e conversa não atendida também levam o chat.
- É log local do operador, na VPS dele, e é o que transforma "não funcionou" em uma linha que aponta a causa.

## 2026-09-18: O aviso de handoff dizia um número que não existe (v0.13.2)

- **Achado do operador**: o aviso chegou com "Assumi a conversa com +1100000000000". Aquilo era o `@lid` do contato formatado como telefone: são dígitos, mas não são o número de ninguém, e quem recebe o aviso tenta ligar para o nada.
- **Quem monta o nome do contato é o serviço de handoff**, não o canal: nome e telefone do Contato (que a v0.11.1 passou a resolver por trás do `@lid`), na forma `Maria (+55 51 99999-8888)`. Sem nome, só o telefone; sem telefone, o rótulo do canal. Vale para o aviso de handoff e para os dois avisos de retomada.
- **`numero_legivel` não formata mais `@lid` como telefone**: devolve "o contato".
- **`/retomar` do destino que escreve por trás de um `@lid`**: a comparação era só pelo id guardado no cadastro do destino, e quem escreve nem sempre aparece por ele. Agora o telefone resolvido desempata (`e_o_destino`), como já era para o contato na lista de quem pode falar.

## 2026-09-18: Arquivo de mídia dura 24 horas, o texto fica (v0.13.0)

- **Observação do operador**: o modelo não ouve nem enxerga; o que chega nele é sempre o texto da transcrição ou da visão. Então o arquivo é insumo, não acervo.
- **O arquivo sai do disco um dia depois de lido** (`midia_horas_no_disco`, job `limpar_midia` diário de madrugada); o texto lido fica no registro de Mídia e na mensagem, enquanto a conversa existir. Diário e não de hora em hora (correção do operador na revisão): o arquivo acaba durando de um a dois dias, e ninguém se importa com isso; o que importa é não guardar por semanas. O registro e o hash continuam: o cache por hash segue valendo e um arquivo reenviado não é lido de novo, mesmo depois de o arquivo sumir.
- **Campo `arquivo_apagado_em`** (migração `0011`) em vez de deixar `caminho_arquivo` apontando para o vazio: quem lê o banco vê que o arquivo saiu, e não que ele se perdeu.
- Substitui o `limpar_midia` de 90 dias previsto na fase 7. Menos dado de cliente parado na VPS e menos disco: numa VPS de 20 GB, áudio e foto de atendimento enchem rápido.

## 2026-09-17: Arquivo de mídia morava num endereço que o worker não alcança (v0.12.3)

- **Áudio, imagem e PDF falhavam todos com `ConnectError`** no download, mesmo depois da correção do cabeçalho (v0.11.2). A WAHA baixa e guarda o arquivo, mas anuncia o `media.url` com o endereço que conhece de si mesma, `http://localhost:3000/...`; dentro do contêiner do worker, `localhost` é o próprio worker.
- **Duas voltas de proteção**: `WAHA_BASE_URL=http://waha:3000` no Compose, que é o jeito certo de a WAHA anunciar o endereço, e a reescrita da URL no canal (`localhost`, `127.0.0.1` e afins viram o endereço da WAHA na rede do Compose), que funciona mesmo em instalação que já existe ou se a variável mudar de nome.
- **Alarme falso durante o pareamento**: pedir um QR code novo passa por `STOPPED`, e a v0.12.0 avisava "número fora do ar" sobre o que o próprio operador estava fazendo. A rota de reiniciar marca uma janela de 15 minutos no Redis, e nem o webhook nem a ronda alarmam nela.

## 2026-09-17: Aparelho conectado com o nome do agente (v0.12.2)

- **Pedido do operador**: no celular, o aparelho conectado aparecia como "Ubuntu Firefox". Quem abre Aparelhos conectados precisa reconhecer qual agente é aquele.
- **`WAHA_CLIENT_DEVICE_NAME` e `WAHA_CLIENT_BROWSER_NAME`**: o nome vira `Agente (Empresa)`, com `Desktop` como navegador, que no GOWS faz o WhatsApp mostrar só o nome, sem "Firefox" na frente. Outros valores fora da lista (Chrome, Firefox, Safari, Edge, Opera, IE, Desktop) fazem o WhatsApp mostrar "Outro dispositivo" e jogar o nome fora.
- **O nome é da instalação inteira e vale no instante da leitura do QR code**, não por sessão: o setup grava o nome do agente e recria o contêiner da WAHA antes de cada pareamento. Sessão já pareada volta sozinha em segundos, e o nome dela no celular não muda (ficou gravado no aparelho quando foi lida).
- **`GET /admin/canais/waha`** diz se a WAHA está no ar e em que versão: é por onde o setup espera o contêiner voltar depois de recriado, em vez de dormir um tempo fixo.

## 2026-09-17: Quem diz o id do número do handoff é o WhatsApp (v0.12.1)

- **Achado no teste**: o handoff abriu (o agente calou), mas o aviso não chegou: `handoff_incompleto` com "aviso de handoff não chegou: CredencialInvalida". Os números que apareceram nas falhas do mesmo teste (`555197035844`, `555133332222`) mostraram a causa provável: naquela região o WhatsApp usa o número **sem** o nono dígito, e o destino estava cadastrado com ele.
- **`check-exists` na escolha do destino**: o setup pergunta ao WhatsApp se o número existe e guarda o `chatId` que ele devolve, que hoje pode até ser um `@lid`. Número sem WhatsApp é recusado na hora, com o motivo, em vez de virar um handoff mudo semanas depois.
- **Rede de segurança no envio**: se o aviso falhar com o id guardado, o canal pergunta o id de verdade e tenta uma vez, registrando na falha que o destino precisa ser trocado no menu. Assim o agente já existente volta a avisar sem depender de reconfiguração.
- **Erro do envio passou a levar o motivo** da WAHA, não só o tipo da exceção. Foi a terceira vez que um erro genérico custou uma rodada de diagnóstico (antes: download de mídia e sessão).

## 2026-09-17: Número que sai do ar deixa de ser silêncio (v0.12.0)

- **Lacuna conhecida desde a v0.9.0**: o WhatsApp derruba o aparelho sem avisar (número em outro celular, muito tempo offline, alguém desconectou na mão) e o agente ficava mudo sem ninguém saber. O evento `session.status` chegava e era ignorado.
- **`Acao.ALERTA`** no contrato do canal: o canal avisa um problema que deixa o agente mudo, e o webhook registra Falha (`canal_fora_do_ar`) em vez de gravar conversa. Pareamento em andamento (`STARTING`, `SCAN_QR_CODE`) não gera alerta: alguém está com o QR code na tela.
- **Ronda a cada dez minutos** (`confere_whatsapp`, em `canais/waha/vigia.py`) como rede de segurança para quando nem o evento chega (contêiner reiniciado, WAHA fora do ar). Uma falha por agente por hora, controlada no Redis: o operador precisa saber, não ser inundado.
- **Aviso no menu**, consultado uma vez ao abrir: "Número fora do ar no WhatsApp: Spencer (FAILED)", com o caminho para ler o QR code de novo. A falha em Ver consumo e falhas conta o histórico; o menu conta o agora.
- Avisar pelo próprio WhatsApp não serve aqui: se a sessão caiu, é justamente por ela que não dá para mandar nada.

## 2026-09-17: Áudio não era baixado da WAHA (v0.11.2)

- **Achado no teste de ponta a ponta**: o agente respondeu texto, mas o áudio virou `midia_download_falhou` e o contato recebeu o pedido para escrever. Causa: quando o QR code em texto entrou (v0.9.0), o `Accept: application/json` foi para o cabeçalho compartilhado das chamadas à WAHA, e ele acompanhava também o download do arquivo, que é binário.
- **Cabeçalhos separados**: `cabecalho()` só com a chave, para baixar arquivo; `cabecalho_json()` para a API, onde o `Accept` é justamente o que faz o QR code vir em texto. Teste de regressão nos dois.
- **Erro de download agora diz o status HTTP** (`a WAHA recusou o arquivo: HTTP 406`), que é o que faltava para achar isso em minutos em vez de por eliminação.
- **`hasMedia` deixou de ser exigido** para reconhecer o anexo: o que vale é a URL do arquivo. `hasMedia` nem sempre vem, e `hasMedia` sem URL é arquivo que a WAHA não baixou.

## 2026-09-17: Número escondido atrás de @lid barrava quem podia falar (v0.11.1)

- **Achado no primeiro teste de ponta a ponta**: o agente não respondeu a um número liberado na lista. O log mostrou `contato fora da lista do agente`, e o log da WAHA mostrou a razão: o WhatsApp entrega a conversa endereçada por `@lid` (id oculto), não pelo telefone. A comparação não tinha como bater.
- **O telefone de verdade vem resolvido pela WAHA** (2026.8.1+) em `pn` ou, no GOWS, em `_data.Info.SenderAlt`; em grupo, no participante. `telefone_do_contato` procura nesses campos e guarda o número no Contato; a conversa continua endereçada pelo `@lid`, que é por onde se responde. `@lid` nunca é lido como telefone: os dígitos dele não são o número de ninguém.
- **Nono dígito**: a comparação passou a aceitar o mesmo celular com e sem o 9 (`555133332222` e `5551933332222`), que é como o mesmo número aparece conforme a idade do cadastro. DDDs diferentes continuam diferentes.
- **Contato barrado vira Falha** com o identificador, visível em Ver consumo e falhas. Antes só havia uma linha de log em nível info: o operador via o agente mudo e não tinha como saber que a lista tinha barrado, nem quem.

## 2026-09-17: Atendente assume a conversa no Chatwoot, com prazo de volta (v0.11.0)

- **Pedido do operador**: no Chatwoot, mensagem de atendente (outgoing que não é do bot) tem de abrir a conversa, tirar o bot e atribuir a quem respondeu; passado o prazo do onboarding, a conversa volta para Pendente com o bot conduzindo.
- **Mesma mecânica da WAHA**: o evento virou `Acao.PAUSAR`, que grava a fala como de humano e abre o handoff sem IA e sem aviso, com `retomar_em` pelo `retomada_automatica_horas` do agente. O que muda por canal é o efeito visível, que fica no canal: `assumir_no_canal` (Chatwoot: status aberto e atribuição a quem escreveu; WhatsApp: nada, porque a conversa não tem dono).
- **O canal é avisado pelo worker**, não pelo webhook: a regra de só validar, gravar e agendar continua valendo, e o Chatwoot silencia o bot se o webhook demorar. Job novo `assumir_conversa`.
- **`retomada_automatica_horas` passou a valer no Chatwoot** (`retoma_por_tempo` agora é False só no nativo, onde não existe atendente). É a rede de segurança para a conversa que o atendente esqueceu de devolver.
- **A retomada por tempo devolve no canal antes de fechar o handoff**: `devolver_ao_agente` (Chatwoot: pendente e sem atribuição) e só então o handoff fecha. Se o canal recusar, o handoff fica aberto e a tentativa vai para dez minutos depois, com falha registrada: fechar sem o canal deixar criaria um agente achando que fala onde está calado.
- **Desatribuir junto da devolução**: conversa pendente com dono confunde a fila de quem olha o Chatwoot, e quem conduz dali em diante é o bot.
- A pergunta das horas entrou na criação do agente Chatwoot, em Editar agente > Handoff e ao ligar um agente nativo no Chatwoot, com o texto do canal (lá a devolução normal é voltar para Pendente).

## 2026-09-17: Pessoa da equipe assume a conversa, joinha devolve (v0.10.0)

- **Pedido do operador**: quando alguém da empresa responde pelo próprio aparelho, o agente tem de calar na hora, respeitando o tempo de retomada do onboarding, e voltar quando essa pessoa reagir com 👍 numa mensagem.
- **Como o canal percebe**: a sessão passou a assinar `message.any` em vez de `message`, que traz também o que sai do número, com o campo `source`: `api` é o agente falando pela WAHA, `app` é gente digitando no celular ou no WhatsApp Web. Sem isso não dava para separar as duas coisas sem guardar estado (a primeira ideia, comparar os ids enviados, tinha corrida com o commit do turno).
- **Ação nova no contrato do canal**: `Acao.PAUSAR`, que grava a mensagem como fala de humano e cala o agente. `handoff.pausar_por_humano` abre o handoff sem chamar IA e sem avisar o destino (foi a própria pessoa que assumiu), com `retomar_em` pelo `retomada_automatica_horas` do agente. A regra de nunca chamar IA dentro do webhook continua valendo.
- **Joinha devolve**: `message.reaction` com 👍 vindo do próprio número (`fromMe`) fecha o handoff daquela conversa, com `retomado_por: joinha`. Tons de pele e seletor de variação entram na comparação. Reação do contato não mexe em nada: quem devolve é a equipe. O aviso de handoff agora oferece as duas saídas, 👍 ou `/retomar <código>`.
- **A fala da equipe entra na memória do agente, marcada**: já era assim desde a fase 3 (mensagem de atendente vira fala do assistente com prefixo), e agora vale também para quem responde pelo aparelho na WAHA. O prefixo virou `(atendente da equipe)` e, antes da primeira fala dessas, entra um aviso do sistema explicando que aquilo foi escrito por uma pessoa e vale como combinado com o contato. O aviso só aparece em conversa que teve atendente: em conversa comum seriam tokens à toa em todo turno. Sem isso, o contato que volta dias depois era atendido por um agente que não sabia o que a equipe tinha prometido.
- **Sessões já criadas**: `POST /admin/clientes/{c}/agentes/{a}/waha/webhook` reescreve a configuração da sessão com os eventos de hoje, e `asimov atualizar` chama para cada agente WAHA. Sem isso, um agente criado na v0.9.x nunca receberia reação nem mensagem do aparelho.

## 2026-09-17: Escolher o grupo do handoff pelo nome (v0.9.3)

- **Pedido do operador**: o destino do handoff na WAHA precisa ser uma escolha clara entre número e grupo, e com muitos grupos dá para procurar pelo nome. A tela virou dois passos: "Um número de WhatsApp" ou "Um grupo"; no grupo, com mais de 9 na lista, o setup pede parte do nome e filtra ignorando acento e maiúscula (`normaliza_linhas`, um processo só para a lista inteira), com a opção de procurar outro nome sem sair.
- **Lista de grupos mais leve**: `GET /api/{sessao}/groups?limit=200&sortBy=subject&sortOrder=asc&exclude=participants`. Sem os participantes, que não servem aqui e engordam a resposta.
- **Número ainda é o caminho quando não há grupo**: número sem grupo nenhum (ou WAHA que ainda não sincronizou depois do pareamento) mostra o porquê e volta para a escolha por número, em vez de deixar o operador travado.

## 2026-09-17: Quem o agente atende (v0.9.2)

- **Pedido do operador ao parear o primeiro número**: poder deixar o agente respondendo só a números escolhidos enquanto testa, ou abrir para qualquer pessoa. Campo `contatos_permitidos` no Agente (migração `0010`), lista vazia por padrão, aplicada no webhook antes de gravar qualquer coisa: quem está fora não vira conversa nem turno, só log. Vale para qualquer canal, não só a WAHA.
- **Comparação tolerante**: o operador digita `11988887777` ou `+55 (11) 98888-7777` e o canal manda `5511988887777@c.us`. Bate quando o mais curto é o fim do mais longo, com pelo menos 8 dígitos; números de DDDs diferentes continuam diferentes.
- **Grupo o agente nunca responde** (já era assim desde a v0.9.0, menos o grupo do handoff): agora está escrito na tela, porque era a primeira dúvida de quem pareia um número.
- **Na criação e em Editar agente > WhatsApp**: "Qualquer pessoa que mandar mensagem" ou "Só os números que eu listar", separados por vírgula. A ficha do agente mostra quem ele atende.

## 2026-09-17: Aviso de API não oficial e correções do primeiro teste da WAHA (v0.9.1)

- **Aviso de que a WAHA é API não oficial**, pedido pelo operador ao ver a tela de canais: o rótulo do canal passou a dizer "API não oficial" e, antes de qualquer coisa (antes até de subir o contêiner), o fluxo mostra o que isso significa (a Meta não homologa nem dá suporte, o número pode ser bloqueado, use um chip só do agente, valem as regras do WhatsApp) e pede confirmação. Vale na criação e ao ligar um agente que já existe. spec/telas.md.
- **Selecionar o WhatsApp voltava ao menu sem criar o agente**: `instala_timer_waha` era a última coisa de `garante_waha` e, quando o systemd recusava a unidade, o `set -e` derrubava a ação inteira. Agora o timer é conforto, não requisito: falhar só gera aviso, e a criação segue. O fuso no `OnCalendar` (systemd 252+) é conferido com `systemd-analyze calendar` antes de gravar.
- **`espera_url` sem o número de tentativas** virava erro de variável não definida com `set -u` e a API não era esperada depois de ser recriada para enxergar a chave da WAHA: a primeira chamada do fluxo caía numa API ainda subindo. Passou a ter padrão de 24 tentativas, e `garante_waha` espera de verdade.
- **Nomes dos passos**, também apontados pelo operador: "qrencode (desenha o QR code aqui)" e "WAHA no ar" viraram "Leitor de QR code no terminal", "Serviço do WhatsApp (WAHA)" e "Plataforma ligada ao WhatsApp". O total de passos passou a contar só os que vão rodar (antes marcava 3 e mostrava 2 quando o `qrencode` já existia).

## 2026-09-17: WhatsApp pela WAHA, parte 2 da fase 5 (v0.9.0)

- **A WAHA não sobe na instalação** (decisão do operador): nada muda no onboarding e quem só usa Chatwoot não carrega o contêiner. Ela entra quando o operador escolhe o canal WhatsApp ao criar ou conectar um agente (`garante_waha` em `setup/lib/waha.sh`): grava `WAHA_ATIVA=1` e `VERSAO_WAHA` no `.env`, baixa a imagem e sobe o serviço do perfil `waha` do Compose. A partir daí o `dc` (deploy/compose.sh) sempre inclui o perfil, para um `dc up` não derrubar o contêiner. A `WAHA_API_KEY`, ao contrário, nasce na instalação mesmo sem a WAHA: assim ligar o WhatsApp depois não obriga a API a reiniciar para enxergar a chave.
- **Imagem fixada em `devlikeapro/waha:gows-2026.8.2`** (`gows-arm-...` em VPS arm), a imagem só com a engine GOWS. Sem porta publicada: quem fala com a WAHA é a API, pela rede do Compose. Volumes para as sessões (`/app/.sessions`) e para os arquivos de mídia (`/app/.media`, `WHATSAPP_FILES_LIFETIME=3600`, para o arquivo durar do webhook até o fim do turno). Nomes das variáveis conferidos na documentação: `WAHA_DASHBOARD_ENABLED`, `WHATSAPP_SWAGGER_ENABLED`, `WAHA_EVENTS_DOWNLOAD_MEDIA`, `WAHA_API_DOWNLOAD_MEDIA`.
- **A pausa do handoff no canal direto é o status da conversa aqui**, não um estado no canal: no WhatsApp não existe "conversa aberta com atendente" para perguntar. Em vez de `if canal ==` no turno, `agente_pode_falar` passou a receber o `status` da conversa; o Chatwoot continua perguntando ao Chatwoot e a WAHA responde pelo status. Sem estado duplicado entre banco e Redis.
- **O aviso de handoff leva o código**: `canal.transferir` passou a receber o `codigo`, gerado antes do aviso. A WAHA manda ao número ou grupo do destino uma mensagem com o contato, o motivo, o resumo e "mande /retomar ABC123". O Chatwoot ignora o código (a nota privada já basta).
- **`/retomar <código>` só vale vindo do destino**: `interpretar` passou a receber o `handoff_destino` do agente, e só a mensagem daquele chat vira comando (`Acao.RETOMAR_POR_CODIGO`); de qualquer outro número o mesmo texto é conversa comum. Mensagem de grupo é ignorada, exceto o grupo do handoff.
- **Retomada automática**: job `retomada_automatica` no worker, cron a cada minuto, fecha os handoffs com `retomar_em` vencido e avisa o destino (`avisa_destino` no contrato do canal; no Chatwoot e no nativo não faz nada). As horas são perguntadas na criação do agente WAHA (padrão 4, 0 deixa parado até o comando).
- **O destino do handoff é escolhido depois do pareamento**, porque a lista de grupos vem do próprio número: criar agente, ler o QR code, escolher número digitado ou grupo. Cancelar o QR (Esc) deixa o agente criado e o pareamento fica em Editar agente > WhatsApp.
- **A WAHA se atualiza sozinha, com rede de segurança** (decisão do operador): a WAHA acompanha um protocolo que a Meta muda sem avisar, e imagem parada um dia deixa de conectar. Timer do systemd (`asimov-waha.timer`, domingo 4h de Brasília, com atraso sorteado de até 30 min e `Persistent=true`) roda `deploy/atualiza_waha.sh`: procura a tag mais nova com o prefixo da arquitetura no Docker Hub, guarda quais números estavam conectados, troca a imagem e espera todos voltarem em até 2 minutos; se algum não voltar, devolve a versão anterior e deixa o aviso no menu. O timer roda no host, não no worker: dar o socket do Docker a um contêiner seria dar a VPS inteira.
- **Só tags de versão** (`gows-2026.8.2`), nunca rótulos móveis como `gows` ou `latest`: a versão instalada precisa ser sempre conhecida, e quem troca é o timer ou o operador. Menu novo "WhatsApp (WAHA)", que aparece quando a WAHA está ligada: versão, quando foi conferida, ligar ou desligar a atualização automática e procurar versão nova agora.
- **A versão do Core mudou o jogo em 2026.6.1**: até ali a imagem gratuita atendia uma sessão só (`OnlyDefaultSessionIsAllowed`) e não enviava mídia, o que quebraria uma sessão por agente. Da 2026.6.1 em diante tudo do Plus veio para a imagem gratuita; a instalação fixa a `2026.8.2`, posterior a essa mudança. Mais um motivo para o timer existir.
- **Uma sessão por agente**, com nome derivado do nome do agente mais um sufixo sorteado, e chave HMAC própria por agente (guardada cifrada nas credenciais). Remover o agente faz logout (o aparelho some da lista do WhatsApp) e apaga a sessão.
- Atualizados spec/arquitetura.md (contrato do canal, rotas da WAHA, variáveis), spec/telas.md (telas 6 e 8), spec/dados.md (destino de handoff da WAHA) e spec/fases.md.

## 2026-09-17: Agente nasce cru (v0.8.11)

- **Decisão do operador**: o agente criado deve ser o mais cru possível, para personalizar depois com vibecoding e ferramentas. Com a busca ligada, falar do que buscou não é erro do agente; o problema era o padrão. Agente de atendimento em geral não tem busca.
- **Ferramentas**: nenhuma vem ligada (`padrao` falso nas fichas; migração `0009` troca o padrão da coluna para `[]`). A criação termina, em todo canal, numa lista de marcar toda desmarcada; o agente nasce só com as marcadas. Substitui "calculadora e busca ligadas por padrão" da v0.7.0 para agentes novos; os existentes mantêm as suas.
- **`persona.md` padrão de uma linha**: "Você é {{AGENTE}}, do atendimento de {{CLIENTE}}." Saíram as regras de estilo e as proibições; a plataforma continua mandando limite de mensagens, sem markdown, mídia como dado, handoff e data. Agentes existentes mantêm o próprio arquivo (o setup nunca sobrescreve prompt).
- **Criação do nativo**: nome, empresa, ritmo e ferramentas. Mensagens por resposta e modelo saíram da criação e continuam em Editar agente.

## 2026-09-17: Mensagem sem markdown e data no turno (v0.8.10)

- **Teste do operador na VPS com a v0.8.9** (Isa, gpt-5.5, terminal): sem o erro de JSON; buscou quando precisava. Três achados.
- **Citação da busca em markdown**: a busca da OpenAI anexa "([site](link?utm_source=openai))", que no WhatsApp aparece cru. A instrução já proibia markdown; agora `sem_markdown` (em `conversas/divisao.py`) limpa toda mensagem antes do envio, em qualquer canal: citação vira "(site)", link vira o texto, some negrito com `**`, título com `#` e o `utm_source=openai`.
- **Data**: o modelo não recebia a data; acertou "que dia é hoje" por ter buscado antes. Toda chamada de resposta leva "Agora é <dia da semana>, dd/mm/aaaa, hh:mm no horário de Brasília", por último nas instruções para não quebrar o cache do prompt fixo.
- **Fica com o operador**: prompt da persona (a Isa, de um escritório de advocacia, ofereceu curso da Asimov) e custo do gpt-5.5, que raciocina por padrão (15,7 s e US$ 0,076 no turno com busca). A cotação veio incoerente (venda abaixo da compra, de um site de terceiros citado como Banco Central): erro do modelo lendo a fonte, sem trava na plataforma.

## 2026-09-17: Resposta no formato estruturado nativo (v0.8.9)

- **Achado na VPS**: agente novo (Isa, gpt-5.5, terminal) perguntado sobre o dólar de ontem buscou na web e respondeu "Esse erro indica que o JSON enviado está vazio ou mal formatado. Me manda o JSON?". Histórico limpo; o turno gastou 19,8 mil tokens de entrada e 359 de saída, o dobro de um turno normal.
- **Causa provável, não reproduzida**: a resposta saía pela tool `final_result`. Quando o modelo erra o formato, a PydanticAI manda o aviso de correção e, pela API Responses, o aviso sem tool vai como mensagem do usuário: o modelo achou que o contato mandou um erro de JSON. Refeito 4 vezes no container, o turno deu certo nas 4 com uma chamada só.
- **Resposta no formato estruturado nativo** (`NativeOutput`, `json_schema` estrito) quando todo modelo do agente aceita (principal e fallback; perfil da PydanticAI); senão, tool como antes. Aceitam: OpenAI, Anthropic, Gemini e gpt-oss da Groq; llama da Groq não. No teste nativo foi mais rápido (5,2 a 5,5 s contra 6,7 a 9,1 s). Sem tool de resposta, `tool_choice` volta a `auto`: o modelo não é mais obrigado a chamar alguma tool, o que levava o gpt-5.1 a chamar a calculadora com "1+1".
- **Instrução de saída**: aviso sobre formato, JSON ou validação vem do sistema e fala da própria resposta, nunca do contato.
- **Falha `resposta_corrigida`** com os avisos recebidos quando o modelo precisa corrigir a resposta no turno: da próxima vez a causa aparece em Ver consumo e falhas, em vez de deduzida.

## 2026-09-17: Uma ferramenta por arquivo (v0.8.8)

- **Pedido do operador**: toda ferramenta dos agentes num `.py` separado, para ir adicionando ferramentas novas. `ia/ferramentas.py` virou o pacote `ia/ferramentas/`: `base.py` (ficha `Ferramenta`), `calculadora.py`, `busca_web.py` e `registro.py` (catálogo, padrão, valida, monta).
- **A ficha mora com a ferramenta**: nome (igual ao do arquivo e ao que fica gravado no agente), rótulo e descrição do menu, instrução de quando usar, se vem ligada no agente novo, tools e capabilities. O padrão do agente novo sai das fichas, não de uma lista à parte.
- **Registro explícito**, como `canais/registro.py`: a ordem é a do menu. Um teste falha se um arquivo da pasta não estiver no registro ou se a ficha tiver nome diferente do arquivo. Regra em AGENTS.md e no AGENTS.md gerado para o projeto instalado.
- Sem mudança de comportamento: mesmas ferramentas, instruções e nomes gravados.

## 2026-09-17: Calculadora para qualquer conta (v0.8.7)

- **Pedido do operador: a calculadora serve para qualquer cálculo e o modelo nunca calcula sozinho.** Até a v0.8.6 ela só fazia as quatro operações, potência e parênteses; conta de porcentagem, parcela ou data o modelo fazia de cabeça.
- **`ia/calculadora.py`**, ainda sem `eval`: lista fechada de funções (raiz, abs, arredonda, piso, teto, min, max, soma, media, log, ln, exp, sen, cos, tan, radianos, fatorial, porcentagem, variacao_percentual, juros_compostos, parcela pela tabela Price, hoje, dias_entre, soma_dias), constantes pi e e, `^`, `√`, `x` entre números e `15%` como porcentagem (`7 % 2` continua resto). Datas "dd/mm/aaaa" entre aspas; "hoje" no fuso de Brasília fixo (UTC-3, sem horário de verão desde 2019).
- **Argumentos separados por `;`**, como no Excel em português: a vírgula é decimal. `, ` com espaço também separa, porque o modelo escreve assim por hábito.
- **`arredonda` é meio para cima**, como em dinheiro: 1.299,90 × 0,85 = 1.104,915 vira 1.104,92 (o `round` do Python daria 1.104,91).
- **Teto de tamanho**: resultado inteiro até 14 mil bits (abaixo do limite de 4.300 dígitos do Python para virar texto). Um contato podia pedir `((fatorial(170)^100)^100)^100` e travar o worker.
- **Instrução**: toda conta passa pela calculadora, inclusive as simples; nunca escrever número que saiu de conta sem vir dela; usar o resultado como veio; erro volta ao modelo em português para corrigir e chamar de novo. É instrução: a garantia de que o modelo obedece vem do teste na VPS e do `tools_chamadas` no consumo.

## 2026-09-17: Calculadora no formato brasileiro (v0.8.6)

- **Testes do operador na VPS com a v0.8.5**: busca da cotação de ontem funcionou (2 buscas, 20 s). A calculadora foi chamada uma vez por conta, mas o modelo leu o ponto como decimal: "918.273 dividido por 47,6" deu 19,29 (certo: 19.291,45) e "(3.847 × 219) − (15.632 / 8) + 2.901²" deu 848,95 (certo: 9.256.340). A calculadora trocava vírgula por ponto e juntava as duas leituras.
- **A calculadora lê o formato brasileiro, número a número**: com vírgula, ponto é milhar e vírgula é decimal; só pontos em grupos de 3 depois de um primeiro grupo sem zero à esquerda (87.432, 1.500.000) é milhar; o resto (0.9, 0.125, 3.14) continua decimal, porque o modelo às vezes escreve assim. Aceita ×, ÷, − e ². Devolve no formato brasileiro (462.602.712; 19.291,4495798319), sem notação científica.
- **Instrução da calculadora**: números do contato estão no formato brasileiro; passar como o contato escreveu e responder no formato brasileiro.
- **Ambiguidade aceita**: "1.250" vira mil duzentos e cinquenta. Num atendimento em português é a leitura certa.

## 2026-09-17: Raciocínio baixo nos modelos da OpenAI que vêm sem ele (v0.8.5)

- **Achado na VPS, mesmo com a v0.8.4**: o gpt-5.1 buscava a cotação e respondia que não conseguia ver o valor em tempo real, ou prometia "já te respondo" sem dar o valor.
- **Teste na VPS sem enviar nada** (turno refeito com o histórico real e com uma conversa limpa em que o agente já tinha recusado antes), instrução nova da busca nos dois casos: com o raciocínio padrão do gpt-5.1 (desligado), não deu o valor em nenhum e chegou a chamar a calculadora 4 vezes com "1+1" (32 mil tokens); com raciocínio `low`, buscou e respondeu o valor nos dois. Trocar só a instrução, sem raciocínio, também falhou nas 2 rodadas com o histórico real.
- **`OPENAI_RACIOCINIO`** (padrão `low`): vale só para modelo da OpenAI que aceita raciocínio e vem com ele desligado (perfil da PydanticAI). Os que já raciocinam (gpt-5, gpt-5.5, mini) e os que não aceitam (gpt-4o, gpt-4.1) ficam como estão; `none` mantém o padrão. Configuração, não nome de modelo no código. Custa uns segundos a mais por turno.
- **Instrução da busca**: responder com o que encontrou e nunca dizer que não consegue ver informação em tempo real, mesmo que tenha dito antes na conversa. **Calculadora**: só quando houver conta de verdade.

## 2026-09-17: Histórico com o handoff e teto por turno (v0.8.4)

- **Achado na VPS**: numa conversa do Chatwoot que já tinha passado por handoff e sido devolvida, o contato pediu a cotação do dólar. O gpt-5.1 buscou (a v0.8.3 funcionou), mas transferiu de novo com o motivo "já está em fluxo com atendente humano" e chamou `transferir_para_humano` 16 vezes no mesmo turno: 30 s e 102 mil tokens.
- **Causa**: o histórico só tinha as falas. O modelo via o pedido antigo de pessoa e o "vou chamar alguém", sem saber que a equipe tinha devolvido a conversa. E a tool respondia igual a cada chamada.
- **Handoffs viram avisos do sistema no histórico**, no ponto em que aconteceram: passou para a equipe (com o motivo) e a equipe devolveu. A instrução de handoff diz para chamar uma vez só e que pedido já atendido não conta.
- **Tool de handoff chamada de novo no mesmo turno** responde "já registrada, responda o contato agora"; vale o primeiro motivo.
- **Teto por turno**: 6 chamadas ao modelo e 8 tools (`LIMITE_CHAMADAS_MODELO_POR_TURNO`, `LIMITE_TOOLS_POR_TURNO`). Estourar vira falha do turno (mensagem de expectativa e handoff) sem as tentativas extras, que só repetiriam o gasto.

## 2026-09-17: Busca na web com instrução de uso (v0.8.3)

- **Achado na VPS**: com a busca ligada, o gpt-5.1 respondia "não consigo acessar a cotação em tempo real" sem buscar. A requisição levava `web_search`, mas nenhuma instrução dizia quando usar, e a plataforma obriga uma tool com o raciocínio desligado: o modelo ia direto para a resposta.
- **Teste na VPS com a mesma pergunta** ("qual a cotação do dólar hoje?", gpt-5.1): sem instrução, 2,6 s, 4.676 tokens de entrada, sem busca; com instrução, 5,4 s, 17.465 tokens, buscou; instrução com raciocínio baixo, 8,0 s, 19.174 tokens, sem ganho; sem a busca ligada, 513 tokens.
- **Cada ferramenta leva a própria instrução** (`Ferramenta.instrucao`), só quando está ligada. Raciocínio continua no padrão do modelo.
- **Custo da busca nativa da OpenAI**: cerca de 4,2 mil tokens de entrada em todo turno, mesmo sem buscar, e cerca de 13 mil a mais no turno que busca. Continua ligada por padrão (decisão da v0.7.0); a descrição no menu passou a dizer isso para o operador decidir por agente.

## 2026-09-17: Conectar agente nativo a um canal e feedback na conversa (v0.8.2)

- **Pedido do operador: ligar num canal, depois, o agente criado sem canal.** "Conectar a um canal" na ficha de edição do nativo e `POST .../agentes/{id}/canal`. Mantém prompt, modelos, ajustes, conversas e o token do webhook. Só sai do nativo: trocar entre canais externos continua sendo remover e criar de novo. Hoje o único canal externo é o Chatwoot; WAHA e oficial entram na mesma tela. O contrato do canal ganhou `externo`.
- **A conversa de teste do terminal passou a ser da conversa, não do agente.** `Conversa.canal` (migração `0008`, conversas antigas com o canal do agente) e `canal_da_conversa` em `agentes/servico.py`: o turno, o handoff e a retomada usam o canal da conversa. Assim o agente conectado continua conversando no terminal, e qualquer agente (Chatwoot incluso) pode ser testado lá sem mandar nada ao canal. O terminal só lê e escreve em conversa do nativo: nunca numa conversa real do canal. Substitui "só agentes nativos conversam no terminal" da v0.8.0.
- **Pedido do operador: mais feedback do agente funcionando.** Linha animada com a etapa, derivada do que a API já dava (buffer contado no terminal, `respondendo`, `digitando`, mensagens) e o resumo do último turno na leitura (modelo, latência, tokens, custo, ferramentas, erro). Ferramenta em tempo real exigiria streaming do modelo; fica no resumo do fim do turno.
- **`tools_chamadas` inclui a busca nativa do provedor** (`BaseToolCallPart`); antes só as tools nossas apareciam.

## 2026-09-17: Ajustes na criação do agente nativo (v0.8.1)

- **Achado do operador na VPS**: o nativo era criado só com nome e empresa e herdava o buffer de 8 s e a digitação de uma pessoa (até 20 s por mensagem, 90 s na resposta). No terminal isso parecia travado.
- **Criar nativo pergunta o ritmo**: "Rápido, para testar" (buffer 2 s, 30 caracteres/s e teto de 1 s: cada mensagem fica 1 s digitando, o mínimo do turno), "Como no WhatsApp" (padrões dos canais) ou tempos escolhidos. Também mensagens por resposta, ferramentas e modelo de resposta. O resto dos modelos segue o padrão e muda em Editar agente. spec/telas.md.
- **O Chatwoot continua sem essa tela**: lá o padrão é o ritmo certo e a edição já existe.

## 2026-09-17: Agente nativo (fase 5, v0.8.0)

- **A fase 5 sai em três versões**, decisão do operador: nativo (v0.8.0), WAHA e WhatsApp oficial, com validação na VPS entre elas. O operador confirmou a validação que faltava da fase 4.
- **Envio e digitando no Redis; o terminal lê pela API.** O turno roda no worker e só grava no banco no fim: lendo do banco, as mensagens chegariam todas juntas, sem o digitando entre elas. `canais/nativo/memoria.py` guarda a saída por conversa (7 dias), o digitando (prazo de 5 minutos, para worker que caiu) e a marca de humano conduzindo.
- **`depois` é a posição, não uma marca de tempo.** A lista no Redis é só do agente e só cresce: a posição não perde nem repete mensagem com relógios diferentes entre API e worker. spec/arquitetura.md.
- **A leitura devolve `respondendo`** (lock do turno ocupado). O handoff é gravado depois da última mensagem, com o resumo do modelo no meio: sem isso o terminal parava de esperar antes de ele chegar.
- **Handoff no nativo**: o canal marca humano conduzindo no Redis (é o que `agente_pode_falar` lê no turno) e o terminal mostra motivo, resumo e código. `/retomar` usa a rota de retomada do operador que já existia; ganhou assim a primeira opção no menu, só para o nativo. Mensagem mandada com handoff aberto é gravada e não agenda turno.
- **Rotas do terminal ficam em `canais/nativo/rotas.py`**, para a regra "só agente nativo" não sair de `canais/`.
- **Canal sem acesso do operador**: `pede_acesso_do_operador` no contrato. Falso no nativo; `usa_acesso` roda a operação sem procurar token. A WAHA (chave no `.env`) e o oficial (credenciais do agente) também não precisam.
- **Criar agente começa pelo canal**, na primeira instalação e no menu; só aparecem os canais já construídos. "Conversar com agente" entra como segunda opção do menu. Editar esconde Handoff no nativo; listar mostra `asimov conversar` no lugar do webhook; a pergunta de handoff pendente da v0.4.0 e `asimov handoff` só olham agentes do Chatwoot.
- **`/sair` além do Esc**: sem terminal (simulação com arquivo de respostas) não há Esc.
- **Simulação do onboarding realinhada**: a espera do DNS consome uma linha do arquivo de respostas, e desde a v0.6 as respostas seguintes caíam uma pergunta adiante (a conta escolhida era a errada, o nome do agente ficava vazio). O arquivo ganhou a linha que faltava.

## 2026-09-17: Fase 5 sem Telegram; WAHA e agente nativo

- **Telegram saiu**, decisão do operador. No lugar: WhatsApp não oficial e um agente nativo, sem canal, para conversar no terminal. O WhatsApp oficial continua. spec/visao.md, spec/usuarios.md, spec/telas.md, spec/dados.md, spec/arquitetura.md, spec/fases.md.
- **WhatsApp não oficial pela WAHA com motor GOWS** (whatsmeow). Comparados: Evolution API (Baileys; manutenção do projeto dela, mas 300 a 500 MB e licença Apache 2.0 com aviso obrigatório e licença comercial se não cumprir), Baileys direto (MIT e leve, mas serviço Node nosso para manter), GoWA e WuzAPI (Go, MIT, leves, comunidades menores). WAHA: maior comunidade, empresa por trás, Apache 2.0 sem condições e, desde a 2026.6.1, várias sessões e mídia na versão gratuita. Container subido só no primeiro agente WAHA, sem porta pública, com webhook pela rede interna.
- **Agente nativo** serve para testar e conversar no terminal (`asimov conversar`), com o mesmo buffer, turno, ferramentas, consumo e handoff dos outros canais. Não atende ninguém de fora.
- **Ordem na fase: nativo, WAHA, oficial.** O nativo não depende de canal externo e já serve para testar prompt e ferramentas; o oficial depende de template aprovado pela Meta.

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
