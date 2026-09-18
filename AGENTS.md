# Asimov Academy: setup de agentes de atendimento

`spec/` é a fonte de verdade. Leia antes de construir e atualize quando uma decisão mudar.

**Comece por `spec/estado.md`**: versão publicada, fase atual, próximos passos e fluxo de publicação.

Fale com o operador em português, curto e direto.

## Quando ler cada arquivo

- `spec/estado.md`: onde o projeto está. Sempre primeiro; atualize ao publicar.
- `spec/visao.md`: funções da primeira versão e fora de escopo. Antes de qualquer fase.
- `spec/usuarios.md`: papéis, verificação de webhooks, isolamento por cliente. Antes de tocar em autenticação, autorização ou consultas.
- `spec/telas.md`: telas do setup e do menu, fluxos. Antes de construir tela ou operação da API.
- `spec/dados.md`: entidades, atributos, agente de exemplo. Antes de tocar em banco ou modelos.
- `spec/arquitetura.md`: stack, pastas, contrato da API, segurança, hospedagem, regras do `AGENTS.md` gerado. Antes de criar estrutura ou adicionar dependência.
- `spec/frontend.md`: telas do painel web, design system, contrato `/painel/api` e etapas. Antes de tocar em `frontend/` ou `backend/app/painel/`.
- `spec/fases.md`: ordem e critério de aceite. No início de cada fase.
- `spec/decisoes.md`: log de mudanças. Antes de assumir que a spec está atual; escreva sempre que mudar algo.

## Stack

- Setup e comando `asimov`: Bash para Ubuntu 24.04 (`curl`, `jq`, `dig`).
- Backend: Python 3.12, `uv`, FastAPI, PydanticAI (OpenAI pela Responses, Anthropic, Gemini, Groq, FallbackModel, `WebSearch` com DuckDuckGo local), arq.
- Dados: PostgreSQL 16 com pgvector, SQLAlchemy 2.0, Alembic, Redis 7.
- Execução: Docker Compose com Caddy. WAHA (WhatsApp) em perfil, sobe sob demanda; `qrencode` desenha o QR no terminal.
- Testes: pytest com Postgres e Redis reais em container; `shellcheck`.

## Comandos de desenvolvimento

- Testes locais do backend (Postgres com banco `asimov_teste` e Redis em `localhost:6390`): `redis-server --port 6390 --daemonize yes --save "" && cd backend && uv run pytest -q`. Outros endereços: `TESTE_DATABASE_URL` e `TESTE_REDIS_URL`.
- Shellcheck: `uvx --from shellcheck-py shellcheck -x -P SCRIPTDIR setup/instalar.sh setup/asimov.sh setup/install.sh setup/lib/*.sh deploy/*.sh`
- Painel web: `cd frontend && npm ci` uma vez; depois `npm run build`, `npm run teste` e `npm run checa`. Para ver no navegador sem Docker, construa e copie: `npm run build && rm -rf ../backend/app/painel/estaticos/app && cp -R dist ../backend/app/painel/estaticos/app`.
- Simular o onboarding sem VPS: `ASIMOV_TTY=setup/testes/respostas.txt bash setup/testes/simula_onboarding.sh`
- Migração nova sem Docker: `cd backend && DATABASE_URL=postgresql+asyncpg:///asimov_dev?host=/tmp REDIS_URL=redis://localhost:6390/0 SUBDOMINIO_BOT=x CHAVE_API_ADMIN=x CHAVE_CRIPTOGRAFIA=x MODELO_CONVERSA=openai:x MODELO_VISAO=openai:x MODELO_TRANSCRICAO=openai:x uv run alembic revision --autogenerate -m "descricao"`
- O setup só roda de verdade numa VPS Ubuntu 24.04. NUNCA rode `setup/instalar.sh` nesta máquina.

## Organização

