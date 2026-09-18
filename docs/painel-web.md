# Painel web em `app.<dominio>`: estudo de viabilidade

Estudo da opção de, depois que a plataforma sobe, o operador escolher entre **seguir só no terminal**
(como hoje) ou **instalar um painel web** em `app.<dominio>`, que no primeiro acesso conduz a
configuração como o setup faz e depois vira uma dash de operação (conversas em andamento,
ferramentas, consumo, handoff).

> **Estudo histórico. Não use como referência do que existe hoje.**
>
> Escrito contra a `v0.17.0`, quando o painel ainda não existia. A decisão final foi outra: o painel
> foi construído como SPA em React, Vite e Tailwind, e não em Jinja2 com HTMX como este documento
> recomenda. A seção que diz que a chave do provedor não pode sair do `.env` também deixou de valer:
> desde a v0.20.0 ela fica cifrada no banco. O que existe hoje está em `spec/frontend.md` e
> `spec/estado.md`; as decisões, em `spec/decisoes.md`.

Este documento começou como análise, escrito em 2026-09-18 contra a `v0.17.0`.

## 0. O que já está construído

Fora da versão publicada, no diretório de trabalho:

| Onde | O que é | Situação |
|---|---|---|
| `painel/prototipo/` | Protótipo estático das onze telas, com dados de exemplo | Navegável, sem erro de console; valida telas e fluxos |
| `backend/app/painel/` | Pacote do painel: modelos, repo, serviço de acesso, rotas e templates Jinja | Entrar, primeiro acesso com código de uso único, sessão, início e lista de agentes |
| `backend/migrations/versions/20260918_0014_usuario_painel.py` | Tabela `usuario_painel` | Migração aplicada em banco local |
| `backend/testes/test_painel.py` | 29 testes: senha, código, sessão, freio, origem, isolamento e o que a tela não mostra | Passando, junto dos 266 anteriores (295 no total) |
| `deploy/Caddyfile`, `deploy/caddy/` | `import` de extras e o bloco de `app.<dominio>`, escrito pelo setup | O arquivo existe sempre; só tem comentário com o painel desligado |
| `setup/lib/painel.sh` | `asimov painel`: liga, desliga, espera o DNS, gera o código e apaga a conta | `shellcheck` sem erro; nunca rodou em VPS |
| `.env.example`, `config.py` | `PAINEL_ATIVO` e `SUBDOMINIO_APP`, desligados por padrão | Com o painel desligado, a API é a de sempre |

Conferido rodando a API de verdade num banco local: primeiro acesso com o código, sessão, dash
listando agentes e empresas reais do banco. Falta o que está na parte 8.2 e 8.3 abaixo.

Dois defeitos encontrados e corrigidos durante a construção, que valem registro:

- `hashlib.scrypt` com `n=2^15` estoura o limite de memória padrão do OpenSSL e falhava com
  `memory limit exceeded` depois de o código de uso único já ter sido gasto. Passou para `n=2^14`
  com `maxmem` explícito.
- A checagem de origem comparava por prefixo, então `app.exemplo.com.br.outracoisa.com` passava.
  Agora compara host e porta normalizados, com teste para cada caso.

## 1. Resumo em cinco linhas

- **É viável e a arquitetura já favorece**: `rotas.py` / `servico.py` / `repo.py` são separados desde
  o começo, e `spec/arquitetura.md` diz em letras claras que o front, quando chegar, usa as mesmas
  operações do menu. Nenhuma regra de negócio precisa ser reescrita.
- **O backend de domínio não sofre modificação pesada.** Nenhum `servico.py` existente muda.
- **A modificação pesada está em um ponto só**: hoje o plano de controle não existe na internet
  (`/admin` não é publicado, a API escuta em `127.0.0.1:8000`, a única credencial é uma chave
  compartilhada no `.env`). O painel obriga a criar login, sessão e uma nova superfície pública.
- **O item mais caro não é o painel, é o assistente de configuração**: reproduzir na web o que
  `waha.sh` (644 linhas) e `whatsapp.sh` (380 linhas) fazem no terminal é trabalho novo, não
  reaproveitamento.
- **Recomendação**: fazer em três partes, e na primeira versão do painel entregar a dash de operação
  mais o assistente dos canais baratos (nativo e Chatwoot), deixando WAHA e WhatsApp oficial no
  terminal. Isso corta cerca de 40% do esforço e quase todo o risco de retrabalho.

