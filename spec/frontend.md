# Painel web: spec do front

O front do operador em `app.<dominio>`. Complementa spec/telas.md (que descreve as telas de
terminal) e o estudo em docs/painel-web.md. Leia antes de tocar em qualquer coisa dentro de
`frontend/` ou em `backend/app/painel/`.

Autorizado pelo operador em 2026-09-18. Registro em spec/decisoes.md.

## 1. O que é e o que não é

É o painel do **operador**: quem instalou a VPS administra empresas, agentes, canais, conversas e
consumo pelo navegador, no computador e no celular, sem SSH.

Não é: front do cliente final (cada empresa vendo os próprios agentes), não é painel de atendente
(isso é o Chatwoot) e não é administração de infraestrutura. Continua fora de escopo, como em
spec/visao.md.

Referência de organização das telas: o operador pediu a arquitetura de informação do GPT Maker
(menu lateral fixo, lista à direita, ficha do agente em abas). A aparência é a do design system em
`designsystem/`, não a do GPT Maker.

## 2. Decisões de base

**Stack.** React 19, TypeScript, Vite, Tailwind CSS 3 e React Router. Pasta `frontend/` na raiz.
Isto muda a regra antiga do `AGENTS.md` ("não existe `frontend/` na primeira versão").

**Onde o build mora.** O Vite gera `frontend/dist/`, copiado para dentro da imagem e servido pela
própria API em `/painel/app`. Nada de CDN: fonte, CSS e JavaScript saem da VPS.

**Como o build acontece.** A VPS já constrói a imagem do backend (`deploy/docker-compose.yml`, `build:
context`). Entra um estágio `node:22-alpine` no `backend/Dockerfile` que roda `npm ci && npm run build`
e copia o `dist` para o estágio de produção. O contexto do build passa a ser a raiz do repositório,
com `.dockerignore` para não mandar `.git`, `prompts/` e mídia para o daemon. Nenhum node na VPS,
nenhum artefato de build commitado.

**Autenticação.** Entrar, primeiro acesso e sair continuam como estão hoje: páginas Jinja2 em
`backend/app/painel/paginas/`, sessão no Redis, cookie `HttpOnly`, `Secure`, `SameSite=Lax`, freio
de tentativa e checagem de origem. Os 29 testes de acesso seguem valendo sem mudança. O front só
começa depois do login, e quem chega sem sessão é redirecionado para `/painel/entrar`.

**Como o front conversa com o backend.** Rotas novas em `/painel/api/*`, JSON, mesma sessão por
cookie. Toda escrita exige o cabeçalho `X-Painel-CSRF` com o token da sessão. `/admin` continua sem
sair da VPS e o front nunca tem a `CHAVE_API_ADMIN`.

**Camadas.** `rotas.py` do painel valida e chama os `servico.py` que já existem em `agentes/`,
`clientes/`, `consumo/`, `conversas/`, `canais/`. Nenhuma regra de negócio nasce no painel e nenhuma
nasce no front.

## 3. Design system

Fonte: `designsystem/`, projeto "Enterprise SaaS UI". Escuro, cantos retos, borda de 1 px, rótulo em
mono maiúsculo, acento ciano. Os valores entram no `tailwind.config.ts` como tokens e nunca são
escritos soltos no componente.

| Token | Valor | Uso |
|---|---|---|
| `void` | `#000000` | fundo da página |
| `surface` | `#0a0a0a` | fundo de cartão e de campo |
| `panel` | `#111111` | menu lateral e barra do topo |
| `border` | `#222222` | borda padrão |
| `dim` | `#8a8a8a` | texto de apoio, rótulo, placeholder, borda de controle desligado |
| `muted` | `#a3a3a3` | texto secundário |
| `text` | `#e5e5e5` | texto |
| `ciano` | `#29b8db` | acento, item ativo, foco, confirmação |
| `success` | `#00cc66` | situação boa |
| `warning` | `#ffaa00` | atenção |
| `danger` | `#ff453a` | erro e ação destrutiva |

Todo texto fica acima dos 4,5:1 da WCAG AA sobre os três fundos: `text` em 15:1, `muted` em 7,5:1 e
`dim` em 5,5:1. `dim` e `muted` nasceram em 1,9:1 e 2,4:1 e sumiam no preto.