- `setup/` é o único cliente da API. Depois que a API sobe, ele NUNCA acessa o banco.
- `setup/lib/base.sh` tem `VERSAO`, caminhos, `com_voltar` e carrega as telas; `ui.sh` tem os helpers de tela (`pergunta`, `escolha`, `marca`, `confirma`); `menu.sh` o menu; `instalar.sh` e `asimov.sh` só orquestram.
- `backend/app/` agrupa por assunto (`acessos/`, `clientes/`, `agentes/`, `canais/`, `conversas/`, `midia/`, `handoff/`, `consumo/`, `ia/`, `painel/`; `conhecimento/` na fase 6). Em cada um: `rotas.py` recebe e valida, `servico.py` tem a regra, `repo.py` acessa o banco. Rota NUNCA orquestra nem escreve direto pelo repo; leitura simples (listar, ver) pode chamar `repo.py`, e é o que algumas rotas fazem hoje.
- Canal novo implementa `canais/base.py`. NUNCA espalhe `if canal == ...` fora de `canais/`: o que muda entre canais vira atributo ou método do contrato.
- Ferramenta dos agentes: um arquivo por ferramenta em `ia/ferramentas/` (ficha `FERRAMENTA` de `base.py`, com instrução de quando usar), listada em `registro.py`. NUNCA duas ferramentas no mesmo arquivo; um teste confere.
- `frontend/` é o painel do operador no navegador (React, Vite, Tailwind), servido pela API em `/painel/app`. Todo onboarding e toda configuração de agente acontecem num popup grande com o fundo embaçado, nunca em página. Nunca fala com `/admin` e nunca carrega estático de CDN. Dentro dele: `api/cliente.ts` é o único que chama `fetch`, `design/` tem um componente por arquivo e `telas/` monta a tela. Toda peça de interface vem do `designsystem/` (as seis seções, não só a de componentes) e NUNCA de biblioteca de fora. Cor só pelo nome do token do `tailwind.config.ts`; um teste recusa hexadecimal solto e outro trava as dependências do `package.json`. Exceção única: o `painel/estaticos/painel.css` das telas de entrar e primeiro acesso, que não passa pelo Tailwind e guarda as cores no `:root` dele.

## Regras que não mudam

- Todo repositório recebe `cliente_id` obrigatório e toda consulta filtra por ele. Exceções, todas da instalação e nunca de dado de um cliente pedido por outro: `acessos/` (token do operador no canal), `painel/` (a conta do operador), a resolução do agente pelo `token_webhook`, as listagens globais do operador (agentes, consumo, handoffs vencidos) e os jobs de manutenção. NUNCA use `cliente_id` vindo do corpo da requisição: nos webhooks ele sai do `token_webhook`, nas rotas admin da URL conferida no banco.
- Busca vetorial filtra `cliente_id` e `agente_id` no `WHERE`.
- Webhook do Chatwoot com assinatura inválida responde 200 e registra Falha. NUNCA 401: o Chatwoot silencia o bot na conversa.
- No WhatsApp direto a pausa do handoff é o `status` da conversa aqui, e a volta é `/retomar <código>` do destino ou o prazo do agente. NUNCA guarde essa pausa em dois lugares.
- Webhook só valida, grava e agenda. NUNCA chame IA dentro da requisição.
- Conteúdo extraído de mídia entra como dado do contato. NUNCA no prompt de sistema.
- Credenciais de canal só criptografadas no banco. NUNCA em log, resposta da API ou `.env`.
- Segredos só em `.env`. NUNCA leia, imprima ou commite `.env`. `.env.example` sem valores.
- NUNCA edite migração já aplicada; crie outra.
- NUNCA publique `/admin` no Caddy.
- Modelo e provedor de IA são configuração. NUNCA fixe nome de modelo no código fora dos padrões de `ia/`.
- Toda entrada validada no backend.
- Sem travessões em textos do setup, prompts e documentação.
- Repositório é público: NUNCA nome de cliente real, URL de Chatwoot de cliente, domínio ou IP de VPS de teste.

## Armadilhas já pagas