## 2. O que o pedido contraria hoje

Três coisas escritas hoje como regra:

| Onde | Regra de hoje | O que o painel faz com ela |
|---|---|---|
| `AGENTS.md`, regras que não mudam | "NUNCA publique `/admin` no Caddy" | Continua valendo. O painel não publica `/admin`: ele ganha caminho próprio. A regra é preservada, não quebrada |
| `AGENTS.md`, organização | "Não existe `frontend/` na primeira versão" | Muda. Vira "não existe SPA", com o painel servido pela própria API |
| `spec/visao.md`, fora de escopo | "Front de CRM (a pessoa pode usar um front próprio)" | Continua fora. Painel do operador não é CRM de atendente, e a diferença precisa ficar escrita (seção 9) |

Uma quarta, não escrita mas real: **conteúdo de conversa nunca apareceu em tela nenhuma**. A v0.14.2
tirou o texto das mensagens do log por privacidade. Uma dash com "sessões ativas" mostra conversa de
contato no navegador. É decisão de produto consciente, não detalhe de implementação.

## 3. Três caminhos, e por que um deles

| Caminho | Como é | Esforço | Risco | Atende o pedido |
|---|---|---|---|---|
| **A. Túnel SSH** | O painel escuta só em `127.0.0.1`. O operador abre com `ssh -L 8080:127.0.0.1:8000`. Sem DNS, sem certificado, sem login | Baixo | Quase zero: quem entra já tinha a VPS | Não. Sem `app.<dominio>`, sem celular |
| **B. Caminho no host que já existe** | `https://bot.<dominio>/painel`. Sem registro DNS novo, sem certificado novo | Médio | Mistura o host dos webhooks com o host do operador | Em parte |
| **C. Host próprio `app.<dominio>`** | Bloco novo no Caddy, registro A novo, certificado próprio. Separado dos webhooks | Médio-alto | Superfície pública nova, que é o custo real | Sim |

**Recomendado: C**, que é o pedido, com **A disponível de graça** como modo de emergência (o painel
responde igual em `127.0.0.1:8000` quando o operador não quer expor nada). B fica como reserva se o
operador não quiser criar registro DNS: é a mesma implementação com outro matcher no Caddy.

Vale dizer o que C **não** aumenta: o processo `api` já está exposto à internet hoje, porque o Caddy
já faz proxy de `bot.<dominio>` para `api:8000` por causa dos webhooks. O que cresce é o conjunto de
rotas alcançáveis, não o número de processos expostos.

## 4. Desenho recomendado

### 4.1 Onde o painel mora

```
backend/app/painel/
├── rotas.py      login, sessão, páginas e ações
├── servico.py    senha, sessão, convite de primeiro acesso, limite de tentativas
├── repo.py       usuário do painel
├── modelos.py    UsuarioPainel
├── paginas/      templates Jinja2
└── estaticos/    css, htmx.min.js, qrcode.min.js (servidos da VPS, nunca de CDN)
```

Um pacote como qualquer outro do backend, com a mesma divisão de camadas. `rotas.py` do painel chama
os `servico.py` que já existem (`agentes/servico.py`, `consumo/servico.py`, `canais/waha/...`),
exatamente como as rotas `/admin` fazem. Zero regra duplicada.

**Alternativa considerada e descartada:** container separado que fala com `api:8000/admin` usando a
`CHAVE_API_ADMIN` pela rede interna, virando um segundo cliente da API como o menu. É mais fiel ao
princípio "o setup é o único cliente da API", mas custa mais um build, mais uma imagem e mais um
ponto de atualização, e não isola nada de verdade: quem executa código no painel executa no mesmo
lugar. Vale reconsiderar se o painel um dia crescer para atendente ou cliente final.

### 4.2 Autenticação, que é o ponto sensível

- **Uma conta só, do operador.** Tabela `usuario_painel` com uma linha: senha em Argon2id
  (`argon2-cffi`), criada em, último acesso. Sem cadastro aberto, sem recuperação por e-mail (a VPS
  não manda e-mail).