Tipografia: Inter para texto, JetBrains Mono para rótulo, número, token e situação. As duas vêm dos
pacotes `@fontsource`, só no subconjunto latino, e entram no build: são servidas da VPS, nunca de CDN.

Os componentes não são inspirados no design system: são a forma dele. O que cada um copia, com a
seção de origem:

| Componente | O que o design system manda | Onde |
|---|---|---|
| `Botao` sólido | Fundo `texto` (quase branco) sobre preto, negrito, maiúsculo, espaçado. É o mais forte da tela | 5, 01 |
| `Botao` acento | Contorno `ciano/50`, texto ciano, preenche no hover. **O ciano cheio não é botão**: trocar isso apaga a hierarquia | 5, 01 |
| `Botao` fantasma | Contorno `texto/20`, fundo transparente, com os dois cantos marcados em SVG. É a assinatura do sistema | 5, 01 |
| `Campo` | **Só borda de baixo**, `dim` em repouso e `ciano` no foco, fundo `surface`, ícone à esquerda | 5, 02 |
| `Interruptor` | Retângulo de 48x24 com botão **quadrado** de 16px, `dim` desligado e `ciano` ligado com fundo `ciano/10`. Nada de cápsula | 5, 02 |
| `Cartao` | `.comp-card`: borda de 1px `borda`, fundo `surface`, 2rem de respiro, 1.5rem entre as partes, borda clareando no hover | 5 |
| `Aviso` | Borda de 4px à esquerda na cor do tom, ícone do sprite, título curto maiúsculo, corpo em mono | 5, 05 |
| `Medidor` | Anel de 2px com arco em ciano e brilho, número em mono no centro | 5, 05 |
| `Vazio` | Tracejado `dim` que vira `ciano` no hover, ícone em círculo apagado | 5, 02 |
| `.rotulo` | `.comp-label`: mono, 0.65rem, `dim`, maiúsculo, espaçado em 0.1em | 5 |
| `.titulo-secao` | `.section-title`: mono, ciano, espaçado em 0.2em, com régua embaixo | 5 |

**Ícones.** Os 50 do sprite da seção 1 (grade de 24px, traço de 2px) vivem em `design/icones.ts`,
extraídos sem retoque, e saem pelo `<Icone nome="nav-dashboard" />`. Nenhum ícone de biblioteca de
fora e nenhum SVG desenhado à mão numa tela. Ícone que falta entra no sprite primeiro.

Ainda a construir, nas etapas que precisarem: `Area`, `Escolha`, `Abas`, `Tabela`, `Modal`,
`Passos` (o stepper da seção 5, 04), `Trilha` (o breadcrumb) e `Grafico` (a AXIS, seção 2).

### 3.1 O design system é a única fonte, e o painel usa ele inteiro

Regra dura: **nada de biblioteca de interface de fora**. Sem Radix, sem shadcn, sem Headless UI, sem
Chart.js, sem Recharts, sem Framer Motion, sem lucide, sem heroicons. O que a tela precisar nasce de
`designsystem/index.html`, copiado com a seção de origem no comentário do arquivo. Quando o design
system não traz a peça pronta (Abas, Tabela, Modal), ela é montada com as primitivas dele (borda de
1 px `borda`, fundo `surface`, rótulo mono maiúsculo, acento ciano, cantos retos, os dois cantos
marcados em SVG), nunca com uma peça de fora nem com um estilo inventado na hora.

O painel tinha usado até aqui só a seção 5. As seis seções entram, cada uma com dono:

