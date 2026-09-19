# Etapa 5: Arquitetura e segurança

## Resumo para quem não é técnico

O projeto tem duas partes: o script de instalação, que roda no terminal da VPS e conversa com você, e a plataforma dos agentes, que fica no ar recebendo mensagens do WhatsApp (oficial ou pela WAHA) e do Chatwoot, ou conversando com você no terminal. A plataforma usa uma base madura e já testada em agentes em produção (Python, PydanticAI, Postgres e Redis), só que preparada para vários clientes e agentes na mesma VPS. Cada cliente só enxerga o que é dele, e senhas e chaves ficam trancadas fora do código. Tudo roda em containers numa única VPS, com HTTPS automático e backup diário. No final, o projeto fica com `CLAUDE.md` e `AGENTS.md` para você continuar evoluindo em vibecoding.

## Ajustes de consistência

Encontrados ao cruzar spec/visao.md, spec/usuarios.md, spec/telas.md e spec/dados.md, e já corrigidos nesses arquivos:

1. **Modelo de embeddings estava por agente.** A dimensão do vetor é fixa na coluna do banco, então agentes com modelos diferentes quebrariam a busca. Passou para a Instalação.
2. **Função 17 (consumo e falhas) não tinha tela.** Adicionada a opção "Ver consumo e falhas" no menu e a operação correspondente na API.
3. **Aviso de handoff no WhatsApp direto.** Fora da janela de 24 horas a Meta só aceita template aprovado, e o número da empresa normalmente nunca falou com o bot. O aviso tenta texto livre e cai no template, que fica no `handoff_destino` do agente (v0.15.0).
4. **Comando de retomada sem formato.** Definido: o aviso leva um código curto e o atendente responde `/retomar <código>`. Adicionado `codigo` ao Handoff.
5. **Renovação de SSL listada como job agendado.** O proxy escolhido renova sozinho; removido dos jobs.
6. **Verificação do webhook do Chatwoot.** Além do token na URL, o Chatwoot assina com HMAC; incluído em spec/usuarios.md.
7. **Provedor de IA e geração de `AGENTS.md`/`CLAUDE.md`** pedidos depois da Etapa 4; incluídos em spec/visao.md (funções 4 e 18) e spec/telas.md (telas 3, 5 e 7).
8. **Firewall do script original abria a porta 8000.** A API fica só em localhost; o firewall abre apenas 22, 80 e 443.
9. **Princípio fixo de `frontend/` separado.** Não há front na primeira versão (spec/visao.md, Fora de escopo). O papel de cliente da API é do menu do setup, que só fala com a API. A pasta `frontend/` nasce quando o CRM entrar, consumindo a mesma API.

## 1. Separação das partes

```
asimov-agentes/
├── setup/        script de instalação e menu (cliente da API, papel de frontend)
├── backend/      API, worker e regras de negócio
├── prompts/      prompts de cada agente, versionados
├── deploy/       docker-compose, Caddyfile, backup
├── modelos/      modelos de CLAUDE.md, AGENTS.md e .env usados pelo setup
└── frontend/     painel do operador no navegador (spec/frontend.md)
```

- O setup, antes da API existir, instala a VPS. Depois que ela sobe, toda criação, edição e consulta passa pela API. Ele nunca lê nem escreve no banco.
- O backend é uma API. Webhooks dos canais e o menu são só chamadas a ela.
- O `frontend/` é o segundo cliente da API, pelas rotas `/painel/api`, com sessão de operador. Não conhece a `CHAVE_API_ADMIN` e não fala com `/admin`. Toda operação que ele faz existe também no menu do terminal: a regra é nascer na API e ser consumida pelos dois.
- Justificativa: quando o front de CRM chegar, ele usa exatamente as operações que o menu usa hoje, sem reescrever nada.

## 2. Stack

| Parte | Escolha | Por quê |
|---|---|---|
| Setup e menu | Bash para Ubuntu 24.04, com `curl`, `jq` e `dig` | roda numa VPS vazia sem instalar nada antes; mesmo formato do Setup Orion |
| Distribuição do setup | `setup.<dominio>` servindo um `install.sh` estático, que baixa a versão marcada (tag) do repositório e confere o checksum | um comando só, e cada aluno instala exatamente a mesma versão |
| Runtime | Python 3.12 + `uv` | instalação determinística e rápida |
| API | FastAPI + uvicorn | webhooks e rotas administrativas com validação tipada |
| Agente | PydanticAI | tools tipadas, saída estruturada e troca de provedor (OpenAI, Anthropic, Gemini) por configuração |
| Fila, buffer e agendamentos | arq + Redis 7 | assíncrono, cron no mesmo processo, poucas peças |
| Banco | PostgreSQL 16 + pgvector, SQLAlchemy 2.0, Alembic | um banco só para dados e vetores do RAG; Alembic permite evoluir o schema em vibecoding sem quebrar |
| Transcrição | endpoint de áudio da OpenAI ou da Groq (Whisper, `gpt-4o-transcribe`), ou áudio nativo do Gemini | segue o `modelo_transcricao` do agente; Anthropic não transcreve |
| Visão e documentos | modelo multimodal do `modelo_visao`; PDF com texto lido antes com `pypdf`, só o escaneado vai para a visão (10 primeiras páginas) | imagem e PDF escaneado sem OCR separado; PDF com texto sem custo de IA |
| Duração de áudio | `tinytag` (MIT), lido do cabeçalho do arquivo | confere o limite de 5 minutos sem ffmpeg na imagem |
| Embeddings | `text-embedding-3-small` (OpenAI) ou `gemini-embedding` (Gemini) | barato e suficiente; fixo na instalação |
| Leitura de documentos da base | `pypdf`, `python-docx`, texto puro | licenças permissivas, sem serviço externo |
| Criptografia de credenciais | `cryptography` (Fernet) | padrão simples e auditado |
| Logs | structlog em JSON | `cliente_id`, `agente_id` e `conversa_id` em todo evento |
| Proxy e HTTPS | Caddy | certificado Let's Encrypt e renovação automáticos, configuração de poucas linhas |
| WhatsApp não oficial | WAHA (`devlikeapro/waha`, Apache 2.0) com motor GOWS (whatsmeow), versão fixada, container `waha` subido só quando o primeiro agente WAHA é criado | leve, várias sessões numa instância, QR code e webhook assinado; manutenção do protocolo é do projeto WAHA; licença sem condições (Evolution e Baileys direto descartados, spec/decisoes.md) |
| Execução | Docker Compose (`caddy`, `api`, `worker`, `postgres`, `redis` e, sob demanda, `waha` e `copiloto`) | sobe e reinicia tudo com um comando; nada de Swarm numa VPS dedicada |
| Agente de código | Claude Code (instalador oficial) ou Codex (npm, com Node LTS) | escolha do operador; a mesma escolha move o copiloto do painel |
| Copiloto do painel | O CLI escolhido, em modo não interativo, num container `copiloto` com perfil, falando com a plataforma por um servidor MCP nosso (SDK `mcp`) | roda pela assinatura do operador, sem chave de API e sem custo por token; o CLI é o único motor que já sabe usar ferramenta e manter fio de conversa |
| Painel web | React 19 + TypeScript + Vite + Tailwind CSS, em `frontend/`, construído num estágio `node` do `backend/Dockerfile` e servido pela API em `/painel/app` | telas com abas e histórico de conversa pedem estado no cliente; sem container novo, sem node na VPS e sem estático de CDN |
| Testes | pytest + pytest-asyncio; `shellcheck` no Bash; vitest no `frontend/` | cobre regras e isolamento; pega erro comum de script |

