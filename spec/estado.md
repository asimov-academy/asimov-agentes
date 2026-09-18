# Estado do projeto

Atualize ao fim de cada fase ou versão publicada. Última atualização: 2026-09-18.

## Auditoria local

Auditoria de 2026-09-18: [relatório e plano de correção](../docs/auditoria-2026-09-18.md), com inventário, 22 achados priorizados e oito reproduções executáveis. Foram verificados os 266 testes e as 13 migrações da base publicada. O painel que surgiu em trabalho concorrente recebeu revisão parcial separada; esses resultados não validam suas alterações. Não muda a fase nem a versão publicada.

**Os seis P1 foram corrigidos** (spec/decisoes.md, 2026-09-18): reentrega recupera turno perdido (A01), envio que não saiu não conta como respondido (A02), prazo do token de buffer não descarta resposta (A03), humano que assume cala o agente na hora (A04), prompt não passa de uma empresa para outra (A05) e o lock passa a durar mais que o job (A06). Viraram 16 regressões em `backend/testes/test_auditoria_p1.py`; a suíte está em 311 testes. **Nada disso rodou em VPS**: precisa de validação real antes de virar versão. Seguem abertos os 14 P2 e 2 P3, com três sondas em `backend/testes/auditoria_2026_09_18.py`.

## Versão publicada