| Seção do design system | O que traz | Onde entra |
|---|---|---|
| 1. Icon System | 50 ícones, grade 24 px, traço 2 px | `design/icones.ts`, já construído. Ícone que falta entra no sprite primeiro |
| 2. AXIS | motor SVG puro (linha, radial, barra, rosca, área, medidor, gauge, treemap) | `Grafico.tsx`, portado para React sem biblioteca: área, barras, rosca e ponteiro construídos; radar, linha dupla e treemap quando uma tela precisar |
| 3. KINETIC | 10 estados de carregando (spinner, pulso, barras, anel, digitando, envio, progresso) e 15 microinterações (foco, marcar, interruptor, sucesso, erro que treme, expandir, tooltip, arrastar, notificação) | `Carregando` com seis formas, uma por tipo de espera (construído); microinterações no salvar de cada seção, erro de formulário, criação do agente e QR da WAHA |
| 4. ONYX decorativos | divisores (onda, degrau, seta), padrões sem emenda (pontos, malha, circuito, grade), acentos (brilho, asterisco, colchetes, círculo de marcador, mira), geometria fluida, fita de selo | fundo de tela vazia, topo do onboarding, selo "em breve", marcação do passo atual |
| 5. ONYX UI | botões, campos, cartões, navegação, situação, barras de proporção | base já construída, mais `Progresso` (o "System Health" da AXIS) e, nas etapas seguintes, `Passos`, `Trilha`, `Busca`, `Envio de arquivo`, `Marcar`, `Tooltip`, `Grupo de avatar`, `Transição de sucesso` |
| 6. NEXUS PRO | composição de página inteira, hierarquia e respiro | referência de layout da Visão geral e do onboarding |

Um teste a mais entra junto com esta regra: nenhum `package.json` do `frontend/` ganha dependência
de interface fora de `react`, `react-dom`, `react-router-dom`, `@fontsource` e as de build. A lista
permitida fica no próprio teste.

Três testes seguram a regra: nenhum arquivo fora do `tailwind.config.ts` escreve cor (hexadecimal
ou `rgb`), o sprite tem os 50 ícones dos seis grupos, e nenhuma tela escreve `<svg>`.

Tema: escuro sempre, na primeira versão. Não existe alternador claro/escuro.

### 3.2 As telas de entrar e de primeiro acesso

Elas são Jinja2, não React: existem antes da sessão, e o front só começa depois do login. Mesmo
assim são do mesmo design system, com a mesma marca, os mesmos cantos marcados, o mesmo campo com
borda só embaixo e o mesmo botão sólido.

O `backend/app/painel/estaticos/painel.css` é o **único lugar do projeto onde cor se escreve em
hexadecimal**, porque ele não passa pelo Tailwind. Todas ficam no `:root` dele, com os mesmos valores
da tabela acima, e em nenhum outro lugar do arquivo.

Inter e JetBrains Mono são servidas pela API em `/painel/fontes/<arquivo>`, de uma lista fechada de
nomes: nada de CDN, aqui também. O endereço da folha carrega a versão (`painel.css?v=<mtime>`), senão
o navegador guarda a folha antiga e o operador vê o estilo da versão passada depois de atualizar.

Não existe mais painel em Jinja2 além dessas duas telas: `/painel/inicio` e `/painel/agentes` eram o
painel de antes do front e viraram desvio para `/painel/app`.

## 4. Casca e navegação

Menu lateral fixo, recolhível, com a marca no topo e o operador no rodapé (sair). Fixo de verdade:
**a página não rola, quem rola é o conteúdo da direita**. O menu é um bloco comum de uma linha que
não rola, então ele não tem como se mexer; com `sticky` ele grudaria, mas ainda participaria da
rolagem da página. A altura é `h-dvh`, não `h-screen`, porque no celular a barra do navegador some e
volta e `100vh` não acompanha. No celular o menu vira gaveta, aberta por um botão solto no canto
superior esquerdo. Itens, nesta ordem:

| Item | Rota | Situação |
|---|---|---|
| Visão geral | `/` | ativo |
| Agentes | `/agentes` | ativo |
| Canais | `/canais` | ativo |
| Chat | `/chat` | ativo |
| Contatos | `/contatos` | ativo |
| Base de conhecimento | `/conhecimento` | em breve, item apagado com selo |

**Não existe barra do topo.** A tela começa no conteúdo. Uma faixa fixa atravessando a página só se
justifica se carregar algo que a pessoa usa o tempo todo, e não era o caso: ela tinha uma busca e um
ponto de situação, e comia uma faixa inteira para isso.

- **Busca** nasce na tela de Agentes (etapa 3), que é onde existe o que procurar. Cada tela que
  precisar tem a sua, no próprio cabeçalho.
- **Filtro de tela mora na tela**: o seletor de empresa fica no cabeçalho da Visão geral, ao lado do
  período. Na barra do topo ele parecia trocar a instalação inteira e trocava só os números de uma
  tela.
- **Situação da plataforma** (verde, amarelo, vermelho) fica no rodapé do menu lateral, junto do
  operador e do sair: é informação da instalação, não de uma tela. Com o menu recolhido sobra o
  ponto colorido. O texto é curto de propósito, porque cabe em uns 200px.