Modelos de IA:

- Um modelo por função, cada um com provedor próprio: resposta, fallback opcional, visão e transcrição. Provedores: OpenAI, Anthropic, Gemini e Groq (PydanticAI com `OpenAIResponsesModel`, `AnthropicModel`, `GoogleModel` e `GroqModel`; OpenAI pela Responses porque só nela há busca na web nativa).
- Fallback com `FallbackModel` da PydanticAI: erro de API do principal (fora do ar, limite, chave) passa para o segundo.
- Modelo é escolha de cada agente, feita ao criá-lo no terminal ou no painel a partir da lista de modelos da API do provedor (`ia/chaves.py`, que também guarda o filtro por função e as sugestões). A instalação não pergunta nada de IA (v0.20.0); `MODELO_*` no `.env` só existe em instalação antiga e segue valendo de padrão.
- Chave de provedor fica cifrada no banco (`chave_provedor`), testada no provedor antes de guardar e nunca devolvida. API e worker releem as chaves antes de validar modelo e no começo do turno; `*_API_KEY` do `.env` antigo vale de reserva.
- Imagem Docker instala os SDKs dos quatro provedores (`PROVEDORES`, gravado pelo setup).
- Embeddings (fase 6) ficam na Instalação, com OpenAI ou Gemini.

## 3. Autenticação e autorização

- **Operador:** entra por SSH. As rotas administrativas (`/admin/*`) exigem o header `X-Admin-Key` com a `chave_api_admin` gerada pelo setup, comparada em tempo constante. O Caddy não publica `/admin/*`; a API escuta em `127.0.0.1:8000` e só o menu, na própria VPS, chega nela.
- **O painel é o segundo cliente da API, nunca do `/admin`.** As rotas `/painel/api/*` exigem a
  sessão do operador e, em toda escrita, o cabeçalho `X-Painel-CSRF`. Elas chamam os mesmos
  `servico.py` que o menu do terminal chama, então painel e terminal nunca divergem no que fazem.
  Nas rotas de um agente (`/painel/api/agentes/{id}`), o `cliente_id` sai da própria linha lida do
  banco, nunca do corpo; as rotas que criam recebem a empresa na URL, conferida antes de virar
  filtro. Nada que esteja cifrado no banco vira JSON: credencial de canal sai mascarada, o endereço
  do webhook só na ficha, e a falha sai como resumo curto, nunca com o corpo que o provedor
  respondeu (que já veio com chave de API dentro).
- **O copiloto entra pela mesma porta do painel.** As rotas `/painel/api/copiloto/*` exigem a
  sessão e o CSRF como qualquer outra. Ele não ganha credencial nem atalho: o CLI roda num
  contêiner sem porta publicada, alcança a plataforma só pelas ferramentas MCP, e a única
  escrita é a rota que o operador clica para confirmar uma proposta. Texto de prompt e de
  conversa chega ao modelo delimitado, como material, nunca como instrução.
- **Estático do painel, tudo da VPS.** O front construído é servido em `/painel/app`, com o
  `index.html` sem cache e os arquivos com hash no nome guardados para sempre. O `painel.css` das
  telas de login leva a versão no endereço, e as fontes saem de `/painel/fontes/<arquivo>`, de uma
  lista fechada de nomes. Nenhum CDN, em lugar nenhum.
- **Operador no painel (fase 8, opcional e desligado por padrão):** com `PAINEL_ATIVO`, o Caddy publica `app.<dominio>` e só o caminho `/painel/*`; `/admin*` e `/webhook*` respondem 404 nesse host. O painel não é cliente do `/admin` com a chave no navegador: é um caminho próprio que chama os mesmos serviços, então a regra de não publicar `/admin` continua valendo. Uma conta só (`usuario_painel`, com unicidade no banco), criada no primeiro acesso com um código de uso único que o `asimov painel` mostra no terminal; senha em scrypt, sessão no Redis com cookie `HttpOnly`, `Secure` e `SameSite=Strict`, origem conferida por host e freio de tentativa por IP. Chave de provedor entra pelo painel ou pelo terminal (v0.20.0): fica cifrada no banco e o navegador só fica sabendo que ela existe.
- **Canais:** cada webhook entra por `https://bot.<dominio>/webhook/{canal}/{token_webhook}`. O `token_webhook` identifica o agente e, por ele, o cliente. Depois disso, a assinatura do canal é verificada com a credencial daquele agente:
  - WhatsApp oficial: a API liga os webhooks do app (campo `messages`, com o token do app), inscreve a conta e aponta o endereço deste agente no número (`webhook_configuration`, o webhook override da Meta), em vez de usar a URL do app. O `GET` de verificação devolve `hub.challenge` quando `hub.verify_token` é igual ao `token_webhook` da URL: a Meta confere o endereço antes de o agente existir no banco, e quem sabe o token já sabe o segredo do webhook. O `POST` vem com `X-Hub-Signature-256` (HMAC SHA-256 do corpo cru com o `app_secret`), e corpo de outro `phone_number_id` é ignorado.
  - WAHA: não passa pelo Caddy. A WAHA chama `http://api:8000/webhook/waha/{token_webhook}` pela rede interna, com `X-Webhook-Hmac` = HMAC SHA-512 do corpo cru com a `hmac_key` do agente.
  - Nativo: sem webhook; o terminal chama as rotas administrativas de conversa.
  - Chatwoot: `X-Chatwoot-Signature` = HMAC SHA-256 de `"{X-Chatwoot-Timestamp}.{corpo cru}"` com o `bot_secret`.
