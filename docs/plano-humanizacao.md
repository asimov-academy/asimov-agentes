# Plano de humanização dos agentes

Escrito em 2026-09-18, a partir de três pesquisas do operador (práticas de mercado, o que os
líderes expõem na interface e o que a PydanticAI oferece). Não é spec: é o detalhamento da **fase
10**, que está resumida em `spec/fases.md` com o critério de aceite.

Decidido pelo operador em 2026-09-18: as cinco etapas são uma fase só, a fase 10, depois da base de
conhecimento; o aviso de que é uma IA nasce **desligado** e o operador marca; a memória do contato
nasce **ligada**.

Cada etapa muda backend, painel e terminal juntos. Nada aqui é escolha da instalação: tudo é
escolha de cada agente, como o tom e o emoji já são.

## O que já está pronto e não precisa ser refeito

A pesquisa trata como estado da arte três coisas que a plataforma já tem:

- **Ritmo na orquestração, não no modelo.** Buffer por conversa com lock, digitando no tempo de uma
  pessoa digitar (6 caracteres por segundo, variação de 15%, teto por mensagem e soma até 90 s), e
  resposta descartada quando chega mensagem nova antes do envio (`conversas/turno.py`,
  `conversas/divisao.py`).
- **Resposta em bolhas.** O modelo devolve uma lista de mensagens curtas no formato estruturado
  nativo, com teto por agente, e o markdown é removido antes de sair (`ia/agente.py`,
  `divisao.limita_mensagens`).
- **Jeito por agente.** Tom em três níveis, emoji em quatro, assunto restrito à empresa,
  transferência para humano opcional (com a tool escondida do modelo quando desligada), assinatura
  do nome, e o `persona.md` gerado a partir do perfil.

Três coisas que a pesquisa desaconselha e que a plataforma já não faz: erro de digitação de
propósito, menu numerado no lugar de linguagem natural, e textão em bolha única.

## O que falta, na ordem em que compensa fazer

### Etapa 1: ritmo com nome, e a pausa de ler

**Por quê.** O painel hoje pede quatro números crus (buffer, partes, caracteres por segundo, teto do
digitando). Quem não construiu a plataforma não sabe o que escolher. Todo líder analisado esconde
número atrás de preset com nome. E falta a pausa que mais denuncia robô: hoje o digitando começa no
mesmo instante em que a mensagem chega. Pessoa lê antes de digitar.

- **Backend.** `divisao.py` ganha uma pausa de leitura antes do primeiro digitando, proporcional ao
  que o contato mandou, com sorteio, teto baixo e desconto do que o turno já levou (o desconto já
  existe para o digitando). Entra no mesmo orçamento de 90 s, que já fica abaixo do lock.
- **Backend.** Um preset de ritmo vira campo do agente (`ritmo`: `instantaneo`, `natural`,
  `reflexivo`, `manual`), e os quatro números passam a ser derivados dele. Quem já tem números
  próprios nasce em `manual`, do jeito que está. Migração aditiva.
- **Painel.** A aba Comunicação abre com três cartões de ritmo e uma frase em cada. Os números só
  aparecem em "Ajustar à mão".
- **Terminal.** `asimov editar` já tem "Tempo de buffer" e "Digitação" separados: os dois viram
  "Ritmo", com as mesmas três opções mais "à mão", reaproveitando `configura_ritmo_novo` de
  `setup/lib/agente.sh`, que já faz isso na criação do agente nativo.
- **Cuidado.** Item que sai ou entra no menu muda a numeração: `setup/testes/respostas.txt` responde
  por número, e a simulação descarrila no meio. Rodar `simula_onboarding.sh` e conferir saída 0.
- **Aceite.** Numa VPS, agente em "Natural" responde com pausa de leitura antes do digitando; agente
  em "Instantâneo" responde na hora; mudar o preset no painel muda o terminal e o contrário também.