- **No celular** sobra só o abridor da gaveta, solto sobre o conteúdo no canto superior esquerdo.

A situação sai do que a API sabe, não do `asimov diagnostico`: falha `canal_fora_do_ar` no período é
vermelho, outra falha recente ou handoff vencido é amarelo, nada é verde. O código HTTP de cada
endereço continua sendo pergunta do terminal, que roda por dentro da VPS. Registrado em
spec/decisoes.md.

Estados obrigatórios em toda tela: carregando, vazio com o que fazer a seguir, erro com o que
aconteceu e o botão de tentar de novo. Tela sem os três não passa na revisão.

## 5. Telas

### 5.1 Visão geral

**Quem abre esta tela já vive no terminal.** Ele vem por uma pergunta só: está tudo de pé e onde eu
preciso agir. Por isso a tela é de triagem, não de relatório, e a ordem é a da urgência.

| Ordem | O que é | Tratamento |
|---|---|---|
| 1 | O veredito: uma frase que responde a pergunta ("Tudo no ar", "2 conversas passaram do prazo", "Um canal saiu do ar") | título grande em Inter, com a régua de 4px do `Aviso` na cor do estado à esquerda |
| 2 | Esperando você: handoff aberto, com o tempo parado e o `/retomar <código>` | lista com régua vermelha no que passou do prazo. **Some inteira quando não há nada**, em vez de virar cartão dizendo que está tudo bem |
| 3 | O ritmo: turnos, custo e quanto o agente fechou sozinho, e a curva do período | três números soltos sobre o fundo, sem moldura, com a curva da AXIS atravessando a largura |
| 4 | Quem respondeu, e onde travou | dois cartões, que é onde cartão serve: separar duas coisas diferentes |
| 5 | Para onde foi o dinheiro | um cartão largo, rosca à esquerda e a fatia de cada modelo à direita. Por último porque é o que menos pede ação |

Regras que valem para a tela:

- **Número nunca aparece sozinho**: cada um vem com a comparação com o período anterior, em por
  cento, verde quando é bom e vermelho quando é ruim (custo e falha subindo é ruim). Sem período
  anterior, "sem período anterior para comparar", nunca um "+100%" sobre zero.
- **Cada cartão espera com a forma do KINETIC** que combina com o que vai aparecer nele.
- **A falha é dita em português de gente** ("O modelo não respondeu"), com o tipo cru embaixo em
  letra pequena, que é por onde se procura no log. O detalhe do provedor sai no mesmo resumo curto
  do terminal, nunca cru.
- **Nome de pessoa não vai em caixa alta**, nem identificador de modelo. A caixa alta em mono é do
  design system para rótulo de dado, e é só para isso.
- **Sem corda de meta com ponto do meio** (`A · B · C`) e sem rótulo em caixa alta acima de cada
  número: as duas coisas são chrome, e chrome não informa.
- Período e empresa ficam no cabeçalho da tela, não numa barra global.

### 5.2 Agentes: lista

Lista à direita com filtro Todos, Ativos e Inativos. Cada linha: inicial ou avatar, nome, selo de
situação, "Vendedor em <empresa>" (função mais empresa) e menu de ações (editar, ativar, remover).
Botão "Criar agente" no canto superior direito.

Criar agente abre o onboarding da seção 5.2.1, não um formulário.

### 5.2.1 Onboarding do agente

O ponto onde o painel ganha ou perde o operador. No terminal são sete perguntas seguidas; aqui a
mesma ordem vira uma tela inteira, com o resultado aparecendo enquanto ele responde.

**Popup grande no meio da tela, com o que está atrás embaçado.** Regra do operador, de 2026-09-18:
toda configuração de agente acontece assim. A lista continua montada atrás, desfocada e escurecida,
para o foco ficar no agente. Rota própria (`/agentes/novo`), que abre o popup sobre a lista; sai com
Esc ou com "Sair", que pergunta antes quando há resposta escrita. Rascunho guardado no navegador:
fechar o notebook e voltar não perde o que já foi respondido.