- **Página pública de privacidade:** `GET /privacidade`, `GET /privacidade/{empresa}` e `GET /privacidade/{empresa}/{agente}` devolvem HTML a partir de `modelos/privacidade.html`, com nome da empresa, nome do agente, domínio, contato (o e-mail do SSL) e data. Três níveis porque na Meta existe um app por número, e cada app pede a própria URL; a do agente sai na API em `url_privacidade`. `GET /icone-app.png` serve `modelos/icone-app.png`, o outro arquivo que a Meta exige para publicar o app, para o operador baixar pelo navegador em vez de tirar da VPS com `scp`. É a única rota que devolve HTML e a única, fora de `/health` e `/webhook/*`, que o Caddy publica: a Meta exige URL de política de privacidade para o app do WhatsApp sair do modo de desenvolvimento, e a instalação já tem domínio com HTTPS. Slug que não existe responde 404, e não há listagem: quem não sabe o slug não descobre os clientes da instalação.
- **Resposta a webhook inválido:** WhatsApp oficial e WAHA recebem 401. Chatwoot recebe 200 com registro em Falha, porque qualquer resposta de erro faz o Chatwoot silenciar o bot naquela conversa. O único erro proposital ao Chatwoot é 500 quando não dá para enfileirar.
- **Id do número do handoff:** quem diz qual é o id de um número é o WhatsApp (`check-exists`), porque o mesmo celular circula com e sem o nono dígito e o id pode ser um `@lid`. O setup confere na escolha do destino; no envio, id que falha é resolvido e tentado uma vez, com a falha pedindo para trocar o destino no menu.
- **Número escondido (`@lid`):** o WhatsApp endereça a conversa por um id oculto. A conversa e o envio usam esse id; o telefone de verdade vem resolvido pela WAHA (`pn`, `_data.Info.SenderAlt` ou o participante) e fica no Contato, que é o que a lista de quem pode falar compara.
- **Quem o agente atende:** com `contatos_permitidos` preenchido, mensagem de contato fora da lista não vira conversa nem turno (fica só no log `webhook_ignorado`). A comparação ignora DDI, máscara e sufixo do canal: o mais curto tem de ser o fim do mais longo, com pelo menos 8 dígitos. Devolução de conversa e `/retomar` do destino do handoff passam sempre. Vale para qualquer canal.
- **Atendente no canal direto:** mensagem vinda do número ou grupo em `handoff_destino` é tratada como comando, nunca como conversa de contato. `/retomar <código>` também vale escrito do próprio número do agente, em qualquer conversa: quem escreve de lá é o operador. O código é opcional: na conversa do contato vale ela, e no chat do destino vale a única em atendimento; com mais de uma, o destino recebe a lista com um código por conversa. Código informado só é aceito se pertence a um handoff aberto do mesmo agente.
- **Atendente assumindo no Chatwoot:** mensagem `outgoing` que não é do bot pausa o agente (`Acao.PAUSAR`) e agenda `assumir_conversa` no worker, que deixa a conversa aberta e atribuída a quem escreveu. Vencido o `retomada_automatica_horas`, a conversa volta para pendente e sem atribuição antes de o handoff fechar; canal que recusa mantém o handoff aberto e a tentativa fica para dez minutos depois.
- **Fala de atendente na memória do agente:** mensagem de humano (atendente no Chatwoot, pessoa respondendo pelo aparelho na WAHA) entra no histórico do modelo como fala do assistente com o prefixo `(atendente da equipe)`, e um aviso do sistema antes da primeira delas explica que foi uma pessoa e que vale como combinado com o contato. Vale para todo canal com atendente; no terminal não existe.
- **Pessoa da equipe assumindo pelo aparelho (WAHA):** a sessão assina `message.any`, que traz também o que sai do número, com `source` (`api` é o agente falando, `app` é gente digitando no celular ou no WhatsApp Web). Mensagem `app` grava como fala de humano e abre handoff sem IA e sem aviso (`pausar_por_humano`), com o prazo de retomada do agente. Reagir com 👍 (`message.reaction` do próprio número) devolve a conversa ao agente, com `retomado_por: joinha`.
- **Atendente no Chatwoot:** autenticado pelo próprio Chatwoot. A retomada chega como `conversation_updated` com status `pending`, já verificada pela assinatura.
- **Isolamento:** o `cliente_id` nunca vem do corpo da requisição. Nos webhooks sai do `token_webhook`; nas rotas administrativas vem da URL e é conferido contra o banco. Todo repositório recebe `cliente_id` como parâmetro obrigatório e todo `SELECT`, `UPDATE` e `DELETE` filtra por ele. A busca vetorial filtra por `cliente_id` e `agente_id` no `WHERE` antes da ordenação por similaridade.

## 4. Proteção de dados