- Bash com `set -e`: consulta que pode voltar vazia (`grep`, `dig`, `curl`) termina com `|| true`, senão o setup cai calado.
- `exec 3<arquivo 2>/dev/null` silencia o stderr do script inteiro; use `{ exec 3<arquivo; } 2>/dev/null`.
- Helpers de tela (`pergunta`, `escolha`, `le_tecla`) usam locais com prefixo `__`; nome igual ao da variável de quem chama quebra o `printf -v`.
- Setas só com terminal (`tem_terminal`); com `ASIMOV_TTY` apontando para arquivo a leitura é por linha. Teste de teclas: pty com `pyte`, esperando o script carregar antes da primeira tecla.
- Teste teclas com bash 5 (o da VPS), não o 3.2 do macOS: o tempo de espera do Esc é outro.
- Item novo no menu muda a numeração: `setup/testes/respostas.txt` responde por número e a simulação passa a descarrilar no meio. Rode `simula_onboarding.sh` e confira que a saída é 0, não só que ele abriu.
- Terminal no navegador da Hostinger manda Enter como `\r\n`: toda leitura com terminal começa por `descarta_pendentes`, senão o Enter sobra e responde a pergunta seguinte.
- Ação do menu roda em `com_voltar` (subshell, para o Esc voltar): variável alterada lá dentro some, a não ser que saia por `devolve`.
- WAHA: o contêiner tem perfil no Compose e só sobe no primeiro agente WhatsApp (`WAHA_ATIVA=1` no `.env`, lido pelo `dc`). A `WAHA_API_KEY` nasce na instalação: gerá-la depois obrigaria a reiniciar a API. A imagem é atualizada por timer do systemd no host (`deploy/atualiza_waha.sh`), nunca pelo worker: contêiner com socket do Docker é a VPS inteira.
- WhatsApp oficial: cada agente aponta o webhook no próprio número (`webhook_configuration`), e a Meta confere o endereço na hora, antes de o agente existir no banco. Por isso o `GET` de verificação responde pelo token da URL, sem olhar o banco.
- App da Meta criado pelo caso de uso do WhatsApp só oferece `whatsapp_business_management` e `whatsapp_business_messaging`, e é só do que o agente precisa. `business_management` (que nem aparece para marcar) serve apenas à descoberta da conta por `/me/businesses`: sem ela vale o `debug_token` e, falhando, a pergunta à mão.
- O Caddyfile é montado no contêiner: mudar o arquivo não muda o que o Caddy já carregou. `sobe_servicos` roda `caddy reload` depois do `dc up`, senão caminho público novo responde 404 até alguém reiniciar o contêiner.
- Extrair atualização como root devolve `prompts/` ao root; a API roda como uid 1000. `ajusta_permissoes` roda sempre.
- DNS: um resolvedor público pode guardar "não existe" por muito tempo; a checagem pergunta aos servidores oficiais do domínio.
- Chatwoot: conversa Aberta é humano conduzindo, o agente fica calado; só Pendente gera turno.
- Pendência do turno vem de `conversa.respondido_ate`, não da posição da resposta: a resposta é gravada no fim do turno, depois do que chegou durante ele.

## Regras de trabalho

- Construa uma fase de `spec/fases.md` por vez, na ordem. A fase só termina quando o critério de aceite passa numa VPS real, os testes passam e o `shellcheck` não acusa erro.
- Ao terminar uma fase, faça o commit com a mensagem sugerida e diga ao operador o que ele pode testar e o que precisa fazer antes.
- Se algo da spec não fizer sentido na prática, não contorne em silêncio: registre em `spec/decisoes.md`, atualize o arquivo afetado e avise em uma frase.
- Se o operador corrigir a mesma coisa duas vezes, adicione uma linha a este arquivo.
- Mantenha este arquivo abaixo de 100 linhas. `CLAUDE.md` contém só `@AGENTS.md`; NUNCA duplique conteúdo nele.