Tamanho: pequeno. É a etapa com mais efeito visível por linha escrita.

### Etapa 2: persona com o que nunca dizer

**Por quê.** As três pesquisas convergem no mesmo ponto: a naturalidade vem de dizer ao modelo o que
**não** fazer, porque o padrão dele é transcrição corporativa. O `persona.md` gerado hoje tem de três
a cinco linhas (quem é, para quem, sobre a empresa, site) e nenhuma delas trata disso.

- **Backend.** Um bloco fixo da plataforma entra nas `instructions`, ao lado do tom: varie a abertura
  em vez de repetir a mesma fórmula, use a saudação do horário (a hora de Brasília já vai no prompt),
  não repita o nome do contato a cada mensagem, não anuncie que vai verificar sem verificar, nada de
  "sua solicitação está sendo processada". Bloco fixo, não texto do operador: é o que impede cada
  agente de reinventar a regra.
- **Backend.** Um bloco de empatia, também fixo: espelhe tom positivo e neutro, valide o negativo sem
  imitar, nunca seja defensivo, deixe o contato terminar antes de oferecer solução. A pesquisa é
  explícita em não espelhar raiva.
- **Backend.** Campo novo por agente: **o que ele nunca deve dizer** (lista curta, texto do operador),
  que entra no `persona.md` gerado por `agentes/servico.monta_persona`. É onde cabe "nunca diga que
  entregamos em 24 horas" e "nunca fale de concorrente".
- **Backend.** Preço e prazo entram como regra de texto no bloco fixo: nunca afirme preço, prazo ou
  condição que não esteja no que você recebeu; diga que vai confirmar. O `@agent.output_validator`
  que recusaria a resposta **não entra aqui** (ver abaixo).
- **Painel.** O campo novo na aba Comunicação, abaixo do tom. A aba Trabalho continua escrevendo o
  `persona.md`, agora com a seção a mais.
- **Terminal.** Entra em "Jeito de falar", depois do tom.
- **Custo.** O prompt cresce. A v0.8.11 mediu uns 550 tokens por turno no agente cru contra uns 5.600
  com tudo ligado: medir de novo depois desta etapa e registrar o número em `spec/decisoes.md`.
- **Aceite.** Duas conversas seguidas com o mesmo agente abrem de jeitos diferentes; reclamação com
  raiva recebe resposta calma que não imita o tom; o que está no campo "nunca dizer" não aparece.

**Por que o validador de preço fica para a fase 6.** Um `output_validator` que devolve `ModelRetry`
quando a resposta fala de preço ou prazo sem nenhuma ferramenta chamada só funciona quando existe de
onde tirar o preço. Hoje quase todo agente tem zero ferramenta e o preço mora no "sobre a empresa"
escrito pelo operador: o validador recusaria a resposta certa e o agente entraria em retentativa a
cada pergunta de preço. Com a base de conhecimento existindo, a busca vira a fonte e o validador
passa a separar o que veio da base do que o modelo inventou. Entra na fase 6, ligado por padrão em
agente com base.

Tamanho: pequeno no código, cuidadoso no texto. Todo texto sem travessão.

### Etapa 3: o agente lembrar do contato