- `v0.24.0` em `asimov-academy/asimov-agentes` (público): **onboarding do agente refeito na ordem que o operador desenhou**: nome, objetivo, empresa (com site), o que a empresa faz e os ajustes. Foram oito passos para cinco. O canal saiu da criação: todo agente nasce respondendo no painel e no terminal, e conectar a um WhatsApp ou Chatwoot virou um passo depois, na ficha. O passo do "sobre" ganhou o botão **Melhorar com IA**, que pede à IA da instalação para reescrever o texto do operador. A prévia de conversa de mentira saiu, e o fim virou três caminhos, com conversar em primeiro.
- `v0.23.1`: cartão de canal mais visual e com menos texto (logo num quadrado, uma frase curta e o aviso como ícone que abre no hover, pelo `Dica`), os dois WhatsApp com o nome técnico ("WhatsApp Cloud API" e "WhatsApp WAHA") e o logo do Chatwoot na forma da marca.
- `v0.23.0`: **funil de oportunidades, com kanban e etiquetas.** Módulo `oportunidades/` com quatro tabelas (migração `0019`, aditiva): colunas do operador, cartões e etiquetas, tudo por empresa. Arrastar é o arrasto nativo do navegador, sem biblioteca. A primeira visita cria o funil padrão, coluna com cartão não some sem aviso e cor de etiqueta é nome de token da paleta. Doze testes novos, três deles sobre isolamento entre empresas.
- `v0.22.0`: **espaço de trabalho, perfil do operador e dados do negócio** em Configurações (tabela `espaco_trabalho` e duas colunas novas em `usuario_painel`, migração `0018`, aditiva). O nome e a sigla trocam o que o menu mostra. Junto: a tela de Canais ganhou o catálogo das integrações, que faltava; a Visão geral passou a usar o mesmo cabeçalho das outras telas; o ponto de situação subiu para a marca, com um formato só nos quatro estados ("0 falhas · 0 paradas" no lugar de "tudo no ar").
- `v0.21.5`: o X do popup do agente não fechava. Ele chamava `window.confirm`, e onde o navegador suprime a caixa nativa ela devolve "não" sem aparecer, deixando o botão morto. A pergunta saiu (o rascunho é gravado a cada mudança e o popup reabre com ele) e um teste passou a recusar `confirm`, `alert` e `prompt` no painel.
- `v0.21.4`: recolhido, o topo do menu ficava com a marca e o botão de recolher espremidos lado a lado e fora do eixo dos ícones. Sobrou a marca, centrada no mesmo eixo, e o recolher virou um botão redondo na borda do menu, que não disputa largura em nenhum dos dois estados.
- `v0.21.3`: Configurações em um cartão só (eram dois, e o da direita ficava metade vazio), sem as duas linhas que não diziam nada. No menu recolhido, o vão sem explicação onde ficavam os títulos dos grupos virou uma linha fina, e o bloco da conta virou só o avatar em vez de uma caixa larga com um ícone no meio.
- `v0.21.2`: tela **Configurações** (conta, instalação e as chaves de IA, que só existiam dentro da ficha de um agente), os três números da Visão geral viraram cartões de indicador no formato comum de painel, o recolher subiu para o topo do menu e o rodapé virou a área da conta, com avatar e endereço. O vazio da conversa deixou de ser um tracejado dentro de um cartão.
- `v0.21.1`: título de seção compacto num `Cabecalho` compartilhado (era `text-5xl` com subtítulo embaixo e comia um terço da tela), listagem distribuindo informação pela largura (canal, empresa e modelo em Agentes; situação na coluna do meio em Canais) e logo das integrações na paleta do painel, não na cor da marca.
- `v0.21.0`: **o painel ganha cara própria e a copy sai do jargão.** Canto arredondado em toda peça, Inter na estrutura (a mono ficou só para dado técnico), logo de WhatsApp, Chatwoot, Meta e terminal nas integrações, menu lateral em dois grupos com o recolher, o sair e a situação da instalação, e paleta padronizada com as três cores de marca como token. Na copy, as palavras internas saíram da tela (turno virou resposta, webhook virou endereço do canal, "o backend" sumiu) e a verbosidade caiu: no terminal, os blocos de três ou mais linhas de explicação antes de uma pergunta foram de 17 para 12, e o pior deles, com 18 linhas antes do primeiro sim, virou três. O painel passou a avisar o que só o terminal contava: a API não oficial pode ter o número bloqueado e a Meta cobra por mensagem. As telas de entrar e de primeiro acesso seguiram junto, e o subtítulo que parecia um campo vazio virou texto. **Nada validado em VPS.**
- `v0.20.4`: auditoria de copy de todo o produto ([relatório](../docs/auditoria-copy-2026-09-18.md)). Nove correções: dois celulares e um id de contato de uma VPS de teste saíram do repositório público, o aviso da API não oficial dizia que o WhatsApp oficial ainda não existia, duas datas de outubro de 2026 estavam escritas como passado, o aviso de transferência na WAHA mandava reagir com joinha a quem não consegue, o painel prometia uma tela de escolher o destino que não existe, o erro público devolvia o caminho dentro do contêiner, nome de ícone inválido compilava, o README descrevia o setup anterior à v0.20.0 e "risco de bloqueio: nenhum" virou o que é. O resto do relatório (jargão, verbosidade e vocabulário) ficou para decisão.
- `v0.20.3`: contraste do texto do painel na régua da WCAG AA. `dim` e `muted` davam 1,9:1 e 2,4:1 sobre o preto, e rótulo, placeholder e texto de apoio sumiam; foram para 5,5:1 e 7,5:1, com um teste que trava o piso.
- `v0.20.2`: a tela "Ligar o painel" ficou com uma linha de dica só, no molde da pergunta do domínio.
- `v0.20.1`: a tela do DNS do `bot` abre com a mesma frase da oferta do painel (o subdomínio inteiro e o IP da VPS), antes da tabela do registro.
- `v0.20.0`: **a IA vira escolha de cada agente e a instalação fica só com o essencial.** A tela "Modelos de IA" saiu do setup: criar agente, no terminal ou no painel (passo novo "IA" no onboarding), pergunta provedor e modelo, e a chave do provedor é pedida uma vez, testada pela API e guardada cifrada no banco (migração `0017`, aditiva; `.env` antigo segue valendo). O painel passa a ser oferecido antes do primeiro agente, que pode nascer por lá; o código de primeiro acesso não some mais (pausa depois de mostrar, e volta no resumo final enquanto não houver conta); a oferta diz o IP do DNS; o domínio aceita ser colado de qualquer jeito; textos sem "Chatwoot" e sem "webhook"; cor principal do painel e do design system no ciano do CLI. **Nada validado em VPS.**
- `v0.19.0`: **painel web do operador completo**, em `app.<dominio>`. Visão geral, agentes, canais, chat e contatos, com todo onboarding e toda configuração de agente num popup grande com o fundo embaçado. O onboarding tem sete passos com prévia de como o agente vai falar e termina numa conversa de teste com ele. A instalação passa a oferecer o painel uma vez, em vez de só citar o comando no fim. Correções que apareceram rodando de verdade: a API do painel devolvia o detalhe cru da falha (que já veio com chave de API dentro), a folha de estilo do login ficava em cache para sempre, e `/painel/inicio` e `/painel/agentes` eram um segundo painel. Migração `0016`, aditiva. **Nada validado em VPS.**
- `v0.18.0`: correções dos seis achados P1 da auditoria, mais os P2 e P3, e a parte 8.1 do painel (acesso, sessão, primeiro acesso com código do terminal e `asimov painel`).
- `v0.17.0` em `asimov-academy/asimov-agentes` (público): nível de emoji por agente (nenhum, pouco, médio ou muito), perguntado na criação em todo canal e editável no menu. Agente criado antes fica sem regra, como era.
- `v0.16.3`: quando o token não enxerga nenhuma conta de WhatsApp Business, a mensagem passa a dizer a causa provável (token gerado antes de a conta ser atribuída ao usuário do sistema) e a saída (gerar o token de novo).
- `v0.16.2`: o ícone do app também vem por URL (`/icone-app.png`, para baixar no navegador) e entrou `asimov diagnostico`, que diz a versão instalada e o código HTTP de cada endereço que precisa responder.
- `v0.16.1`: uma política de privacidade por agente (`/privacidade/<empresa>/<agente>`, mostrada pronta no setup), e o Caddy passou a recarregar de verdade depois de atualizar, que era por que a URL respondia 404.
- `v0.16.0`: a instalação serve a política de privacidade que a Meta exige para publicar o app (`https://bot.<dominio>/privacidade`, e por empresa com o slug), e o projeto traz um ícone quadrado pronto para o app. Erro de app trocado no token virou mensagem que diz o que fazer.
- `v0.15.2` (com `docs/whatsapp-oficial.md` corrigido depois: o token do agente precisa de duas permissões, `whatsapp_business_messaging` e `whatsapp_business_management`; `business_management` não aparece em app do caso de uso do WhatsApp e não é necessária): o setup não pede mais o ID da conta de WhatsApp Business: com app, token e chave secreta ele pergunta à Meta quais contas o token alcança e lista para escolher. O ID era o dado mais escondido do painel novo.
- `v0.15.1`: `docs/whatsapp-oficial.md` refeito com o painel novo da Meta ("Produtos" virou "Casos de uso", com as três etapas guiadas), a cobrança por mensagem de serviço que começou em 1º de outubro de 2026 (e que exige forma de pagamento para o agente conseguir responder) e a política de IA de propósito geral de janeiro de 2026.
- `v0.15.0`: **WhatsApp oficial (Cloud API da Meta)**, terceira parte da fase 5. Cada agente tem o próprio endereço de webhook, apontado no número pela API; o aviso de handoff sai em texto livre ou pelo template aprovado, e a conversa volta com 👍 no aviso, `/retomar` ou o prazo do agente.
- `v0.14.2`: o texto das mensagens saiu do log (conversa pessoal de quem emprestou o número ao agente passava por lá) e mexer no contêiner da WAHA deixou de disparar alarme de número fora do ar.
- `v0.14.1`: a transcrição leva o idioma configurado (`IDIOMA_AUDIO`, padrão `pt`), depois de um "Boa noite" voltar em russo.
- `v0.14.0`: `/retomar` sem código devolve a conversa em que foi escrito, ou a única em atendimento; com várias, o destino recebe a lista para escolher.
- `v0.13.5`: `/retomar <código>` escrito do número do agente vale em qualquer conversa, inclusive na do contato.
- `v0.13.4`: `/retomar` vale também escrito do aparelho do agente no chat do handoff, e nenhuma resposta do webhook sai mais sem log.
- `v0.13.3`: o log do webhook passa a dizer de qual conversa é cada mensagem aceita ou ignorada.
- `v0.13.2`: o aviso de handoff passa a chamar o contato por nome e telefone de verdade (antes mostrava o id oculto como se fosse número), e o `/retomar` funciona quando o destino escreve por trás de um `@lid`.
- `v0.13.1`: o arquivo de áudio, imagem e documento sai do disco na limpeza diária (um a dois dias depois de lido); o texto lido dele fica.
- `v0.12.3`: áudio, imagem e PDF voltam a ser lidos (o arquivo era anunciado em `localhost`, que no contêiner do worker é o próprio worker), e pedir QR code novo deixou de disparar alarme de número fora do ar.
- `v0.12.2`: o aparelho conectado aparece no celular como `Agente (Empresa)`, em vez de "Ubuntu Firefox".
- `v0.12.1`: o id do número do handoff passa a ser o que o próprio WhatsApp devolve (nono dígito, `@lid`), conferido na escolha e corrigido no envio.
- `v0.12.0`: número desconectado do WhatsApp vira falha visível e aviso no menu, pelo evento da WAHA e por uma ronda de dez em dez minutos.
- `v0.11.2`: áudio e imagem voltam a ser baixados da WAHA (o `Accept: application/json` do QR code tinha ido parar no download do arquivo).
- `v0.11.1`: contato que chega por `@lid` (número escondido pelo WhatsApp) passa a ser reconhecido pelo telefone de verdade, o nono dígito deixou de separar o mesmo número, e contato barrado pela lista vira falha visível.
- `v0.11.0`: no Chatwoot, atendente que responde fica com a conversa (aberta e atribuída a ele) e o agente volta sozinho no prazo do onboarding, com a conversa de volta para Pendente e sem atribuição.
- `v0.10.0`: no WhatsApp, responder pelo aparelho cala o agente na hora (handoff sem IA e sem aviso, com o prazo do agente) e reagir com 👍 na conversa o traz de volta. O que a equipe respondeu entra na memória do agente marcado como fala de atendente, em todo canal que tem atendente.
- `v0.9.3`: destino do handoff da WAHA em dois passos (número ou grupo), com busca pelo nome do grupo.
- `v0.9.2`: o agente pode atender só os números listados (`contatos_permitidos`), escolhido na criação e em Editar agente; grupos continuam sempre ignorados.
- `v0.9.1`: aviso de API não oficial com confirmação antes de parear, correção do fluxo que voltava ao menu quando o systemd recusava o timer, e nomes dos passos da instalação do WhatsApp.
- `v0.9.0`: **WhatsApp direto pela WAHA**, segunda parte da fase 5. A WAHA sobe sob demanda (perfil do Compose, no primeiro agente WhatsApp), o número é pareado por QR code no terminal, o handoff avisa um número ou grupo com resumo e código, e a conversa volta com `/retomar <código>` ou sozinha pelo prazo do agente.
- `v0.8.11`: agente nativo, primeira parte da fase 5, com ajustes na criação, conexão posterior a um canal, feedback de etapa e turno na conversa, busca na web com instrução de uso e raciocínio baixo, handoff no histórico do modelo, teto de chamadas por turno, calculadora completa no formato brasileiro, uma ferramenta por arquivo, resposta no formato estruturado nativo, mensagem sem markdown, data de Brasília no turno e agente que nasce cru (sem ferramentas marcadas e prompt de uma linha).
- Instalação: `bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)`
- Atualizar uma VPS instalada: `asimov atualizar` (ou `ASIMOV_ATUALIZAR=1` antes do comando de instalação).
- Verificação local na última revisão: 420 testes do backend passando, 28 do painel no navegador, `shellcheck` sem erro, `simula_onboarding.sh` completo (inclui o fluxo do WhatsApp), conversa no terminal testada num pty com bash 5.