- **Token de administrador do Chatwoot:** pedido uma vez por URL e guardado criptografado com a mesma chave, fora das credenciais do agente (`acessos/`); o menu pode esquecê-lo. Quem tiver a VPS tem esse token, além dos tokens dos bots.
- **Credenciais de canal:** criptografadas com Fernet usando `CHAVE_CRIPTOGRAFIA` do `.env` antes de gravar; decifradas só na memória do processo que usa. Nunca aparecem em log, resposta da API ou tela do menu (o menu mostra só os 4 últimos caracteres).
- **`.env`:** gerado pelo setup, permissão 600, dono root, fora do git. Toda execução do setup confere a permissão e devolve para 600 com aviso se alguém afrouxou; a API não lê o arquivo (recebe as variáveis pelo `env_file` do Compose), então a promessa antiga de "recusar iniciar" valia só para o setup e virou conserto com aviso.
- **Conteúdo de conversa:** logs em nível informativo registram ids e tipos, não o texto. Texto só em nível de depuração, desligado por padrão.
- **Mídia recebida:** baixada para `/var/lib/asimov/midia/<cliente>/<agente>/<hash>` em volume Docker, fora de qualquer rota pública. Limite de 20 MB por arquivo (conferido durante o download) e 5 minutos de áudio; acima disso, não processa, registra Falha, o agente avisa e a conversa vai para humano. O link do Chatwoot é baixado sem o token do bot.
- **Conteúdo de mídia é entrada hostil:** o texto extraído entra na conversa rotulado como dado do contato, nunca no prompt de sistema, e o turno que processa mídia roda sem tools que alteram estado, exceto handoff.
- **Documentos da base:** copiados para `/var/lib/asimov/conhecimento/<cliente>/<agente>/`.
- **Exclusão:** lógica em Cliente, Agente e Documento. Trechos de documento removido são apagados. Remover Agente apaga as credenciais e invalida o `token_webhook`. Job diário apaga do disco o arquivo de mídia com mais de `MIDIA_HORAS_NO_DISCO` horas (24 por padrão, então na prática de um a dois dias), em lotes até esgotar, mantendo `texto_extraido`. Três retenções diferentes, de propósito: o **arquivo** dura um dia, o **texto extraído** fica com a conversa, e a **conversa** não é apagada.
- **Backup:** `deploy/backup.sh` com timer do systemd, diário às 3h: `pg_dump` em formato custom, `.env`, `prompts/` e a pasta de conhecimento, compactados em `/var/backups/asimov/`, retenção de 14 dias, cada peça só publicada depois de gravada inteira, cópia remota opcional via `rclone` se configurada. A mídia de contatos não entra no backup (tem retenção de 90 dias e o texto já está no banco).

## 5. Organização interna

```
backend/app/
├── plataforma/     config, banco, redis, log, criptografia, autenticação admin
├── acessos/        token de administrador do operador no canal, cifrado (da instalação, sem cliente_id)
├── clientes/       rotas.py, servico.py, repo.py, modelos.py
├── agentes/        rotas.py, servico.py, repo.py, modelos.py
├── canais/
│   ├── base.py     interface: conectar e desconectar, responder verificação de endereço, verificar assinatura, normalizar entrada, enviar, digitando, baixar mídia, transferir, devolver ao agente
│   ├── chatwoot/
│   ├── whatsapp/   Cloud API oficial
│   ├── waha/       WhatsApp não oficial
│   └── nativo/     conversa no terminal, sem canal externo
├── conversas/      webhook, buffer, turno, divisão e envio de mensagens
├── ia/             fábrica de modelos por provedor (provedores.py), agente PydanticAI (agente.py)
│   └── ferramentas/ uma ferramenta por arquivo (calculadora.py, busca_web.py), ficha em base.py, catálogo em registro.py
├── midia/          download, cache por hash, transcrição, visão
├── painel/         painel web do operador (fase 8)
│                   acesso.py (sessão, origem e CSRF), servico.py (senha, código, sessão e a
│                   composição da visão geral), repo.py (leituras do painel), canais.py (situação
│                   de cada canal), rotas.py (entrar, primeiro acesso, sair e o front),
│                   api.py + api_agentes.py + api_conversas.py (o JSON que o front consome),
│                   paginas/ (entrar e primeiro acesso em Jinja2), estaticos/ (painel.css, fontes/)
├── copiloto/       copiloto do painel: vinculo.py (a conta de IA que o setup registrou),
│                   sessao.py (conversa e propostas no Redis), servico.py (monta e roda o CLI),
│                   mcp.py (servidor MCP por stdio), aplicar.py (a escrita, no clique do operador),
│                   worker.py (fila e worker próprios)
│   └── ferramentas/ uma por arquivo, ficha em base.py, catálogo em registro.py
├── conhecimento/   ingestão, divisão em trechos, embeddings, busca, tool de busca
├── handoff/        tool de transferência, aviso, comando de retomada, retomada automática
├── consumo/        turnos, falhas, relatório por cliente
├── worker.py       definição do arq (jobs e crons)
└── main.py         monta a API
backend/testes/     espelha as pastas acima
backend/migrations/ Alembic
prompts/<cliente>/<agente>/persona.md
prompts/<cliente>/<agente>/resumo_handoff.md
```

- Em cada assunto: `rotas.py` só recebe e valida, `servico.py` tem a regra, `repo.py` fala com o banco. Rota nunca chama banco direto.
- Cada canal implementa a mesma interface de `canais/base.py`; o resto do sistema não sabe qual canal está atendendo. O que muda entre canais vira atributo ou método do contrato, nunca `if canal ==` fora de `canais/`: `webhook_interno` (WAHA chama a API pela rede do Compose), `agente_pode_falar(credenciais, conversa, status)` (o Chatwoot pergunta ao Chatwoot; o canal direto vale-se do status da conversa), `interpretar(payload, credenciais, destino)` (o destino do handoff é de onde vem o `/retomar`), `interpretar_todos` (um envelope pode trazer várias mensagens; o padrão devolve uma), `transferir(..., codigo)`, `avisa_destino` e `rotulo_da_conversa`.
- Ferramenta nova que o operador liga por agente é um arquivo próprio em `ia/ferramentas/` com a função e a ficha `FERRAMENTA` (nome igual ao do arquivo, rótulo, descrição, instrução de quando usar, se vem ligada), listada em `ia/ferramentas/registro.py`. Um teste falha se houver arquivo fora do registro. Tool que todo agente tem é registrada em `ia/agente.py`.
- O copiloto tem o mesmo desenho de ferramenta: um arquivo por ferramenta em `copiloto/ferramentas/`, ficha em `base.py`, catálogo em `registro.py`, com teste que recusa arquivo solto. A diferença é a regra dele: ferramenta de leitura responde na hora, ferramenta `propor_` só registra uma proposta, e a escrita acontece em `copiloto/aplicar.py`, chamado pela rota que o operador clica. O CLI roda sem as ferramentas de código dele, então o MCP é tudo o que ele alcança.
- Por que assim: para mudar como a WAHA envia mensagem, mexe-se só em `canais/waha/`; para trocar o provedor de IA, só em `ia/`. Nenhuma mudança num assunto obriga mexer em outro.