**Uma pergunta por vez, três coisas dentro do popup.** À esquerda os `Passos` (stepper da seção 5,
04) com o que já ficou pronto, o passo atual e o que falta. No meio a pergunta, grande, com a ajuda
em uma linha abaixo. À direita a **prévia viva**: uma conversa de mentira onde o agente já responde
com o que foi escolhido. Trocar o nível de emoji muda a bolha na hora; escolher vendas muda o jeito
da frase; marcar a busca na web faz aparecer a citação. É o que responde sozinho a pergunta "o que
isso muda no meu agente", que hoje só o teste em produção responde.

**Os passos**, na ordem do terminal:

1. **Empresa**: escolher uma existente ou criar. Some quando a instalação não é revenda.
2. **Canal**: quatro cartões com os cantos marcados, ícone do sprite, uma linha do que serve e um
   rótulo do que exige (Chatwoot pede URL e token, oficial pede app e token da Meta, WAHA pede o
   celular à mão para ler o QR, nativo não pede nada). O cartão diz o custo de entrada antes de o
   operador entrar nele.
3. **Nome e função**: nome do agente e suporte, vendas ou atendimento, com a prévia mudando de tom.
4. **Sobre a empresa**: público, site e o texto livre. Abaixo, um painel que dobra: "ver o que o
   agente vai ler", com o `persona.md` sendo montado ao vivo.
5. **Jeito de falar**: emoji, partes da resposta, tempo de espera, velocidade de digitação. Todos
   refletem na prévia, com o digitando do KINETIC no ritmo escolhido.
6. **Ferramentas**: catálogo com interruptor e a instrução de quando usar. `transferir_para_humano`
   sempre ligada, com destino e prazo.
7. **Conectar**: o que o canal exige, com o QR da WAHA desenhado aqui quando for o caso.

**Nada trava sem necessidade.** Só empresa, canal e nome são obrigatórios; o resto tem valor padrão
e um "pular por ora" que deixa a pendência marcada na ficha. O passo de conexão pode ficar para
depois: o agente nasce inativo e a lista mostra "falta conectar" com o caminho de volta.

**O fim é um começo.** Terminar não devolve um "pronto": roda a transição de sucesso do KINETIC e
abre a conversa de teste pelo canal nativo já com a primeira mensagem sugerida. O operador fala com
o agente antes de sair da tela. Ao lado, três atalhos: ver a ficha, conectar o canal, criar outro.

**Erro é do passo, não da tela.** Falha da API aparece no passo que falhou, com o texto do que
aconteceu e tentar de novo, sem perder as respostas anteriores. A criação é uma chamada só no fim
(`POST /painel/api/agentes`): passo nenhum grava pela metade.

Acessibilidade: navegação inteira pelo teclado (Tab, Enter e Esc), `aria-current` no passo, foco
indo para o título a cada troca de passo e prévia marcada como `aria-live="polite"`.

### 5.3 Agente: ficha

**Também em popup**, o mesmo da criação: ele abre sobre a lista, que fica embaçada atrás. Não existe
página de edição de agente. Rota `/agentes/{id}` e `/agentes/{id}/{aba}`, para recarregar e
compartilhar o endereço caírem na mesma aba.

Abas: **Perfil**, **Comunicação**, **Trabalho**, **Ferramentas e integrações**, **Configurações** e
**Conversar**. A última é a conversa de teste pelo canal nativo, que a spec antes punha na tela de
Chat: falar com o agente é como se confere uma mudança antes de ela chegar em alguém, e isso
pertence ao agente, não à lista de conversas. Registrado em spec/decisoes.md.
Cada seção tem o próprio botão Salvar, e sair com alteração pendente pede confirmação. Salvar
mostra o que mudou, não um "pronto" genérico.

**Perfil**: nome, empresa, canal, situação (ativo ou inativo), criado em, endereço do webhook
(mostrado uma vez, com copiar) e remover agente.

**Comunicação**: emoji (nenhum, pouco, médio, muito), dividir resposta em partes (até quantas),
tempo de espera antes de responder (buffer, em segundos), velocidade de digitação e teto do
digitando, assinar o nome do agente na resposta.

**Trabalho**: a seção que escreve o prompt.

- Função: suporte, vendas ou atendimento.
- Vende (ou atende) para: texto curto sobre o público.
- Site: opcional.
- Sobre a empresa: texto livre, com o rótulo "Descreva um pouco sobre <nome da empresa>".
- Abaixo, em "Prompt gerado", o `persona.md` resultante, com opção de editar à mão.