- **Primeiro acesso com convite de uso único.** O setup imprime no terminal um código de 8 a 10
  caracteres, válido por 15 minutos, gravado no Redis. Sem ele, `app.<dominio>` responde uma tela que
  só diz "rode `asimov painel` na VPS". Isto fecha a corrida óbvia: sem convite, quem descobrir o
  domínio antes do operador é quem define a senha.
- **Sessão no Redis** (`SETEX`, 12 horas, renovada no uso), cookie `HttpOnly`, `Secure`,
  `SameSite=Lax`, sem `localStorage`. O Redis já sobe com `appendonly yes`, então reinício não
  derruba ninguém.
- **Token CSRF** por sessão em todo formulário. Mesma origem, sem CORS.
- **Freio de tentativa** por IP e global no Redis: 5 erros seguidos custam espera crescente. Registra
  Falha, que já é entidade existente e já aparece no menu.
- **Camada extra opcional na porta**: `basicauth` do Caddy com hash gerado pelo setup
  (`caddy hash-password`). Custa dez linhas e tira o painel da vista de qualquer varredura. Bom para a
  primeira versão, chato no celular. Fica como pergunta ao operador.
- **Segundo fator (TOTP)**: fora da primeira versão, mas o modelo de dados já pode nascer com a coluna.

### 4.3 Caddy e DNS

No host `app.<dominio>`, apenas o painel responde, e `/admin*` e `/webhook*` respondem 404 de forma
explícita, não por falta de rota:

```
{$SUBDOMINIO_APP} {
	@bloqueado path /admin* /webhook*
	handle @bloqueado {
		respond 404
	}
	handle {
		reverse_proxy api:8000
	}
}
```

O problema é que um bloco com `{$SUBDOMINIO_APP}` vazio quebra o Caddy inteiro, e o painel é
opcional. Solução: o Caddyfile principal termina com `import /etc/caddy/extras/*.caddy`, o setup
monta `deploy/caddy/` no contêiner e **sempre** escreve `deploy/caddy/painel.caddy`, com só um
comentário dentro quando o painel está desligado (glob que não casa arquivo nenhum é erro em algumas
versões do Caddy, então o arquivo existir sempre é o caminho seguro).

Depois de escrever o arquivo, `caddy reload`. Isso já está em `sobe_servicos` desde a v0.16.1, e a
armadilha está registrada no `AGENTS.md`: mudar o arquivo montado não muda o que o Caddy carregou.

DNS: mais um registro A, `app`, para o mesmo IP. A `tela_dns` de hoje espera um host só; passa a
esperar dois quando o painel é escolhido. O código de `dns.sh` já é genérico o bastante
(`ip_do_dominio` recebe o nome), muda o laço e o texto.

### 4.4 O que o setup passa a perguntar

Depois de `tela_instalacao` (a plataforma já no ar) e antes do primeiro agente:

```
Como você prefere administrar?

  > Pelo terminal, com o comando asimov   (como sempre)
    Por um painel no navegador            (app.<dominio>, também no celular)
```

Escolhendo painel:

1. Pergunta o subdomínio (padrão `app`), grava `SUBDOMINIO_APP` no `.env`.
2. Espera o DNS, como já faz com `bot`.
3. Escreve `deploy/caddy/painel.caddy`, sobe e recarrega o Caddy, espera o certificado.
4. **Pula `tela_primeiro_agente`** e mostra no resumo a URL e o código de primeiro acesso.

Comando novo: `asimov painel`, que mostra a URL, gera outro código de acesso, liga e desliga o painel
e troca a senha. O `asimov diagnostico` ganha mais uma linha (código HTTP de `app.<dominio>`).

### 4.5 Front sem build

| Opção | Prós | Contras |
|---|---|---|
| **Jinja2 + HTMX + CSS próprio** | Sem Node na VPS, sem build, sem passo de deploy novo. Polling e troca de pedaço de tela saem de graça, que é o que a conversa de teste e o QR code precisam. O operador edita um `.html` e vê o resultado | HTML no servidor, menos confortável para telas muito interativas |
| **HTML estático + Alpine.js consumindo JSON** | Painel vira cliente da API de verdade | Duas linguagens de estado, mais código para o mesmo resultado |
| **SPA (React/Vite)** | Confortável para telas ricas | Precisa de build, de Node no deploy ou de artefato commitado, e cria a pasta `frontend/` que a spec adiou. Não paga nesta escala |