## 6. Contrato da API

Rotas administrativas: prefixo `/admin`, chamadas pelo menu, exigem `X-Admin-Key`.

| Operação | Rota | Recebe | Devolve | Regras |
|---|---|---|---|---|
| Verificar saúde | `GET /health` (pública) | nada | status de api, banco, redis e worker | não expõe versões nem dados; `worker` vem do pulso de minuto em minuto no Redis, e `aguardando` (instalação que ainda não viu o worker subir) não reprova |
| Criar cliente | `POST /admin/clientes` | nome | cliente | slug único |
| Listar clientes | `GET /admin/clientes` | nada | lista | só não removidos |
| Criar agente | `POST /admin/clientes/{cliente_id}/agentes` | nome, canal, conexao (Chatwoot: url, conta, caixas e token de administrador se não houver guardado), handoff_destino, handoff_template, modelos, buffer, retomada | agente com URL do webhook | cliente existe e ativo; canal conectado antes de gravar (Chatwoot: cria o Agent Bot com a URL do webhook, liga nas caixas e confere na caixa que o bot ficou; se não ficou ou a gravação falhar, apaga o bot); o agente guarda só o token e o secret do bot, e o token de administrador que funcionou vai para Acesso ao canal; sem token guardado nem informado, 428; modelos só de provedores com chave; cria pasta e arquivos de prompt padrão; na WAHA cria a sessão com o webhook interno; no nativo não conecta nada |
| Catálogo de ferramentas | `GET /admin/ferramentas` | nada | nome, rótulo, descrição e se é padrão | usado pelo menu |
| Listar agentes | `GET /admin/agentes?cliente_id=` | filtro opcional | lista com canal, destino de handoff, URL do webhook, ativo | credenciais nunca devolvidas |
| Ver agente | `GET /admin/clientes/{cliente_id}/agentes/{agente_id}` | ids | agente | agente pertence ao cliente |
| Editar agente | `PATCH /admin/clientes/{cliente_id}/agentes/{agente_id}` | só os campos alterados: nome, handoff_destino, buffer_segundos, max_mensagens_por_resposta, retomada_automatica_horas, digitacao_caracteres_por_segundo e digitacao_maximo_segundos (1 a 30), ferramentas (nomes do catálogo), modelo_conversa, modelo_fallback, modelo_auxiliar, modelo_visao, modelo_transcricao; `null` esvazia fallback, destino e retomada; nome novo vai ao canal com o token guardado ou informado em conexao (428 sem token), ou só na plataforma com `renomear_no_canal: false` | agente | agente pertence ao cliente; campo fora da lista é recusado; destino validado pelo canal; modelos só de provedores com chave; retomada por tempo só em canal que retoma por tempo; slug e pasta de prompts não mudam; credencial de canal editável entra com a fase 5 |
| Remover agente | `DELETE /admin/clientes/{cliente_id}/agentes/{agente_id}` | confirmacao (nome do agente), conexao opcional (token_admin) e desconectar_canal (padrão true) | removido e canal_desconectado | agente pertence ao cliente; desfaz no canal antes com o token guardado ou informado (Chatwoot apaga o Agent Bot; 428 sem token) e, se o canal recusar, não remove; `desconectar_canal: false` remove sem mexer no canal; exclusão lógica: webhook invalidado, credenciais apagadas, slug liberado; na WAHA faz logout e apaga a sessão |
| Remover empresa | `DELETE /admin/clientes/{cliente_id}` | confirmacao (nome da empresa) | nada (204) | só sem agentes (409); exclusão lógica com slug liberado |
| Listar empresas | `GET /admin/clientes` | nada | lista | usada pelo `asimov novo-agente` no modo revenda |
| Descobrir no canal | `POST /admin/canais/{canal}/descobrir` | acesso do operador (Chatwoot: url e, se não houver guardado, token de administrador) | contas, caixas de entrada, atendentes e times | grava só o token novo que funcionou; sem token, ou com o guardado recusado (que é apagado), 428 |
| Ver tokens guardados | `GET /admin/canais/{canal}/acessos` | nada | endereços e data | o token nunca sai |
| Esquecer token | `DELETE /admin/canais/{canal}/acessos?endereco=` | endereço | nada (204) | 404 se não havia |
| Enviar documento | `POST /admin/clientes/{cliente_id}/agentes/{agente_id}/documentos` | caminho do arquivo na VPS ou upload multipart | documento com status `processando` | formato aceito (PDF, DOCX, TXT, MD); hash repetido no mesmo agente é recusado; enfileira ingestão |
| Listar documentos | `GET .../agentes/{agente_id}/documentos` | ids | lista com status e trechos | agente pertence ao cliente |
| Remover documento | `DELETE .../documentos/{documento_id}` | ids | ok | documento pertence ao agente e ao cliente; apaga trechos |
| Sessão WAHA | `GET /admin/clientes/{cliente_id}/agentes/{agente_id}/waha` | ids | status (`STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED`, `STOPPED`), pareado, número e QR code em texto quando aguardando | agente WAHA do cliente; o menu desenha o QR no terminal até `WORKING`; WAHA fora do ar devolve 502 |
| Reiniciar sessão WAHA | `POST /admin/clientes/{cliente_id}/agentes/{agente_id}/waha/reiniciar` | ids | mesma saída da consulta | para e inicia a sessão para vir um QR code novo (depois de `FAILED` ou para trocar de número) |
| Grupos da WAHA | `GET /admin/clientes/{cliente_id}/agentes/{agente_id}/waha/grupos` | ids | grupos do número (chat_id e nome) | para escolher o destino do handoff; número ainda não pareado devolve lista vazia |
| Conversar no terminal | `POST /admin/clientes/{cliente_id}/agentes/{agente_id}/terminal` | texto (1 a 4000) e conversa (vazia começa uma nova) | conversa, conversa_id (para retomar) e agendada (false com handoff aberto: grava e o agente não responde) | agente ativo do cliente, de qualquer canal: a conversa é criada no canal nativo e a resposta não passa pelo canal do agente; conversa informada precisa ser desse agente e do nativo (404: nunca escreve em conversa real do canal); grava a mensagem e agenda o buffer, como um webhook |
| Ler conversa do terminal | `GET /admin/clientes/{cliente_id}/agentes/{agente_id}/terminal/{conversa}?depois=` | ids e `depois` (quantas mensagens do agente o terminal já mostrou) | mensagens do agente depois dessa posição, próxima posição, digitando, respondendo (turno em andamento), último turno de resposta (modelo, latência, tokens, custo, ferramentas, erro) e handoff aberto (motivo, resumo, código) | conversa do terminal desse agente e cliente; o lock do turno é lido antes das mensagens: respondendo falso garante que resposta, turno e handoff já estão gravados |
| Conectar agente a um canal | `POST /admin/clientes/{cliente_id}/agentes/{agente_id}/canal` | canal, conexao (como na criação) e handoff_destino | agente | agente ativo do cliente num canal que não é externo (nativo), senão 409; canal novo externo, senão 422; conecta com o mesmo token do webhook e grava credenciais e destino; sem token guardado nem informado, 428; se gravar falhar, desfaz a conexão; prompt, modelos, ajustes e conversas ficam |
| Ver consumo e falhas | `GET /admin/consumo?cliente_id=&agente_id=&dias=` | filtros; `dias` de 1 a 365, padrão 7 | por agente: turnos (resposta), chamadas, tokens, custo estimado e chamadas sem preço; até 10 últimas falhas | cliente informado é conferido no banco; `agente_id` exige `cliente_id`; sem cliente, a instalação inteira |
| Retomar agente | `POST /admin/clientes/{cliente_id}/conversas/{conversa_id}/retomar` | ids | retomado (false se não havia handoff aberto) | conversa pertence ao cliente; o canal devolve a conversa ao agente antes (Chatwoot: status pendente) e, se recusar, 502 sem fechar; `retomado_por` `operador` |