## Fases

| Fase | Situação |
|---|---|
| 1. Setup de ponta a ponta com agente de texto no Chatwoot | Concluída e validada em VPS real |
| 2. Áudio, imagem e documento | Concluída e validada em VPS real (v0.3.2) |
| 3. Handoff no Chatwoot | Concluída e validada em VPS real (v0.4.1) |
| 4. Menu do operador | Concluída e validada em VPS real (confirmado pelo operador em 2026-09-17) |
| 5. WhatsApp direto (oficial e WAHA) e agente nativo | **Em construção**, uma versão por parte. Parte 1 (agente nativo) validada em VPS real (v0.8.11). **Parte 2 (WAHA) validada em VPS real em 2026-09-18 (v0.14.2)**: instalação, pareamento, texto, áudio, imagem, PDF, lista de quem atende, handoff com aviso e código, `/retomar`, joinha, pausa por resposta pelo aparelho, retomada por tempo e remoção tirando o aparelho do celular. **WhatsApp oficial (v0.15.0 a v0.17.0), em validação na VPS**: número de produção respondendo texto e áudio, com o digitando da Cloud API convincente (confirmado pelo operador em 2026-09-18). Faltam handoff com aviso por template e retomada por tempo. Ver "Para a fase 5" abaixo |
| 6. Base de conhecimento | Não iniciada |
| 7. Polimento e distribuição | Parcial: repositório público, README, licença MIT, `install.sh` pelo GitHub; faltam backup, limpeza de mídia de 90 dias e domínio próprio do setup |
| 8. Painel web do operador | **Construída inteira e na `main`, nada validado em VPS.** Parte 8.1 (acesso, sessão e as duas telas de login em Jinja2) e as **onze etapas** do front em `frontend/` (React, Vite, Tailwind): visão geral, agentes com onboarding e ficha em popup, canais, chat, contatos e polimento. Plano e decisões em `spec/frontend.md`. Fora da versão publicada até existir uma tag |