**Recomendado: Jinja2 + HTMX**, com os arquivos JS servidos da própria VPS. Casa com o resto do
projeto (Bash e Python, sem Node em runtime) e com o jeito do operador de evoluir em vibecoding.

## 5. O que já existe e o que falta

Esta é a tabela que decide o tamanho do trabalho.

### 5.1 Pronto na API, é só desenhar a tela

| Função da dash | Rota que já existe |
|---|---|
| Listar empresas e criar empresa | `GET/POST /admin/clientes` |
| Listar agentes, ver agente, webhook, URL de privacidade | `GET /admin/agentes`, `GET .../agentes/{id}` |
| Criar agente em qualquer canal | `POST /admin/clientes/{c}/agentes` |
| Editar nome, buffer, mensagens, digitação, emoji, modelos, handoff | `PATCH .../agentes/{id}` |
| **Ligar e desligar ferramentas** | `GET /admin/ferramentas` (catálogo com rótulo e descrição) e o mesmo `PATCH` |
| Remover agente e empresa | `DELETE .../agentes/{id}`, `DELETE /admin/clientes/{id}` |
| Consumo, custo e últimas falhas | `GET /admin/consumo` |
| Conectar agente nativo a um canal | `POST .../agentes/{id}/canal` |
| Descobrir contas e caixas no Chatwoot | `POST /admin/canais/{canal}/descobrir` |
| Token de administrador guardado, esquecer token | `GET/DELETE /admin/canais/{canal}/acessos` |
| Conversa de teste com o agente | `POST` e `GET .../terminal` (já com digitando, turno, custo e handoff) |
| QR code e status da WAHA, reiniciar sessão, grupos | `GET .../waha`, `POST .../waha/reiniciar`, `GET .../waha/grupos` |
| Número na Meta, refazer webhook | `GET .../whatsapp`, `POST .../whatsapp/webhook` |
| Retomar conversa em handoff | `POST .../conversas/{id}/retomar` |
| Saúde da instalação | `GET /health` |

É bastante coisa. A parte de **ferramentas** sai praticamente de graça, e a **conversa de teste** já
devolve tudo o que uma tela precisa, inclusive latência, tokens, custo e ferramentas usadas do último
turno.

### 5.2 Falta no backend

| Função | O que falta | Tamanho |
|---|---|---|
| **Sessões ativas (conversas em andamento)** | `GET /admin/conversas` com filtro por cliente, agente, status e período, e `GET /admin/conversas/{id}` com mensagens paginadas. Repo, serviço, rota, índice `(cliente_id, atualizado_em)` e teste de isolamento | Médio |
| Handoffs abertos numa lista | `GET /admin/handoffs`. Resolve também uma pendência antiga: hoje não existe como listar conversa em handoff no Chatwoot pelo menu | Pequeno |
| Contatos | `GET /admin/contatos`, com a mesma regra de isolamento | Pequeno |
| **Ver e editar o prompt do agente** | `GET/PUT .../agentes/{id}/prompt` lendo e escrevendo `prompts/<cliente>/<agente>/persona.md`. É o que o operador mais quer mexer, e hoje só existe por SSH | Pequeno, valor alto |
| Falhas paginadas | Hoje só as 10 últimas vêm junto do consumo | Pequeno |
| Visão geral das sessões WAHA | Existe por agente; falta a lista de todas | Pequeno |
| QR code como imagem | A rota devolve texto cru para o `qrencode` desenhar. No navegador, ou uma lib JS local desenha, ou uma rota nova devolve PNG | Pequeno |
| Usuário, sessão, convite e freio de tentativa | Tudo novo, com migração | Médio |

### 5.3 O que o painel não vai conseguir fazer

Limite que precisa ficar escrito, senão vira expectativa frustrada:

- **Chave de API de provedor, modelos padrão da instalação, provedores instalados na imagem.** Estão
  no `.env`, que é do host, com dono root e permissão 600, e mudar provedor exige reconstruir a
  imagem. O contêiner da API não lê o `.env` do host nem fala com o Docker, e não deve passar a
  falar: contêiner com socket do Docker é a VPS inteira (já está no `AGENTS.md`).
- **Atualizar a plataforma, subir e descer serviço, ver log de contêiner.** Mesma razão.
- Consequência: o wizard web configura **agentes**, não a **instalação**. Trocar chave da OpenAI
  continua sendo `asimov` no terminal.