**Ferramentas e integrações**: catálogo de `ia/ferramentas/registro.py` com interruptor por
ferramenta e a instrução de quando usar. `transferir_para_humano` sempre ligada, com o destino e o
prazo de retomada automática. Google Calendar como cartão apagado, com selo "em breve".

**Configurações**: modelo e fornecedora por função (conversa, reserva, auxiliar, visão,
transcrição), com a lista vinda do backend (`openai`, `anthropic`, `gemini`, `groq`; transcrição
sem `anthropic`). Contatos permitidos. Ações do canal (reconectar, trocar número, ver QR).

### 5.4 Canais

Lista dos canais em uso com situação por agente: Chatwoot (inbox e bot), WhatsApp oficial (número e
verificação), WhatsApp pela WAHA (pareamento, QR, reiniciar) e nativo. Ação de reiniciar e de
reparear. Criar canal continua no terminal na primeira versão do front.

### 5.5 Chat

Duas colunas, não popup: a lista à esquerda e a conversa aberta à direita, porque aqui o operador
compara uma com a lista enquanto lê. O popup é a regra da configuração do agente, que é outra coisa.

Conversas com filtro por agente, empresa e situação (com o agente, com gente). Abrir uma
conversa mostra o histórico, quem falou, o turno (modelo, tempo, tokens, custo) e o botão de devolver
ao agente quando está em handoff. Aba de conversa de teste, pelo canal nativo, que já existe na API.

Conteúdo de conversa aparece no navegador: é decisão consciente, registrada em decisões, e o acesso é
só do operador, sem exportação e com `noindex`.

### 5.6 Contatos

Lista com busca por nome e telefone, e ficha com as conversas do contato e os dados extraídos de
mídia. Sem exportação em massa.

### 5.7 Base de conhecimento

Tela com o selo "em breve" e uma linha sobre o que vai fazer, ligada à Fase 6. Não chama rota
nenhuma.

## 6. Contrato `/painel/api`

Leitura pode chamar `repo.py`; escrita sempre passa por `servico.py`. Toda rota confere a sessão e,
quando recebe `cliente_id`, confere que ele existe antes de usar. `cliente_id` nunca vem do corpo.

```
GET    /painel/api/eu                         operador, tamanho da instalação e token de escrita
GET    /painel/api/visao-geral                números do período, falhas e handoffs abertos
GET    /painel/api/empresas                   lista de empresas
POST   /painel/api/empresas                   cria empresa
GET    /painel/api/agentes                    lista global, com filtro por empresa e por situação
POST   /painel/api/empresas/{cliente}/agentes cria agente na empresa
GET    /painel/api/agentes/{id}               ficha
PATCH  /painel/api/agentes/{id}               perfil, comunicação, trabalho, modelos, ferramentas
DELETE /painel/api/agentes/{id}               remove
GET    /painel/api/agentes/{id}/prompt        persona.md atual
PUT    /painel/api/agentes/{id}/prompt        grava à mão
POST   /painel/api/agentes/{id}/teste         turno de teste pelo canal nativo
GET    /painel/api/ferramentas                catálogo
GET    /painel/api/modelos                    provedores e modelos por função
GET    /painel/api/canais                     situação por agente
POST   /painel/api/agentes/{id}/canal/acao    reiniciar, reparear, ver QR
GET    /painel/api/conversas                  lista com filtro
GET    /painel/api/conversas/{id}             histórico e turnos
POST   /painel/api/conversas/{id}/retomar     devolve ao agente
GET    /painel/api/contatos                   lista com busca
GET    /painel/api/contatos/{id}              ficha
```

Onde a rota cria dentro de uma empresa, o `cliente_id` vem da URL e é conferido no banco antes de
virar filtro. Nas rotas de um agente (`/agentes/{id}`) ele sai da própria linha do agente lida do
banco, nunca do corpo: é a mesma garantia com uma URL mais curta, que é o que o front precisa para
abrir o popup a partir da lista.

## 7. Mudanças no banco

Uma migração, aditiva:

- `agente.perfil` (JSONB, padrão `{}`) com `funcao`, `publico`, `site` e `sobre_empresa`.
- `agente.assina_nome` (booleano, padrão falso).