## Ambiente do operador

- VPS Hostinger com Ubuntu 24.04, acessada pelo terminal no navegador do painel da Hostinger. Esse terminal manda Enter como `\r\n` (resolvido na v0.6.3 com `descarta_pendentes`).
- Chatwoot próprio do operador (a URL nunca entra no repositório), com caixas de WhatsApp e Instagram.
- Modo revenda, com mais de uma empresa.

## O que existe hoje

### Setup e comando `asimov`

- Instalação guiada: modo de uso, domínio (colado de qualquer jeito), e-mail do SSL, assistente de código, DNS, instalação com retomada, oferta do painel, primeiro agente (no painel ou no terminal) e resumo. Nada de IA na instalação desde a v0.20.0.
- IA por agente: toda criação pergunta provedor (openai, anthropic, gemini, groq) e modelo da resposta; a chave do provedor é pedida uma vez e fica cifrada no banco (`/admin/ia/chaves`, `ia/chaves.py`). Resumo, visão e áudio nascem no mesmo provedor e mudam em Editar agente > Modelos.
- Setup rodado de novo numa instalação concluída pede o que faltar de versões novas, reconstrói se o código mudou, mostra o resumo e abre o menu. `asimov atualizar` para no resumo.
- Menu (`setup/lib/menu.sh`, `asimov` sem argumento): criar agente (começa pelo canal: Chatwoot, WhatsApp oficial, WhatsApp pela WAHA ou nativo), conversar com agente nativo (`setup/lib/conversa.sh`), listar, editar e remover agente, ver consumo e falhas (escolhe a empresa), token do Chatwoot (esquecer) e sair. Subcomandos: `novo-agente`, `conversar`, `agentes`, `editar`, `remover`, `consumo`, `handoff`, `diagnostico`, `atualizar`, `ajuda`.
- Editar agente: nome (renomeia o bot no Chatwoot também), buffer, mensagens por resposta, digitação, ferramentas (lista de marcar), emoji, modelos (inclui o do resumo do handoff) e, conforme o canal, destino do handoff, "Conectar a um canal" (nativo) ou "WhatsApp" (WAHA: número pareado, destino e horas até voltar sozinho; oficial: número na Meta, destino com template, horas e quem atende).
- WhatsApp oficial (`setup/lib/whatsapp.sh`, v0.15.0): pede o ID do app, o token permanente e a chave secreta, descobre as contas de WhatsApp Business que o token alcança, lista os números da conta e os templates aprovados, e cria o agente já com o webhook apontado no número. Item "WhatsApp" em Editar agente: confere o número na Meta, troca destino e template do aviso, horas até voltar sozinho, quem o agente atende e refaz o webhook na Meta. Nada sobe na VPS por causa deste canal.
- WhatsApp pela WAHA (`setup/lib/waha.sh`, v0.9.0): o contêiner sobe na primeira vez que o operador escolhe o canal (`garante_waha`), o QR code é desenhado com `qrencode` até o número parear e o destino do handoff é escolhido depois (número digitado ou grupo do próprio número). A imagem se atualiza sozinha: `asimov-waha.timer` (domingo de madrugada) roda `deploy/atualiza_waha.sh`, que volta para a versão anterior se algum número não reconectar em 2 minutos e deixa o aviso no menu. Item "WhatsApp (WAHA)" no menu: versão, última conferida, ligar ou desligar a automática e procurar versão nova agora.
- Tela: escolhas com setas e Enter (números como atalho), Sim/Não com setas, lista de marcar com Espaço, cada seção limpa a tela e redesenha o banner, Esc volta à tela anterior (cada ação do menu roda em `com_voltar`), pausa com Enter antes de o menu limpar o que precisa ser lido.
- Token de administrador do Chatwoot pedido uma vez por URL e guardado cifrado (`acessos/`); a API responde 428 quando falta ou foi recusado e o menu pergunta (`api_com_token` em `setup/lib/agente.sh`).