- Saída possível no futuro, se incomodar: guardar chave de provedor no banco cifrada, como já é feito
  com credencial de canal, e deixar o `.env` só com o que a imagem precisa no boot. É mudança em
  `plataforma/config.py` e `ia/provedores.py`, de tamanho médio, e some com a necessidade de
  reiniciar a API para trocar chave.

## 6. O assistente de primeiro acesso

O pedido é que o primeiro acesso ao painel funcione como o setup, "até ficar funcional", e só depois
libere a dash.

**Como saber em que estado está, sem coluna nova:** o painel mostra o assistente enquanto a
instalação não tem nenhum agente ativo, e mostra a dash quando tem. Depois disso o assistente
continua acessível em "Novo agente". Nada de flag em banco, nada para dessincronizar.

**Etapas do assistente**, espelhando as telas 6 e 8 do terminal:

1. Empresa (no modo revenda, escolher ou criar; no modo empresa, uma só).
2. Canal: Chatwoot, WhatsApp oficial, WhatsApp pela WAHA ou nativo.
3. Dados do canal (é aqui que o custo varia muito, ver abaixo).
4. Nome, prompt inicial, ferramentas, emoji, buffer, mensagens por resposta, digitação.
5. Handoff: destino, template quando for o caso, horas de retomada.
6. Teste: a conversa de teste já existente, na mesma tela, com o turno mostrando modelo, custo e
   ferramentas usadas.
7. Pronto: mostra a URL do webhook e a URL da política de privacidade.

**O custo por canal, que é o que decide o recorte:**

| Canal | O que o assistente precisa fazer | Custo na web |
|---|---|---|
| Nativo | Nada externo | Trivial |
| Chatwoot | URL, token de administrador, escolher conta e caixa. Tudo já é `POST /admin/canais/chatwoot/descobrir` | Baixo |
| WAHA | Subir o contêiner sob demanda, criar sessão, desenhar QR, esperar parear, escolher destino entre números e grupos, tratar sessão caída. Hoje são 644 linhas de Bash | Alto |
| WhatsApp oficial | App, token permanente, chave secreta, descobrir contas, listar números e templates, apontar webhook no número, mostrar política de privacidade. Hoje são 380 linhas de Bash | Alto |

O caminho feliz dos dois canais de WhatsApp não é o problema; o caro é o que já foi aprendido a duras
penas e está no `AGENTS.md`: token que não enxerga a conta, app do caso de uso sem
`business_management`, `@lid`, nono dígito, sessão órfã, número que cai. Nada disso se reaproveita do
Bash, tudo isso precisa reaparecer na web em forma de mensagem que diz o que fazer.

**Por isso a recomendação de recorte**: a primeira versão do painel cobre nativo e Chatwoot, e para
WhatsApp mostra, com todas as letras, "rode `asimov novo-agente` na VPS para conectar um número".
Feio? É. Honesto e barato? Também. E o operador descobre, usando, se o wizard web de WhatsApp vale os
três a quatro dias que custa.

## 7. A dash de operação

Telas, em ordem de valor por esforço:

1. **Início**: saúde (API, banco, Redis, WAHA), agentes por canal, conversas ativas nas últimas 24
   horas, handoffs abertos, custo dos 7 dias, últimas falhas. Quase tudo já existe; só as conversas e
   os handoffs precisam de rota.
2. **Agentes**: ficha igual à do menu, com edição no lugar. Tudo pronto na API.
3. **Ferramentas**: lista de marcar por agente, com a descrição do catálogo. Pronto na API.
4. **Prompt**: editor de `persona.md` e `resumo_handoff.md`, com aviso de que vale no próximo turno.
   Rota nova, pequena.
5. **Conversas ativas**: lista com contato, canal, status, última mensagem, e a conversa aberta com o
   histórico. Rota nova, é o bloco médio.
6. **Handoff**: lista de conversa em atendimento humano, com botão de devolver ao agente
   (`POST .../retomar`, que já existe).
7. **Consumo**: por agente e período, com o que a API já devolve.
8. **Conversa de teste**: a mesma do terminal, com polling por HTMX.
9. **WhatsApp**: status do número, QR quando a WAHA pede, refazer webhook na Meta.