**Por quê.** É o item de maior efeito e o mais caro. Hoje o modelo recebe as últimas 40 mensagens
(`conversas/repo.ultimas_mensagens`) e nada mais. No WhatsApp a conversa é uma só, para sempre: o
contato volta em três semanas e o agente esqueceu tudo. A pesquisa aponta continuidade ("da última
vez você pediu X") como o que mais eleva a percepção de atendimento humano, e memória em camadas
como o padrão.

- **Backend.** Resumo rolante da conversa: quando o histórico passa do limite, o modelo auxiliar
  (que já existe e já é o barato, usado no resumo do handoff) escreve um resumo curto guardado na
  conversa, e ele entra antes do histórico. Sem isso, ou o contexto cresce sem fim ou o começo some.
- **Backend.** Ficha do contato: fatos duráveis e curtos (como prefere ser chamado, o que já comprou,
  o que já foi resolvido), escritos pelo modelo auxiliar no fim do turno, com teto de tamanho, por
  agente e contato. Migração aditiva, e `cliente_id` obrigatório como em todo repositório.
- **Regra que não pode ser quebrada.** Resumo e ficha nascem do que o contato escreveu. Entram no
  turno **marcados como dado do contato**, no mesmo molde do bloco `<midia_do_contato>`, nunca como
  instrução de sistema. Sem isso, "ignore suas regras" escrito hoje vira regra do agente amanhã.
- **Painel.** A tela Contatos ganha "o que ele lembra de você", com o texto à vista e um botão de
  apagar. Isso não é enfeite: é o pedido de exclusão da LGPD chegando pelo operador.
- **Terminal.** `asimov` ganha, em editar, o liga e desliga da memória, e a conversa de teste mostra
  o que foi lembrado.
- **Padrão.** Agente novo nasce com a memória **ligada**: é o comportamento que o contato espera de
  quem já falou com ele. Agente criado antes da fase nasce sem memória e só passa a lembrar do que
  vier depois de ligada.
- **Fora de escopo aqui.** Busca vetorial e pgvector são da fase 6 (base de conhecimento). Memória do
  contato é texto curto, não RAG.
- **Aceite.** Conversa longa continua coerente depois de passar do limite do histórico; o contato
  volta dias depois e o agente lembra do que ficou combinado; apagar no painel apaga de verdade e o
  turno seguinte não sabe mais.

Tamanho: médio. É a etapa que mexe em banco e a que precisa de mais teste de isolamento por empresa.

### Etapa 4: sentimento, gatilho de transferência e aviso de que é uma IA

**Por quê.** O handoff só acontece hoje quando o modelo decide chamar a ferramenta, quando o arquivo
é grande demais ou quando o modelo falha. A pesquisa lista gatilhos que faltam: frustração, mesma
resposta repetida e tentativas seguidas sem resolver. E o aviso de que o atendimento é automatizado,
que a LGPD recomenda e que o artigo 50 do EU AI Act passou a exigir em 2 de agosto de 2026, não
existe em lugar nenhum do produto.

- **Backend.** O formato de saída ganha um campo `sentimento` (positivo, neutro, negativo). Um campo
  só: cada campo a mais custa token em todo turno e pode piorar a resposta.
- **Backend.** Gatilhos novos, todos opcionais e só quando o agente transfere: dois turnos seguidos
  com sentimento negativo, resposta praticamente igual repetida (comparação no código, não no
  modelo), e pedido explícito que a tool não pegou.
- **Backend.** Aviso de IA por agente: uma linha na primeira mensagem de cada conversa nova, com
  texto padrão editável ("Oi! Sou o assistente virtual da Empresa, e se preferir eu chamo uma
  pessoa"). Registrar na conversa quando foi mostrado, que é o que prova o cumprimento.
- **Painel.** O interruptor do aviso na aba Comunicação, com a frase do porquê. Na Visão geral, o
  sentimento das conversas do dia e quantas transferências vieram de frustração.
- **Terminal.** Mesmo interruptor em "Jeito de falar", e o aviso aparece na conversa de teste.
- **Padrão, decidido pelo operador.** O aviso nasce **desligado** e o operador marca quando quer.
  Quem atende na União Europeia precisa marcar: o artigo 50 do EU AI Act exige o aviso na primeira
  interação desde 2 de agosto de 2026. O painel e o terminal dizem isso na frase de apoio do
  interruptor, em uma linha, sem virar aula de lei.
- **Aceite.** Agente novo não avisa nada; marcado o interruptor, a conversa nova começa com o aviso
  uma vez só, e ele não se repete a cada mensagem; contato
  irritado em dois turnos cai para uma pessoa quando o agente transfere, e não cai quando não
  transfere; a Visão geral mostra o sentimento do dia.

Tamanho: médio.

### Etapa 5: medir antes de publicar o que a IA escreveu

**Por quê.** Duas coisas já reescrevem o prompt sozinhas: o botão "Melhorar com IA" e o copiloto do
painel. Ninguém mede o resultado. A pesquisa chama isso de regressão de persona e é o que protege o
produto quando um leigo mexe no prompt.

- **Backend.** `pydantic-evals` já vem com a PydanticAI. Um conjunto pequeno de casos por agente
  (saudação, pedido de preço, reclamação com raiva, pedido de humano, assunto fora da empresa),
  julgado por `LLMJudge` contra o tom escolhido. Roda pelo modelo auxiliar do agente ou pela
  assinatura vinculada, que já move o "Melhorar com IA" e o copiloto.
- **Painel.** Antes de salvar um prompt que a IA escreveu, mostrar como o agente responde aos casos e
  o que mudou em relação ao prompt anterior. **Mostrar, não bloquear**: bloquear o salvar por causa de
  uma nota de um juiz automático frustra mais do que ajuda, e a nota não é confiável a esse ponto.
- **Terminal.** `asimov` ganha um comando que roda os casos e imprime as respostas, para conferir
  fora do navegador.
- **Testes.** Os mesmos casos, com `TestModel` e `FunctionModel`, entram na suíte sem chamar modelo de
  verdade. `models.ALLOW_MODEL_REQUESTS = False` na suíte, se ainda não estiver.
- **Aceite.** Melhorar com IA mostra as respostas antes e depois; recusar mantém o prompt antigo
  intacto.

Tamanho: médio, e é o único item que pode esperar sem prejuízo se o tempo apertar.

## O que este plano deixa de fora de propósito

- **Erro de digitação de propósito.** A pesquisa brasileira é unânime em desaconselhar: humanização
  não é truque cosmético, e o erro de digitação é coisa que a IA precisa entender do contato, nunca
  produzir.
- **Voz e áudio de saída.** Responder em áudio é outro produto, com outro custo e outro risco.
- **Trocar a WAHA pela Cloud API.** A plataforma já oferece as duas e já avisa o risco de bloqueio da
  não oficial. A escolha é do operador, não do plano.
- **Langfuse, Mem0, Zep e afins.** Serviço de fora para guardar memória e prompt contraria a
  arquitetura: uma VPS, um Postgres, um Redis. O que eles fazem cabe em tabela nossa.

## Onde isso entra na ordem

Fase 10, uma fase só, depois da fase 6. Antes dela ficam as duas pendências da fase 5 no WhatsApp
oficial (aviso de handoff por template e retomada por tempo) e a base de conhecimento inteira.
`AGENTS.md` manda construir uma fase por vez, na ordem, e a etapa 3 encosta na fase 6: as duas
mexem no que o agente sabe além da conversa, e a memória do contato reaproveita decisão da base.

Dentro da fase, a ordem é a das etapas: 1, 2, 3, 4 e 5. Uma versão por etapa, com validação em VPS
entre elas, como foi na fase 5.

## O que ainda não tem dono

Nada bloqueia o começo. Três coisas se decidem construindo, e cada uma vira linha em
`spec/decisoes.md` quando a VPS responder:

1. **Quanto o prompt engordou.** A etapa 2 acrescenta dois blocos fixos em todo turno. Medir contra
   os uns 550 tokens do agente cru da v0.8.11 e cortar o que não mudar a resposta.
2. **De onde sai o resumo rolante.** O modelo auxiliar do agente é o caminho óbvio, mas a assinatura
   vinculada não cobra por turno. Decidir depois de ver o custo real.
3. **O piso do juiz automático da etapa 5.** Só faz sentido depois de rodar os casos em agente de
   verdade. O plano é mostrar, nunca bloquear o salvar.