### Painel web do operador

Desligado por padrão. `asimov painel` liga, pede o DNS de `app.<dominio>` e mostra o código de uso
único do primeiro acesso.

- **Entrar e primeiro acesso**: Jinja2, com o design system (o `painel.css` é o único lugar do
  projeto com cor em hexadecimal). Senha em scrypt, sessão no Redis, cookie `HttpOnly`, `Secure` e
  `SameSite=Strict`, origem conferida e freio de tentativa por IP. Uma conta só.
- **O painel em si** é o front em `frontend/`, servido em `/painel/app`: visão geral (veredito,
  handoffs esperando, ritmo, custo, resolução, quem respondeu, onde travou), agentes, canais, chat e
  contatos. Menu lateral fixo, gaveta no celular.
- **Agente sempre em popup**, com o fundo embaçado: criar em sete passos com prévia viva do jeito de
  falar, terminando na conversa de teste; e a ficha em seis abas (perfil, comunicação, trabalho,
  ferramentas, configurações, conversar), cada seção com o próprio salvar.
- **Contrato** em `/painel/api/*`, com sessão por cookie e `X-Painel-CSRF` em toda escrita. Chama os
  mesmos `servico.py` do menu. Credencial sai mascarada, falha sai como resumo curto, e o
  `cliente_id` nunca vem do corpo.