Webhooks, chamados pelos canais:

| Operação | Rota | Regras |
|---|---|---|
| Verificação do endereço | `GET /webhook/{canal}/{token}` | só o WhatsApp oficial responde: `hub.verify_token` igual ao token da URL devolve `hub.challenge`. Nos outros canais, 404 |
| Receber WhatsApp | `POST /webhook/whatsapp/{token}` | assinatura; agente ativo; corpo de outro `phone_number_id` ignorado; recibo de entrega ignorado; deduplica pelo id da mensagem; mensagem do `handoff_destino` vira comando (`/retomar` ou 👍 no aviso) |
| Refazer o webhook na Meta | `POST /admin/clientes/{c}/agentes/{a}/whatsapp/webhook` | refaz as três camadas com as credenciais guardadas; idempotente |
| Receber WAHA | `POST /webhook/waha/{token}` (rede interna) | HMAC SHA-512; agente ativo; aceita `message` e `session.status`; ignora `fromMe` e grupos, exceto o grupo de handoff; deduplica pelo id da mensagem; mensagem do `handoff_destino` vira comando |
| Receber Chatwoot | `POST /webhook/chatwoot/{token}` | HMAC; aceita só `message_created`, `conversation_status_changed` e `conversation_updated`; vale qualquer caixa em que o bot esteja ligado (o Chatwoot só chama o bot a partir delas e a assinatura prova o bot); deduplica mensagem pelo id; mudança de status para `pending` fecha o handoff aberto (idempotente) |

Todo webhook valida, grava a mensagem, agenda o buffer e responde em menos de 1 segundo. Nenhum processamento de IA acontece dentro da requisição.

Ferramentas opcionais por agente (`ia/ferramentas/`, uma por arquivo; campo `ferramentas`; agente novo nasce só com as marcadas na criação, nenhuma por padrão):

| Ferramenta | O que faz | Regras |
|---|---|---|
| `calculadora` (`calcular(expressao)`, `ia/ferramentas/calculadora.py`) | toda conta do agente: o modelo nunca calcula sozinho | lida pela árvore sintática (nunca `eval`); números no formato brasileiro e argumentos separados por `;`; operadores, `^`, `15%`, funções de uma lista fechada (raiz, arredonda meio para cima, min, max, soma, media, log, trigonometria, fatorial, porcentagem, variação, juros compostos, parcela pela Price, hoje, dias_entre, soma_dias) e datas "dd/mm/aaaa"; expoente até 100 e resultado até 14 mil bits; erro volta ao modelo em português para ele corrigir |
| `busca_web` (`ia/ferramentas/busca_web.py`) | pesquisa na internet | capability `WebSearch` da PydanticAI: busca nativa do provedor quando o modelo tem (OpenAI Responses, Anthropic, Gemini, Groq `compound`), DuckDuckGo quando não tem; resultado é dado de terceiros, nunca instrução |

Tools padrão que todo agente recebe:

| Tool | O que faz | Regras |
|---|---|---|
| `buscar_base_conhecimento(pergunta)` | devolve os trechos mais próximos | só do agente e cliente do turno; sem base, devolve vazio |
| `transferir_para_humano(motivo)` | registra o pedido; no fim do turno, depois de enviar a resposta, gera resumo com o modelo auxiliar e transfere no canal (Chatwoot: nota privada, atribuição ao destino, status aberto) | idempotente se já há handoff aberto; resposta descartada por mensagem nova descarta o pedido junto |

## 7. Processamento em segundo plano

Worker arq, mesmo código do backend, container `worker`:

