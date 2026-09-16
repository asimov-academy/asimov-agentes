# Etapa 5: Arquitetura e segurança

## Resumo para quem não é técnico

O projeto tem duas partes: o script de instalação, que roda no terminal da VPS e conversa com você, e a plataforma dos agentes, que fica no ar recebendo mensagens do WhatsApp, Telegram e Chatwoot. A plataforma usa uma base madura e já testada em agentes em produção (Python, PydanticAI, Postgres e Redis), só que preparada para vários clientes e agentes na mesma VPS. Cada cliente só enxerga o que é dele, e senhas e chaves ficam trancadas fora do código. Tudo roda em containers numa única VPS, com HTTPS automático e backup diário. No final, o projeto fica com `CLAUDE.md` e `AGENTS.md` para você continuar evoluindo em vibecoding.

## Ajustes de consistência

Encontrados ao cruzar spec/visao.md, spec/usuarios.md, spec/telas.md e spec/dados.md, e já corrigidos nesses arquivos:

1. **Modelo de embeddings estava por agente.** A dimensão do vetor é fixa na coluna do banco, então agentes com modelos diferentes quebrariam a busca. Passou para a Instalação.
2. **Função 17 (consumo e falhas) não tinha tela.** Adicionada a opção "Ver consumo e falhas" no menu e a operação correspondente na API.
3. **Aviso de handoff no WhatsApp direto.** Fora da janela de 24 horas a Meta só aceita template aprovado, e o número da empresa normalmente nunca falou com o bot. Adicionado `handoff_template` ao Agente de canal WhatsApp.
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
└── modelos/      modelos de CLAUDE.md, AGENTS.md e .env usados pelo setup
```

- O setup, antes da API existir, instala a VPS. Depois que ela sobe, toda criação, edição e consulta passa pela API. Ele nunca lê nem escreve no banco.
- O backend é uma API. Webhooks dos canais e o menu são só chamadas a ela.
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
| Execução | Docker Compose (`caddy`, `api`, `worker`, `postgres`, `redis`) | sobe e reinicia tudo com um comando; nada de Swarm numa VPS dedicada |
| Agente de código | Claude Code (instalador oficial) ou Codex (npm, com Node LTS) | escolha do operador |
| Testes | pytest + pytest-asyncio; `shellcheck` no Bash | cobre regras e isolamento; pega erro comum de script |

Modelos de IA:

- Um modelo por função, cada um com provedor próprio: resposta, fallback opcional, visão e transcrição. Provedores: OpenAI, Anthropic, Gemini e Groq (PydanticAI com `OpenAIChatModel`, `AnthropicModel`, `GoogleModel` e `GroqModel`).
- Fallback com `FallbackModel` da PydanticAI: erro de API do principal (fora do ar, limite, chave) passa para o segundo.
- Padrões da instalação no `.env` (`MODELO_*`), escolhidos no setup a partir da lista de modelos da API de cada provedor; cada agente grava os seus e pode trocar.
- Imagem Docker instala só os SDKs dos provedores usados (`PROVEDORES`).
- Embeddings (fase 6) ficam na Instalação, com OpenAI ou Gemini.

## 3. Autenticação e autorização

- **Operador:** entra por SSH. As rotas administrativas (`/admin/*`) exigem o header `X-Admin-Key` com a `chave_api_admin` gerada pelo setup, comparada em tempo constante. O Caddy não publica `/admin/*`; a API escuta em `127.0.0.1:8000` e só o menu, na própria VPS, chega nela.
- **Canais:** cada webhook entra por `https://bot.<dominio>/webhook/{canal}/{token_webhook}`. O `token_webhook` identifica o agente e, por ele, o cliente. Depois disso, a assinatura do canal é verificada com a credencial daquele agente:
  - WhatsApp: `GET` de verificação com `hub.verify_token`; `POST` com `X-Hub-Signature-256` (HMAC SHA-256 do corpo cru com o `app_secret`).
  - Telegram: `X-Telegram-Bot-Api-Secret-Token` igual ao `secret_token` registrado pelo setup.
  - Chatwoot: `X-Chatwoot-Signature` = HMAC SHA-256 de `"{X-Chatwoot-Timestamp}.{corpo cru}"` com o `bot_secret`.
- **Resposta a webhook inválido:** WhatsApp e Telegram recebem 401. Chatwoot recebe 200 com registro em Falha, porque qualquer resposta de erro faz o Chatwoot silenciar o bot naquela conversa. O único erro proposital ao Chatwoot é 500 quando não dá para enfileirar.
- **Atendente no canal direto:** mensagem vinda do número ou grupo em `handoff_destino` é tratada como comando, nunca como conversa de contato. `/retomar <código>` só é aceito se o código pertence a um handoff aberto do mesmo agente.
- **Atendente no Chatwoot:** autenticado pelo próprio Chatwoot. A retomada chega como `conversation_updated` com status `pending`, já verificada pela assinatura.
- **Isolamento:** o `cliente_id` nunca vem do corpo da requisição. Nos webhooks sai do `token_webhook`; nas rotas administrativas vem da URL e é conferido contra o banco. Todo repositório recebe `cliente_id` como parâmetro obrigatório e todo `SELECT`, `UPDATE` e `DELETE` filtra por ele. A busca vetorial filtra por `cliente_id` e `agente_id` no `WHERE` antes da ordenação por similaridade.

## 4. Proteção de dados

- **Credenciais de canal:** criptografadas com Fernet usando `CHAVE_CRIPTOGRAFIA` do `.env` antes de gravar; decifradas só na memória do processo que usa. Nunca aparecem em log, resposta da API ou tela do menu (o menu mostra só os 4 últimos caracteres).
- **`.env`:** gerado pelo setup, permissão 600, dono root, fora do git. O setup e a API recusam iniciar se ele estiver legível por outros.
- **Conteúdo de conversa:** logs em nível informativo registram ids e tipos, não o texto. Texto só em nível de depuração, desligado por padrão.
- **Mídia recebida:** baixada para `/var/lib/asimov/midia/<cliente>/<agente>/<hash>` em volume Docker, fora de qualquer rota pública. Limite de 20 MB por arquivo (conferido durante o download) e 5 minutos de áudio; acima disso, não processa, registra Falha e o agente pede para o contato escrever (handoff a partir da fase 3). O link do Chatwoot é baixado sem o token do bot.
- **Conteúdo de mídia é entrada hostil:** o texto extraído entra na conversa rotulado como dado do contato, nunca no prompt de sistema, e o turno que processa mídia roda sem tools que alteram estado, exceto handoff.
- **Documentos da base:** copiados para `/var/lib/asimov/conhecimento/<cliente>/<agente>/`.
- **Exclusão:** lógica em Cliente, Agente e Documento. Trechos de documento removido são apagados. Remover Agente apaga as credenciais e invalida o `token_webhook`. Job diário apaga do disco mídias com mais de 90 dias, mantendo `texto_extraido`.
- **Backup:** `deploy/backup.sh` com timer do systemd, diário às 3h: `pg_dump` em formato custom, `.env`, `prompts/` e a pasta de conhecimento, compactados em `/var/backups/asimov/`, retenção de 14 dias, cópia remota opcional via `rclone` se configurada. A mídia de contatos não entra no backup (tem retenção de 90 dias e o texto já está no banco).

## 5. Organização interna

```
backend/app/
├── plataforma/     config, banco, redis, log, criptografia, autenticação admin
├── clientes/       rotas.py, servico.py, repo.py, modelos.py
├── agentes/        rotas.py, servico.py, repo.py, modelos.py
├── canais/
│   ├── base.py     interface: verificar, normalizar entrada, enviar, digitando, baixar mídia, transferir
│   ├── whatsapp/
│   ├── telegram/
│   └── chatwoot/
├── conversas/      webhook, buffer, turno, divisão e envio de mensagens
├── ia/             fábrica de modelos por provedor, agente PydanticAI, tools padrão
├── midia/          download, cache por hash, transcrição, visão
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
- Cada canal implementa a mesma interface de `canais/base.py`; o resto do sistema não sabe qual canal está atendendo.
- Tools novas que o operador criar em vibecoding ficam em `ia/tools/` ou no assunto que elas tocam, e são registradas por agente.
- Por que assim: para mudar como o Telegram envia mensagem, mexe-se só em `canais/telegram/`; para trocar o provedor de IA, só em `ia/`. Nenhuma mudança num assunto obriga mexer em outro.

## 6. Contrato da API

Rotas administrativas: prefixo `/admin`, chamadas pelo menu, exigem `X-Admin-Key`.

| Operação | Rota | Recebe | Devolve | Regras |
|---|---|---|---|---|
| Verificar saúde | `GET /health` (pública) | nada | status de api, banco e redis | não expõe versões nem dados |
| Criar cliente | `POST /admin/clientes` | nome | cliente | slug único |
| Listar clientes | `GET /admin/clientes` | nada | lista | só não removidos |
| Criar agente | `POST /admin/clientes/{cliente_id}/agentes` | nome, canal, conexao (Chatwoot: url, token de administrador, conta, caixas), handoff_destino, handoff_template, modelos, buffer, retomada | agente com URL do webhook | cliente existe e ativo; canal conectado antes de gravar (Chatwoot: cria o Agent Bot com a URL do webhook e liga nas caixas; se a gravação falhar, apaga o bot); guarda só o token e o secret do bot; modelos só de provedores com chave; cria pasta e arquivos de prompt padrão; no Telegram registra o webhook |
| Listar agentes | `GET /admin/agentes?cliente_id=` | filtro opcional | lista com canal, destino de handoff, URL do webhook, ativo | credenciais nunca devolvidas |
| Ver agente | `GET /admin/clientes/{cliente_id}/agentes/{agente_id}` | ids | agente | agente pertence ao cliente |
| Editar agente | `PATCH /admin/clientes/{cliente_id}/agentes/{agente_id}` | campos alterados | agente | agente pertence ao cliente; credencial alterada é testada antes |
| Remover agente | `DELETE /admin/clientes/{cliente_id}/agentes/{agente_id}` | confirmação com o slug | ok | agente pertence ao cliente; remove webhook no Telegram; apaga credenciais |
| Listar empresas | `GET /admin/clientes` | nada | lista | usada pelo `asimov novo-agente` no modo revenda |
| Descobrir no canal | `POST /admin/canais/{canal}/descobrir` | acesso do operador (Chatwoot: url e token de administrador) | contas e caixas de entrada | não grava nada; acesso não é guardado |
| Enviar documento | `POST /admin/clientes/{cliente_id}/agentes/{agente_id}/documentos` | caminho do arquivo na VPS ou upload multipart | documento com status `processando` | formato aceito (PDF, DOCX, TXT, MD); hash repetido no mesmo agente é recusado; enfileira ingestão |
| Listar documentos | `GET .../agentes/{agente_id}/documentos` | ids | lista com status e trechos | agente pertence ao cliente |
| Remover documento | `DELETE .../documentos/{documento_id}` | ids | ok | documento pertence ao agente e ao cliente; apaga trechos |
| Ver consumo e falhas | `GET /admin/consumo?cliente_id=&agente_id=&dias=` | filtros | turnos, tokens, custo estimado, últimas falhas | filtro por cliente obrigatório quando informado |
| Retomar agente | `POST /admin/clientes/{cliente_id}/conversas/{conversa_id}/retomar` | ids | ok | conversa pertence ao cliente; fecha handoff aberto |

Webhooks, chamados pelos canais:

| Operação | Rota | Regras |
|---|---|---|
| Verificação da Meta | `GET /webhook/whatsapp/{token}` | `hub.verify_token` confere com o agente; devolve `hub.challenge` |
| Receber WhatsApp | `POST /webhook/whatsapp/{token}` | assinatura; agente ativo; deduplica pelo id da mensagem; mensagem do `handoff_destino` vira comando |
| Receber Telegram | `POST /webhook/telegram/{token}` | secret token; agente ativo; deduplica por `update_id`; mensagem do grupo de handoff vira comando |
| Receber Chatwoot | `POST /webhook/chatwoot/{token}` | HMAC; aceita só `message_created` de entrada e `conversation_updated`; inbox está em `inbox_ids`; deduplica por `X-Chatwoot-Delivery` |

Todo webhook valida, grava a mensagem, agenda o buffer e responde em menos de 1 segundo. Nenhum processamento de IA acontece dentro da requisição.

Tools padrão que todo agente recebe:

| Tool | O que faz | Regras |
|---|---|---|
| `buscar_base_conhecimento(pergunta)` | devolve os trechos mais próximos | só do agente e cliente do turno; sem base, devolve vazio |
| `transferir_para_humano(motivo)` | abre handoff, gera resumo com o modelo auxiliar, avisa e pausa | idempotente se já há handoff aberto |

## 7. Processamento em segundo plano

Worker arq, mesmo código do backend, container `worker`:

| Job | Disparo | O que faz |
|---|---|---|
| `processar_buffer` | cada mensagem de entrada reagenda o job da conversa para `agora + buffer_segundos` (job id fixo por conversa) | ao disparar, pega lock por conversa no Redis (TTL 240 s, cobre ler mídia e responder), junta as mensagens pendentes, roda mídia, chama o agente, registra Turno |
| `processar_midia` | chamado dentro do turno, antes do modelo (`midia/servico.py`) | baixa pelo canal, consulta cache por `cliente_id` + hash; se não houver, confere limites, transcreve ou lê, grava arquivo, Mídia e Turno da leitura; grava a `situacao` no anexo da mensagem |
| `enviar_resposta` | fim do turno | envia até `max_mensagens_por_resposta` mensagens com digitando antes de cada uma e espera proporcional ao tamanho (entre 1 e 4 s) |
| `ingerir_documento` | envio de documento | extrai texto, divide em trechos de cerca de 800 tokens com sobreposição de 100, gera embeddings em lote, marca `pronto` ou `erro` |
| `retomada_automatica` | cron a cada minuto | fecha handoffs com `retomar_em` vencido e avisa no destino que o agente voltou |
| `limpar_midia` | cron diário | apaga arquivos de mídia com mais de 90 dias |

Digitando por canal: WhatsApp pelo indicador de digitação da Cloud API junto da confirmação de leitura; Telegram `sendChatAction` repetido a cada 4 s durante o turno; Chatwoot `toggle_typing_status`.

Falha no turno (modelo fora do ar, erro de tool): até 2 novas tentativas; persistindo, mensagem curta de expectativa ao contato, registro em Falha e handoff. Nunca resposta inventada.

## 8. Segredos

- Tudo em `.env`, gerado pelo setup a partir de `modelos/env.example`. O repositório tem só `.env.example` com as chaves e nenhum valor.
- Variáveis: `DOMINIO_BASE`, `SUBDOMINIO_BOT`, `EMAIL_SSL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `CHAVE_API_ADMIN`, `CHAVE_CRIPTOGRAFIA`, `PROVEDOR_IA`, `PROVEDOR_APOIO`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `MODELO_EMBEDDINGS`, `LOG_NIVEL`.
- Senha do Postgres, `CHAVE_API_ADMIN` e `CHAVE_CRIPTOGRAFIA` são geradas pelo setup com `openssl rand`, nunca pedidas ao operador.
- Credenciais de canal não ficam no `.env`: ficam criptografadas no banco, por agente.
- Nunca no repositório: `.env`, dumps, backups, mídia, documentos de clientes, `.venv`. O `.gitignore` do projeto gerado já cobre tudo isso.
- Perder `CHAVE_CRIPTOGRAFIA` torna as credenciais ilegíveis: ela entra no backup e o resumo final avisa isso.

## 9. Hospedagem e publicação

- **Onde roda:** tudo numa VPS do operador com Ubuntu 24.04, mínimo 2 vCPU, 4 GB de RAM e 40 GB de disco (o setup recusa menos de 2 GB de RAM e 20 GB livres). Containers: `caddy` (80 e 443 públicas), `api` (127.0.0.1:8000), `worker`, `postgres` e `redis` sem porta pública.
- **Caminho do projeto:** `$HOME/asimov-agentes` do usuário que roda o setup (assumido). Estado do setup em `$HOME/.asimov/estado` (CHAVE=VALOR), log em `$HOME/.asimov/setup.log`.
- **Publicação na primeira instalação:** o próprio setup (tela 5) sobe com `docker compose up -d --build`, roda `alembic upgrade head` e confere `https://bot.<dominio>/health`.
- **Publicação depois de mudanças em vibecoding:** `deploy/publicar.sh` na raiz do projeto: roda `deploy/testar.sh`, build, migrações, sobe os serviços e faz health check. Migração nova com `deploy/nova_migracao.sh`. Todos usam `dc`, de `deploy/compose.sh`. É o que o `AGENTS.md` gerado manda o agente de código usar.
- **Script do setup:** o `install.sh` em `setup.<dominio>` é hospedado como página estática gratuita (GitHub Pages ou Cloudflare Pages) e baixa a release marcada do repositório da Asimov Academy.
- **DNS:** o setup compara o IP público da VPS com o `dig +short bot.<dominio>`. Se o IP for de faixa da Cloudflare, avisa para desligar o proxy (nuvem laranja) desse registro, porque o certificado é emitido na VPS.
- **Execução do setup:** idempotente. Cada passo checa se já está feito antes de fazer. Espera a trava do `apt` com `DPkg::Lock::Timeout`, repete falha passageira até 3 vezes com espera de 5, 15 e 45 s, e grava o passo concluído em `$HOME/.asimov/estado`.
- **Custo mensal estimado:** VPS de 4 GB nos provedores comuns, na faixa de R$ 30 a R$ 80 (estimativa, varia por provedor). Hospedagem do `install.sh`: gratuita. IA: por uso, visível no menu "Ver consumo e falhas". WhatsApp oficial: cobrança da Meta por conversa, conforme a tabela dela.

## 10. Testes mínimos

Automatizados desde a primeira fase (pytest, com Postgres e Redis reais em container):

- **Isolamento:** para cada repositório, dado de um cliente nunca aparece em consulta de outro; busca vetorial de um agente nunca devolve trecho de outro agente ou cliente; cache de mídia de um cliente não é reaproveitado por outro; rota admin com `agente_id` de outro cliente devolve 404.
- **Webhooks:** assinatura válida aceita e inválida recusada nos três canais, incluindo o formato `"{timestamp}.{corpo}"` do Chatwoot e o 200 em falha de assinatura; token de agente removido não processa; mensagem repetida não gera segunda resposta.
- **Buffer:** três mensagens dentro da janela geram um único turno.
- **Handoff:** conversa pausada não gera resposta; `/retomar` com código válido vindo do destino retoma; o mesmo comando vindo de outro número vira mensagem comum; retomada automática fecha no horário.
- **Divisão de mensagens:** nunca passa de `max_mensagens_por_resposta`.
- **Credenciais:** gravadas criptografadas; nunca aparecem em resposta da API nem em log.
- **Setup:** `shellcheck` sem erros em todos os scripts; funções de checagem (versão do Ubuntu, memória, DNS, estado de retomada) testadas isoladamente.

Manual, pelo operador:

- Rodar o setup numa VPS Ubuntu 24.04 vazia do começo ao fim, e rodar de novo para confirmar que abre o menu.
- Derrubar a conexão no meio da instalação e rodar de novo para confirmar a retomada.
- Mandar texto, áudio, imagem e PDF para um agente em cada canal e conferir resposta, digitando e divisão.
- Forçar um handoff em cada canal e retomar.
- Abrir o projeto no Claude Code e no Codex e confirmar que eles leem o `CLAUDE.md`/`AGENTS.md`.

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