- **Nada de CDN**: front, CSS e as duas fontes saem da VPS.

### Plataforma

- Canal WhatsApp oficial (`canais/whatsapp/`, v0.15.0): um número da Cloud API por agente, com a conta de WhatsApp Business, o ID do app, o token permanente e o segredo do app guardados cifrados. A criação liga os webhooks do app (campo `messages`, com o token do app), inscreve o app nos webhooks da conta e aponta o webhook daquele número para o endereço do agente (webhook override); a verificação da Meta é respondida pelo token da URL e o corpo é conferido por `X-Hub-Signature-256`. Webhook de outro número e recibo de entrega são ignorados. Digitando e leitura vão juntos, presos à mensagem que chegou. Handoff: pausa pelo status da conversa, aviso ao número do destino em texto livre e, fora da janela de 24 horas, pelo template aprovado (contato, resumo e código); volta com 👍 no aviso, `/retomar` do destino ou o prazo do agente. Remover o agente devolve o webhook do número para a URL do app.
- Canal WAHA (`canais/waha/`, v0.9.0): uma sessão por agente com webhook interno assinado (HMAC SHA-512), QR code lido pelo setup (`GET .../waha`, `POST .../waha/reiniciar`, `GET .../waha/grupos`), envio, digitando e marcar como lida, download de mídia com a chave da instalação, remoção com logout. Ignora grupos (menos o do handoff) e sessão de outro agente; o que sai do número é lido pelo `source` (`api` é o agente, `app` é gente no aparelho, que pausa o agente). Sessão que sai do ar (`session.status` e ronda `confere_whatsapp`) vira falha e aviso no menu. Handoff: pausa pelo status da conversa, aviso ao número ou grupo com resumo e código, `/retomar <código>` só do destino, job `retomada_automatica` no worker (cron de um minuto) e aviso de que o agente voltou.
- Conversa de teste no terminal para agente de qualquer canal (`Conversa.canal` nativo; `canal_da_conversa`). Agente nativo pode ser conectado depois a um canal externo (`POST .../canal`: Chatwoot ou WAHA).
- Canal nativo (`canais/nativo/`): sem conexão nem webhook; rotas `POST` e `GET .../terminal` em `canais/nativo/rotas.py`; envio, digitando e humano conduzindo no Redis (`memoria.py`); a leitura diz se o turno ainda está em andamento. Handoff mostra motivo, resumo e código no terminal e `/retomar` usa a retomada do operador.
- Canal Chatwoot (`canais/chatwoot/`): cria o Agent Bot e confere na caixa que ele ficou ligado; aceita evento de qualquer caixa em que o bot esteja ligado (a assinatura prova o bot).
- Turno (`conversas/turno.py`): buffer por conversa, lock de 240 s, mídia antes do modelo, resposta descartada se chegar mensagem nova antes do envio, digitando com o tempo de uma pessoa digitar (6 caracteres/s, variação de 15%, teto de 20 s por mensagem, soma até 90 s; editável por agente).
- Mídia: transcrição, visão e PDF com texto, cache por cliente e hash, limites de 20 MB e 5 minutos. O arquivo sai do disco na limpeza diária, um dia depois de lido (`limpar_midia`); o texto lido fica com a conversa.
- Handoff no Chatwoot: nota privada curta, atribuição, status aberto; retomada pelo status pendente ou pelo prazo do agente (que devolve para pendente e desatribui); atendente que responde por lá pausa o agente e fica com a conversa; falha do modelo e arquivo grande também transferem. Retomada pelo operador existe na API (`POST .../conversas/{id}/retomar`), sem opção no menu.
- Ferramentas por agente, uma por arquivo em `ia/ferramentas/` (ficha em `base.py`, catálogo em `registro.py`): calculadora (`ia/ferramentas/calculadora.py`, sem `eval`, formato brasileiro, funções de porcentagem, parcela, juros e datas) e busca na web (`WebSearch` da PydanticAI: nativa do provedor, DuckDuckGo quando o modelo não tem), escolhidas na criação (nenhuma por padrão desde a v0.8.11). OpenAI pela `OpenAIResponsesModel`; Groq sem busca nativa fora dos modelos `compound`.
- Consumo por agente e empresa (`GET /admin/consumo`), falhas registradas, log `webhook_ignorado` com motivo em nível info.
- Exclusão lógica de agente (apaga o bot no Chatwoot, invalida o webhook, apaga credenciais, libera o slug) e de empresa sem agentes.
- Migrações até `0014` (canal da conversa; agente novo sem ferramentas; contatos permitidos; arquivo de mídia apagado; fim da coluna `handoff_template`, que virou parte do `handoff_destino`; nível de emoji; **perfil e assinatura do agente, que escrevem o `persona.md` pelo painel**).