Sobre "sessões ativas", que tem três leituras possíveis e vale escolher antes de construir:

- Conversa em andamento (o mais provável): `Conversa` com `atualizado_em` recente e `status`.
- Número pareado na WAHA: já existe por agente.
- Sessão de login do painel: nasce com a autenticação.

## 8. Riscos

| Risco | Gravidade | O que faz com ele |
|---|---|---|
| Plano de controle na internet | **Alto** | Convite de uso único, Argon2id, sessão curta, CSRF, freio de tentativa, `basicauth` opcional no Caddy, e o modo túnel SSH sempre disponível |
| Conversa de contato visível no navegador | Médio | Decisão registrada, acesso só do operador, sem exportação e sem indexação |
| Duas telas para a mesma operação, uma envelhecendo | Médio | Regra nova: operação nasce na API, e menu e painel consomem. Nada de regra que exista só num dos dois |
| Certificado do `app.` falhar e travar a instalação | Médio | O painel é opcional e nunca bloqueia: falhou, o operador segue no terminal e liga depois com `asimov painel` |
| Wizard web de WhatsApp com menos tratamento de erro que o do terminal | Médio | O recorte da seção 6 evita o problema na primeira versão |
| Painel virar porta para o cliente final entrar | Alto se acontecer sem planejar | Fora de escopo explícito, com o custo anotado na seção 9 |
| Crescer para além do que uma VPS aguenta | Baixo | Polling de poucos segundos, com paginação e teto |

## 9. Fora de escopo proposto

- **Login do cliente final** (cada empresa vendo os próprios agentes). Custa papéis, permissão por
  cliente, convite, auditoria, recuperação de senha e revisão de toda consulta. Dobra o projeto e
  muda a natureza do produto. Se um dia entrar, entra depois, e é aí que `frontend/` e a spec de CRM
  fazem sentido.
- **Painel de atendente** (responder conversa pelo navegador). É Chatwoot, que já existe e já está
  integrado.
- **Administração de infraestrutura** pelo painel (seção 5.3).
- **Push, notificação e alarme por canal externo.** O aviso de número fora do ar já existe no menu.

## 10. Score de implementação

Escala: P vale até meio dia, M vale de um a dois dias, G vale de três a cinco dias. "Toca no que
existe" é o que importa para risco de regressão.

| # | Bloco | Esforço | Toca no que existe | Risco |
|---|---|---|---|---|
| 1 | Decisão, spec e regras novas em `AGENTS.md` | P | Documentação | Baixo |
| 2 | Caddy com `import` de extras, `painel.caddy` gerado, reload | P/M | `deploy/Caddyfile`, `docker-compose.yml` | Médio, mexe no que serve os webhooks |
| 3 | Setup: pergunta de administração, DNS do `app`, `asimov painel`, resumo e diagnóstico | M | `instalar.sh`, `dns.sh`, `final.sh`, `asimov.sh` | Médio |
| 4 | **Autenticação**: `UsuarioPainel`, migração, convite, sessão no Redis, CSRF, freio, telas de login e senha | **G** | Aditivo, mas cria a fronteira nova | **Alto** |
| 5 | Pacote `painel/`, layout, CSS, HTMX, navegação, tratamento de erro | M | Aditivo | Baixo |
| 6 | Dash de operação: início, agentes, ferramentas, consumo, falhas, conversa de teste | M/G | Aditivo | Baixo |
| 7 | Rotas novas de leitura: conversas, mensagens, handoffs, contatos, prompt, índice e isolamento | M/G | Aditivo, com teste de isolamento obrigatório | Médio |
| 8 | Assistente web para nativo e Chatwoot | M | Aditivo | Baixo |
| 9 | Assistente web para WAHA e WhatsApp oficial | **G** | Aditivo | Alto, muito caso de borda |
| 10 | Testes (pytest do painel, isolamento, 404 de `/admin` no host do painel) e `shellcheck` | M | `backend/testes/`, simulação de onboarding | Baixo |
| 11 | Documentação, `asimov atualizar` ciente do painel | P | `docs/`, `README.md` | Baixo |

**Totais**