| Job | Disparo | O que faz |
|---|---|---|
| `processar_buffer` | cada mensagem de entrada reagenda o job da conversa para `agora + buffer_segundos` (job id fixo por conversa) | ao disparar, pega lock por conversa no Redis (TTL 240 s, cobre ler mídia e responder), junta as mensagens pendentes, roda mídia, chama o agente, registra Turno |
| `processar_midia` | chamado dentro do turno, antes do modelo (`midia/servico.py`) | baixa pelo canal, consulta cache por `cliente_id` + hash; se não houver, confere limites, transcreve ou lê, grava arquivo, Mídia e Turno da leitura; grava a `situacao` no anexo da mensagem |
| `enviar_resposta` | fim do turno | envia até `max_mensagens_por_resposta` mensagens com digitando antes de cada uma pelo tempo de uma pessoa digitar: caracteres / `digitacao_caracteres_por_segundo`, variação de 15%, entre 1 s e `digitacao_maximo_segundos`; o tempo que o turno já levou conta na primeira; soma limitada a 90 s (abaixo do lock) |
| `ingerir_documento` | envio de documento | extrai texto, divide em trechos de cerca de 800 tokens com sobreposição de 100, gera embeddings em lote, marca `pronto` ou `erro` |
| `confere_whatsapp` | cron a cada dez minutos | confere se os números dos agentes WAHA continuam pareados; fora do ar vira Falha, uma por agente por hora |
| `retomada_automatica` | cron a cada minuto | fecha handoffs com `retomar_em` vencido e avisa no destino que o agente voltou |
| `turno_do_copiloto` | pedido do operador no painel | executa o CLI no container `copiloto`, que lê a plataforma pelas ferramentas MCP e registra propostas; a resposta e o andamento ficam no Redis, e o painel acompanha por polling. Fila e worker próprios (`app/copiloto/worker.py`): um turno de atendimento precisa ser rápido, um turno de copiloto pensa por minutos |
| `limpar_midia` | cron diário, de madrugada | apaga do disco o arquivo de mídia com mais de `midia_horas_no_disco` (24); com a varredura diária ele dura de um a dois dias. O texto lido fica, e o hash mantém o cache valendo |

Fora do worker, no host: `asimov-waha.timer` (systemd, domingo de madrugada) roda `deploy/atualiza_waha.sh`, que atualiza a imagem da WAHA e volta para a anterior se algum número não reconectar. Fica no host porque atualizar contêiner pede o Docker, e dar o socket do Docker a um contêiner é dar a VPS inteira.

Digitando por canal: WhatsApp oficial pelo indicador da Cloud API junto da confirmação de leitura, preso ao id da última mensagem recebida (some ao responder ou em 25 s); WAHA `startTyping`/`stopTyping` e `sendSeen`; nativo guarda o digitando no Redis para o terminal mostrar; Chatwoot `toggle_typing_status`.

Falha no turno (modelo fora do ar, erro de tool): até 2 novas tentativas; persistindo, mensagem curta de expectativa ao contato, registro em Falha e handoff. Nunca resposta inventada.

## 8. Segredos

- Tudo em `.env`, gerado pelo setup. O repositório tem só `.env.example` com as chaves e nenhum valor.
- Variáveis: `MODO_INSTALACAO`, `DOMINIO_BASE`, `SUBDOMINIO_BOT`, `EMAIL_SSL`, `AGENTE_CODIGO`, `IA_VINCULADA`, `IA_CLI`, `IA_CONTA`, `CREDENCIAL_IA_HOST`, `CREDENCIAL_IA_CONTAINER`, `COPILOTO_ATIVO`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `CHAVE_API_ADMIN`, `CHAVE_CRIPTOGRAFIA`, `MODELO_CONVERSA`, `MODELO_FALLBACK`, `MODELO_VISAO`, `MODELO_TRANSCRICAO`, `IDIOMA_AUDIO` (desde a v0.14.1), `OPENAI_RACIOCINIO` (desde a v0.8.5), `PROVEDORES`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `LOG_NIVEL`, `WAHA_API_KEY` e `VERSAO_WAHA` (as duas nascem na instalação, junto do contêiner da WAHA). Entra depois: `MODELO_EMBEDDINGS` (fase 6).
- Senha do Postgres, `CHAVE_API_ADMIN` e `CHAVE_CRIPTOGRAFIA` são geradas pelo setup com `openssl rand`, nunca pedidas ao operador.
- A credencial da conta de IA do operador não entra nem no `.env` nem no banco: ela fica onde o CLI oficial guarda (`~/.claude/.credentials.json` ou `~/.codex/auth.json`, com a permissão dele), e só o container do copiloto monta essa pasta. O `.env` registra apenas que existe vínculo, com qual CLI, em que conta e onde fica a pasta.
- Credenciais de canal não ficam no `.env`: ficam criptografadas no banco, por agente. Chave de provedor de IA também fica no banco, cifrada, uma por provedor (v0.20.0); `MODELO_*` e `*_API_KEY` só aparecem preenchidos em instalação feita até a v0.19. O token de administrador do Chatwoot também fica no banco, cifrado, em `acessos/`.
- Nunca no repositório: `.env`, dumps, backups, mídia, documentos de clientes, `.venv`. O `.gitignore` do projeto gerado já cobre tudo isso.
- Perder `CHAVE_CRIPTOGRAFIA` torna as credenciais ilegíveis: ela entra no backup e o resumo final avisa isso.

## 9. Hospedagem e publicação

- **Onde roda:** tudo numa VPS do operador com Ubuntu 24.04, mínimo 2 vCPU, 4 GB de RAM e 40 GB de disco (o setup recusa menos de 2 GB de RAM e 20 GB livres). Containers: `caddy` (80 e 443 públicas), `api` (127.0.0.1:8000), `worker`, `postgres` e `redis` sem porta pública, mais `waha` e `copiloto` sob demanda, também sem porta.
- **Caminho do projeto:** `$HOME/asimov-agentes` do usuário que roda o setup (assumido). Estado do setup em `$HOME/.asimov/estado` (CHAVE=VALOR), log em `$HOME/.asimov/setup.log`.
- **Publicação na primeira instalação:** o próprio setup (tela 5) sobe com `docker compose up -d --build`, roda `alembic upgrade head` e confere `https://bot.<dominio>/health`.
- **Publicação depois de mudanças em vibecoding:** `deploy/publicar.sh` na raiz do projeto: roda `deploy/testar.sh`, build, migrações, sobe os serviços e faz health check. Migração nova com `deploy/nova_migracao.sh`. Todos usam `dc`, de `deploy/compose.sh`. É o que o `AGENTS.md` gerado manda o agente de código usar.
- **Script do setup:** o `install.sh` em `setup.<dominio>` é hospedado como página estática gratuita (GitHub Pages ou Cloudflare Pages) e baixa a release marcada do repositório da Asimov Academy.
- **DNS:** o setup compara o IP público da VPS com o `dig +short bot.<dominio>`. Se o IP for de faixa da Cloudflare, avisa para desligar o proxy (nuvem laranja) desse registro, porque o certificado é emitido na VPS.
- **Execução do setup:** idempotente. Cada passo checa se já está feito antes de fazer. Espera a trava do `apt` com `DPkg::Lock::Timeout`, repete falha passageira até 3 vezes com espera de 5, 15 e 45 s, e grava o passo concluído em `$HOME/.asimov/estado`.
- **Custo mensal estimado:** VPS de 4 GB nos provedores comuns, na faixa de R$ 30 a R$ 80 (estimativa, varia por provedor). Hospedagem do `install.sh`: gratuita. IA: por uso, visível no menu "Ver consumo e falhas". WhatsApp oficial: cobrança da Meta por mensagem, conforme a tabela dela. Desde 1º de outubro de 2026 a resposta dentro da janela de 24 horas (mensagem de serviço, que é o que o agente manda) também é cobrada, depois de 1.000 grátis por número por mês; conta sem forma de pagamento não tem essas mensagens entregues. Ver `docs/whatsapp-oficial.md`.