## Pendências conhecidas

- Sessão órfã na WAHA: agente removido e recriado deixa a sessão antiga viva, que manda webhook com token que já não vale (`webhook_token_desconhecido`). Falta uma conferência de sessões no menu, que liste e deixe apagar.
- O número usado no teste é um celular de uso pessoal: como a sessão assina `message.any`, toda conversa particular passa pelo webhook (não é gravada, e desde a v0.14.2 o texto não entra no log). Em produção, chip só do agente.
- Da parte 1, não conferido na VPS depois das correções: contas pela calculadora nova (v0.8.7: ponto de milhar, porcentagem, parcela, datas), citação da busca sem markdown (v0.8.10) e `/retomar` no terminal. Cobertos por teste automatizado.
- Mídia (visão e PDF) na OpenAI Responses ainda não conferida na VPS.
- Uma mensagem digitada no terminal da VPS chegou como "Ol�a" (byte inválido antes do "a"). Suspeita: apagar uma letra acentuada; não reproduzido local com bash 5.
- `INSTRUCAO_DE_MIDIA` ajustada na v0.4.0 para o agente não citar a mecânica ("recebi a transcrição"): não conferido na VPS.
- Causa de o Chatwoot não ligar o bot: era o Enter duplo escolhendo a primeira caixa (v0.6.3). Se voltar a acontecer, a criação agora falha com mensagem clara.
- Retomada pelo operador sem opção no menu para o Chatwoot (falta listar conversas em handoff); no nativo, `/retomar` na conversa.
- Web fetch (ler link) oferecido como terceira ferramenta; o operador não decidiu.

## Para a fase 5

Critério de aceite e o que entra: spec/fases.md, Fase 5. Decisão e comparação de APIs: spec/decisoes.md (2026-09-17). Ordem: **nativo (feito, v0.8.0 a v0.8.11), WAHA (validada, v0.9.0 a v0.14.2), WhatsApp oficial (construído, v0.15.0)**, uma versão por parte, com validação na VPS entre elas.

Validado na VPS no WhatsApp oficial (2026-09-18): áudio entendido e digitando convincente, com o indicador da Cloud API preso à mensagem que chegou. Falta o handoff (aviso por template fora da janela de 24 h) e a retomada por tempo.

Validado na VPS na parte 1 (2026-09-17): conversa no terminal com ritmo rápido e etapas; nativo conectado ao Chatwoot com as conversas de teste separadas; handoff e devolução no Chatwoot; busca na web usada quando precisa (v0.8.5) e sem o erro de JSON (v0.8.9); data do dia respondida sem ferramenta (v0.8.10); agente novo cru, sem ferramentas e com prompt de uma linha, gastando uns 550 tokens por turno contra uns 5.600 com busca ligada (v0.8.11).

O que reaproveitar:
- WAHA e oficial entram também em "Conectar a um canal" (`conecta_canal` em `menu.sh`, hoje fixo no Chatwoot) e precisam de `externo = True`.
- Contrato do canal em `canais/base.py` (`pede_acesso_do_operador`, `descobrir`, `conectar`, `desconectar`, `renomear`, `verificar`, `interpretar`, `agente_pode_falar`, `digitando`, `enviar_texto`, `valida_destino_handoff`, `transferir`, `devolver_ao_agente`, `baixar_midia`, `retoma_por_tempo`, `acesso_do_operador`, `endereco`) e registro em `canais/registro.py`. O webhook genérico `POST /webhook/{canal}/{token}` já serve para a WAHA.
- `Handoff` já tem `codigo` e `retomar_em`; falta o job `retomada_automatica` no `worker.py` (hoje só `processar_turno`).
- No menu: `com_voltar`, `api_com_token`, `escolha`, `marca`, `pergunta_numero`, `pausa`. A escolha do canal está em `fluxo_novo_agente` (`agente.sh`): WAHA e oficial entram como opções novas ali; `escolhe_agente [canal]` filtra por canal; editar monta as opções por canal (`fluxo_editar_agente`).
- `le_tecla VAR segundos` devolve `nada` sem tecla no tempo: serve para desenhar o QR code e consultar o status da sessão enquanto espera.