| Recorte | Blocos | Trabalho focado |
|---|---|---|
| Painel completo, com wizard dos quatro canais | 1 a 11 | **13 a 18 dias** |
| **Recomendado**: sem o bloco 9 | 1 a 8, 10, 11 | **9 a 12 dias** |
| Mínimo defensável: túnel SSH, sem host público, sem login (caminho A) | 5, 6, 7 parcial, 10 | **4 a 6 dias** |

**Placar**

| Critério | Nota | Leitura |
|---|---|---|
| Viabilidade | **9/10** | A arquitetura foi desenhada para isto acontecer |
| Modificação pesada no backend existente | **2/10** | Nenhum `servico.py` ou `repo.py` de domínio muda. É quase todo aditivo |
| Modificação pesada na fronteira de segurança | **8/10** | O plano de controle deixa de ser local. É o trabalho de verdade |
| Esforço total | **7/10** | Duas a três semanas no recorte completo |
| Risco de regressão no que está no ar | **3/10** | Concentrado em Caddy e setup, ambos com reversão simples |
| Valor para o operador | **8/10** | Administração pelo celular, prompt editável sem SSH e conversas visíveis |
| Valor para o aluno que instala | **9/10** | "Abra `app.seudominio` e siga a tela" vence terminal de VPS com folga |

**Resposta direta à pergunta "vai ser necessária alguma modificação pesada":** no código que hoje faz
o agente funcionar, não. Em nenhum momento se mexe em turno, canais, mídia, handoff ou IA. O que é
pesado é o que não existe: login, sessão e exposição pública de administração, mais um bloco médio de
rotas de leitura de conversa. É trabalho grande e aditivo, e não perigoso para o que já está em
produção, desde que o painel nasça desligado por padrão.

## 11. Ordem sugerida

Como fase nova, depois da 6 e antes da 7 (a 7 é distribuição, e o painel muda o que se distribui).

**Fase 8.1: o painel existe e é seguro** (blocos 1 a 5, 10)
Aceite: `app.<dominio>` com certificado, convite de uso único no terminal, login, sessão, `/admin` e
`/webhook` respondendo 404 nesse host, painel mostrando agentes e consumo em modo leitura. Escolher
terminal na instalação não cria nada, e o `.env` fica igual ao de hoje.

**Fase 8.2: a dash opera** (blocos 6 e 7)
Aceite: ligar e desligar ferramenta, editar prompt, ver conversas ativas, abrir conversa, devolver
handoff, conversar de teste pelo navegador. Teste de isolamento passando.

**Fase 8.3: o assistente configura** (bloco 8, e o 9 só se o operador quiser)
Aceite: numa VPS nova, escolher painel na instalação, abrir o navegador com o código, criar empresa e
agente de Chatwoot e receber a primeira resposta sem voltar ao terminal.

## 12. Se for aprovado, o que muda na spec

- `spec/decisoes.md`: entrada com a data, o motivo e o recorte.
- `spec/visao.md`: função nova (administração pelo navegador) e ajuste do "fora de escopo" para
  separar painel do operador de front de CRM.
- `spec/usuarios.md`: papel do operador no painel, autenticação, sessão, convite.
- `spec/telas.md`: telas do painel e o fluxo de primeiro acesso com duas portas.
- `spec/dados.md`: `UsuarioPainel` e a sessão no Redis.
- `spec/arquitetura.md`: seções 1 (pastas), 3 (autenticação e o que o Caddy publica), 6 (contrato da
  API com as rotas de leitura) e a tabela de stack.
- `spec/fases.md`: Fase 8 com as três partes.
- `AGENTS.md`: a regra do `frontend/` vira regra do painel, mais a regra de operação nascer na API.

## 13. O que depende de decisão do operador

1. **Vale o preço?** Nove a doze dias no recorte recomendado, com a fronteira de segurança nova.
2. **Wizard web de WhatsApp na primeira versão, ou terminal?** É a diferença de quatro dias.
3. **`basicauth` do Caddy por cima do login?** Mais seguro, pior no celular.
4. **Conversa de contato visível no painel?** Contraria o cuidado que a v0.14.2 tomou com o log.
5. **`app` é o subdomínio, ou `painel`?** O pedido diz `app`, e pode ser pergunta no setup.
6. **Painel ligado por padrão nas instalações novas, ou sempre por escolha?** A recomendação é sempre
   por escolha, com o padrão no terminal, até rodar por um tempo numa VPS real.