## 10. Testes mínimos

Automatizados desde a primeira fase (pytest, com Postgres e Redis reais em container):

- **Isolamento:** para cada repositório, dado de um cliente nunca aparece em consulta de outro; busca vetorial de um agente nunca devolve trecho de outro agente ou cliente; cache de mídia de um cliente não é reaproveitado por outro; rota admin com `agente_id` de outro cliente devolve 404.
- **Webhooks:** assinatura válida aceita e inválida recusada nos três canais, incluindo o formato `"{timestamp}.{corpo}"` do Chatwoot e o 200 em falha de assinatura; token de agente removido não processa; mensagem repetida não gera segunda resposta.
- **Buffer:** três mensagens dentro da janela geram um único turno.
- **Handoff:** conversa pausada não gera resposta; `/retomar` com código válido vindo do destino retoma; o mesmo comando vindo de outro número vira mensagem comum; retomada automática fecha no horário.
- **Divisão de mensagens:** nunca passa de `max_mensagens_por_resposta`.
- **Credenciais:** gravadas criptografadas; nunca aparecem em resposta da API nem em log.
- **Setup:** `shellcheck` sem erros em todos os scripts; funções de checagem (versão do Ubuntu, memória, DNS, estado de retomada) testadas isoladamente; `setup/testes/simula_onboarding.sh` percorre o onboarding inteiro com a API e o Docker falsos.
- **Copiloto:** nenhuma ferramenta do modelo escreve na plataforma (propor registra proposta e para aí); a escrita só acontece na rota que o operador clica; o comando do CLI sai sem as ferramentas de código dele; o registro de ferramentas recusa arquivo solto na pasta.

Manual, pelo operador:

- Rodar o setup numa VPS Ubuntu 24.04 vazia do começo ao fim, e rodar de novo para confirmar que abre o menu.
- Derrubar a conexão no meio da instalação e rodar de novo para confirmar a retomada.
- Mandar texto, áudio, imagem e PDF para um agente em cada canal e conferir resposta, digitando e divisão.
- Forçar um handoff em cada canal e retomar.
- Abrir o projeto no Claude Code e no Codex e confirmar que eles leem o `CLAUDE.md`/`AGENTS.md`.
- Vincular a conta de IA na instalação, pedir uma mudança ao copiloto do painel, confirmar a proposta e conferir no terminal que ela valeu.

## 11. Arquivos de contexto do projeto gerado

Decisão tomada a partir do guia de boas práticas de AGENTS.md e CLAUDE.md trazido pelo operador (2025 e 2026).

- **Fonte única:** `AGENTS.md` na raiz é o arquivo canônico (lido por Codex, Cursor e outros). `CLAUDE.md` tem uma linha só: `@AGENTS.md`. Por quê: o Claude Code carrega `CLAUDE.md` e resolve o import; duas cópias divergem na primeira edição.
- **Gerado a partir de modelo fixo:** `modelos/AGENTS.md.tmpl`, escrito à mão e revisado a cada versão do setup. O setup só preenche variáveis (provedor de IA, agente de código, canais habilitados, caminho do log). Nenhum trecho é gerado por LLM na instalação. Por quê: arquivo de contexto gerado por LLM tende a repetir o que o código já mostra, custa mais tokens e piora o resultado.
- **Tamanho:** alvo de até 100 linhas, limite duro de 200. Teste de cada linha: "sem esta linha, o agente de código erraria?". Se não, sai.
- **Só o que não é descobrível lendo o código:**
  - comandos exatos: rodar todos os testes, rodar um teste, criar migração, publicar (`deploy/publicar.sh`), ver logs do worker e da api
  - onde criar uma tool nova e como registrar num agente; onde fica o prompt de cada agente
  - gotchas: resposta 200 ao Chatwoot em assinatura inválida; buffer por job id fixo; embeddings fixos na instalação; conteúdo de mídia nunca no prompt de sistema
  - proibições em forma imperativa: NUNCA consultar o banco sem `cliente_id`; NUNCA ler, imprimir ou commitar `.env`; NUNCA editar migração já aplicada, sempre criar nova; NUNCA rodar `docker compose down -v`; NUNCA publicar `/admin` no Caddy; NUNCA colocar chave, token ou número de telefone em código ou prompt
  - regra de trabalho: publicar só com testes passando
  - regra de evolução: quando o operador corrigir o agente de código duas vezes pela mesma coisa, adicionar uma linha a este arquivo
- **Fica de fora:** visão geral do projeto em prosa, árvore de pastas, descrição arquivo por arquivo, convenções padrão de Python, lista de agentes e clientes (muda sempre), domínio, IPs e qualquer segredo.
- **Arquivos aninhados:** não na primeira versão. O `AGENTS.md` gerado orienta: se passar de 200 linhas, mover regras específicas para `backend/AGENTS.md` ou `setup/AGENTS.md`, que valem só naquela pasta.
- **Limite de garantia:** esses arquivos orientam, não impedem. O que não pode acontecer de jeito nenhum também é garantido por teste (isolamento por cliente), `.gitignore` (`.env`) e pelo próprio `publicar.sh` (bloqueia publicação com teste falhando).