WAHA (construída na v0.9.0; conferido na documentação em 2026-09-17):
- Imagem `devlikeapro/waha` com `WHATSAPP_DEFAULT_ENGINE=GOWS` (conferir a tag para amd64 e arm e fixar a versão). Variáveis: `WAHA_API_KEY` (gerada pelo setup no `.env`), `WAHA_DISABLE_DASHBOARD`, `WAHA_DISABLE_SWAGGER`, `WHATSAPP_DOWNLOAD_MEDIA`, `WHATSAPP_FILES_LIFETIME`. Header `X-Api-Key`. Volume para as sessões.
- Sessões: `POST /api/sessions` com `{"name", "config": {"webhooks": [{"url", "events", "hmac": {"key"}, "retries"}]}}`, `POST /api/sessions/{s}/start|stop|logout`, `DELETE /api/sessions/{s}`, `GET /api/sessions/{s}` (status `STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED`, `STOPPED`), `GET /api/{s}/auth/qr?format=raw` (texto para o `qrencode` desenhar no terminal), `POST /api/{s}/auth/request-code` com `phoneNumber` (código de pareamento), `GET /api/sessions/{s}/me`.
- Webhook: eventos `message` (só recebidas) e `session.status`; corpo com `event`, `session` e `payload` (`id`, `from`, `fromMe`, `to`, `body`, `hasMedia`, `media.url`, `media.mimetype`, `media.filename`, `participant`). Assinatura `X-Webhook-Hmac` = HMAC SHA-512 do corpo cru, `X-Webhook-Hmac-Algorithm: sha512`.
- Envio: `POST /api/sendText` com `session`, `chatId`, `text` (devolve `id`); `POST /api/startTyping` e `/api/stopTyping` com `session` e `chatId`; `POST /api/sendSeen`. `chatId`: `@c.us` (número), `@lid` (id oculto), `@g.us` (grupo).
- Webhook pela rede interna do Docker (`http://api:8000/webhook/waha/{token}`), sem passar pelo Caddy. Container subido pelo setup só no primeiro agente WAHA (perfil do Compose). Setup instala `qrencode`.

Para validar o WhatsApp oficial, o operador precisa ter na Meta: um app, uma conta de WhatsApp Business com um número, um token de acesso permanente (usuário do sistema), o segredo do app e um template de aviso de handoff aprovado, de categoria Utilidade, com três parâmetros. Texto sugerido (o setup mostra na tela):

```
O agente passou uma conversa para voce.

Contato: {{1}}
Resumo: {{2}}
Codigo: {{3}}

Responda /retomar neste chat quando terminar.
```

O setup não pede para colar URL nenhuma no painel da Meta: a criação do agente liga os webhooks do app, inscreve a conta e aponta o webhook no próprio número. Passo a passo com links, para o operador e para os alunos: `docs/whatsapp-oficial.md`.

## Fluxo de publicação combinado com o operador

1. Branch nova a partir de `main`.
2. Testes (`backend`), `shellcheck` e, se mexeu no setup, `setup/testes/simula_onboarding.sh`. Mudança em leitura de tecla: teste num pty com bash 5 (AGENTS.md, armadilhas).
3. Commit com autor `Vitor Paim <vitor.paim@asimov.academy>` via `git -c user.name=... -c user.email=...` (a máquina não tem identidade git global).
4. PR, merge com `--delete-branch` e tag `vX.Y.Z` quando muda o setup ou o backend (o operador autorizou fazer os três). Subir `VERSAO` em `setup/lib/base.sh` e o padrão em `setup/install.sh` antes da tag.
5. Dizer ao operador o comando de atualização da VPS (`asimov atualizar`).

## Nunca no repositório (é público)

Nome de cliente real, URL de Chatwoot de cliente, domínio ou IP da VPS de teste, tokens. Exemplos usam Loja Exemplo, agente Ana e `exemplo.com.br`.