Agente criado antes fica com `perfil` vazio e a aba Trabalho mostra o prompt à mão, sem inventar
campo. O `perfil` é por agente, não por empresa: é o que impede um prompt de atravessar de uma
empresa para outra, como já aconteceu (achado A05 da auditoria).

O `persona.md` continua sendo a fonte do prompt de sistema. O formulário preenche o modelo de
`modelos/prompts/persona.md` e grava o arquivo; editar à mão continua valendo e o painel avisa que
salvar o formulário reescreve o texto.

## 8. Regras que não mudam

- `/admin` nunca é publicado. O front não conhece a `CHAVE_API_ADMIN`.
- Credencial de canal nunca sai do banco em claro, nem para o front.
- Toda consulta filtra por `cliente_id`, com as exceções já listadas no `AGENTS.md`.
- Toda entrada é validada no backend. Validação no front é conveniência, nunca defesa.
- Operação nasce na API: menu do terminal e painel consomem a mesma rota. Nada que exista só num dos dois.
- Estático servido da VPS, nunca de CDN.
- Sem travessão em texto de tela.
- Repositório público: nada de nome de cliente, domínio ou número real, nem nos dados de exemplo.

## 9. Etapas de construção

Uma etapa por vez, cada uma com tela navegável, rota real e teste. A etapa só termina quando roda na
VPS, os testes passam e o `shellcheck` não acusa erro.

| Etapa | Entrega | Aceite |
|---|---|---|
| 1. Fundação **(construída, falta a VPS)** | `frontend/` com Vite, Tailwind com os tokens, componentes de base, build num estágio `node` do Dockerfile, API servindo `/painel/app` com retorno ao `index.html`, `GET /painel/api/eu` | Entro com a senha, caio no painel novo, vejo a casca e saio. Sem sessão, volto para entrar |
| 2. Casca e Visão geral **(construída, falta a VPS)** | Menu lateral recolhível, gaveta no celular, barra do topo, `Grafico` portado da AXIS (seção 2) e as animações do KINETIC (seção 3), tela de visão geral com cartões, gráficos, falhas e handoffs | Abro no celular e no computador, troco de período e os números batem com `asimov consumo` |
| 3. Agentes: lista e onboarding **(construída, falta a VPS)** | Lista com filtro, cartão do agente, o onboarding da seção 5.2.1 em tela cheia, com passos, prévia viva e rascunho | Crio um agente de Chatwoot pelo onboarding, converso com ele antes de sair da tela e ele aparece no `asimov agentes` |
| 4. Agente: Perfil e Comunicação **(construída, falta a VPS)** | Duas abas, salvar por seção, remover agente | Mudo o emoji e a divisão de resposta, mando mensagem e a resposta muda |
| 5. Agente: Trabalho **(construída, falta a VPS)** | Migração do `perfil`, formulário, geração do `persona.md`, editor do prompt | Preencho os campos, salvo, abro o `persona.md` na VPS e o texto está lá; o agente responde no papel escolhido |
| 6. Agente: Ferramentas e integrações **(construída, falta a VPS)** | Catálogo com interruptor, handoff com destino e prazo, cartão do Google Calendar em breve | Desligo a busca web, pergunto algo que precisa dela e o agente não usa |
| 7. Agente: Configurações **(construída, falta a VPS)** | Modelos por função, contatos permitidos, ações do canal | Troco a fornecedora do modelo de conversa e a resposta seguinte usa a nova |
| 8. Canais **(construída, falta a VPS)** | Tela de canais com situação, QR da WAHA, reiniciar | Vejo o número conectado, reinicio e ele volta |
| 9. Chat **(construída, falta a VPS)** | Rotas de conversa e mensagem, lista, histórico, devolver ao agente, conversa de teste | Abro uma conversa real, vejo o turno e devolvo um handoff pelo painel |
| 10. Contatos **(construída, falta a VPS)** | Lista com busca e ficha | Acho um contato pelo telefone e vejo as conversas dele |
| 11. Base de conhecimento e polimento **(construída, falta a VPS)** | Tela em breve, vazios, erros, acessibilidade, responsivo | Navego o painel inteiro no celular sem quebrar, e nenhum erro no console |

Testes por etapa: pytest para toda rota nova, com isolamento por `cliente_id` obrigatório; vitest
para o cliente de API e para os componentes de base; a checagem de que ninguém escreve cor solta.
