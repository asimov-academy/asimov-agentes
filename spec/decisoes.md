# Decisões

Log de mudanças na spec. Cada entrada: data, o que mudou, por quê e quais arquivos de `spec/` foram atualizados. Entrada mais nova no topo.

## 2026-09-17: Áudio não era baixado da WAHA (v0.11.2)

- **Achado no teste de ponta a ponta**: o agente respondeu texto, mas o áudio virou `midia_download_falhou` e o contato recebeu o pedido para escrever. Causa: quando o QR code em texto entrou (v0.9.0), o `Accept: application/json` foi para o cabeçalho compartilhado das chamadas à WAHA, e ele acompanhava também o download do arquivo, que é binário.
- **Cabeçalhos separados**: `cabecalho()` só com a chave, para baixar arquivo; `cabecalho_json()` para a API, onde o `Accept` é justamente o que faz o QR code vir em texto. Teste de regressão nos dois.
- **Erro de download agora diz o status HTTP** (`a WAHA recusou o arquivo: HTTP 406`), que é o que faltava para achar isso em minutos em vez de por eliminação.
- **`hasMedia` deixou de ser exigido** para reconhecer o anexo: o que vale é a URL do arquivo. `hasMedia` nem sempre vem, e `hasMedia` sem URL é arquivo que a WAHA não baixou.

## 2026-09-17: Número escondido atrás de @lid barrava quem podia falar (v0.11.1)

- **Achado no primeiro teste de ponta a ponta**: o agente não respondeu a um número liberado na lista. O log mostrou `contato fora da lista do agente`, e o log da WAHA mostrou a razão: o WhatsApp entrega a conversa endereçada por `@lid` (id oculto), não pelo telefone. A comparação não tinha como bater.
- **O telefone de verdade vem resolvido pela WAHA** (2026.8.1+) em `pn` ou, no GOWS, em `_data.Info.SenderAlt`; em grupo, no participante. `telefone_do_contato` procura nesses campos e guarda o número no Contato; a conversa continua endereçada pelo `@lid`, que é por onde se responde. `@lid` nunca é lido como telefone: os dígitos dele não são o número de ninguém.
- **Nono dígito**: a comparação passou a aceitar o mesmo celular com e sem o 9 (`555186389892` e `5551986389892`), que é como o mesmo número aparece conforme a idade do cadastro. DDDs diferentes continuam diferentes.
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
