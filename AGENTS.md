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
- `spec/fases.md`: ordem e critério de aceite. No início de cada fase.
- `spec/decisoes.md`: log de mudanças. Antes de assumir que a spec está atual; escreva sempre que mudar algo.

## Stack

- Setup e comando `asimov`: Bash para Ubuntu 24.04 (`curl`, `jq`, `dig`).
- Backend: Python 3.12, `uv`, FastAPI, PydanticAI (OpenAI, Anthropic, Gemini, Groq, FallbackModel), arq.
- Dados: PostgreSQL 16 com pgvector, SQLAlchemy 2.0, Alembic, Redis 7.
- Execução: Docker Compose com Caddy.
- Testes: pytest com Postgres e Redis reais em container; `shellcheck`.

## Comandos de desenvolvimento

- Testes locais do backend (Postgres com banco `asimov_teste` e Redis em `localhost:6390`): `redis-server --port 6390 --daemonize yes --save "" && cd backend && uv run pytest -q`. Outros endereços: `TESTE_DATABASE_URL` e `TESTE_REDIS_URL`.
- Shellcheck: `uvx --from shellcheck-py shellcheck -x -P SCRIPTDIR setup/instalar.sh setup/asimov.sh setup/install.sh setup/lib/*.sh deploy/*.sh`
- Simular o onboarding sem VPS: `ASIMOV_TTY=setup/testes/respostas.txt bash setup/testes/simula_onboarding.sh`
- Migração nova sem Docker: `cd backend && DATABASE_URL=postgresql+asyncpg:///asimov_dev?host=/tmp REDIS_URL=redis://localhost:6390/0 SUBDOMINIO_BOT=x CHAVE_API_ADMIN=x CHAVE_CRIPTOGRAFIA=x MODELO_CONVERSA=openai:x MODELO_VISAO=openai:x MODELO_TRANSCRICAO=openai:x uv run alembic revision --autogenerate -m "descricao"`
- O setup só roda de verdade numa VPS Ubuntu 24.04. NUNCA rode `setup/instalar.sh` nesta máquina.

## Organização

- `setup/` é o único cliente da API. Depois que a API sobe, ele NUNCA acessa o banco.
- `setup/lib/base.sh` tem `VERSAO`, caminhos e carrega as telas; `instalar.sh` e `asimov.sh` só orquestram.
- `backend/app/` agrupa por assunto (`clientes/`, `agentes/`, `canais/`, `conversas/`, `midia/`, `conhecimento/`, `handoff/`, `consumo/`). Em cada um: `rotas.py` recebe e valida, `servico.py` tem a regra, `repo.py` acessa o banco. Rota NUNCA chama banco direto.
- Canal novo implementa `canais/base.py`. NUNCA espalhe `if canal == ...` fora de `canais/`.
- Não existe `frontend/` na primeira versão.

## Regras que não mudam

- Todo repositório recebe `cliente_id` obrigatório e toda consulta filtra por ele. NUNCA use `cliente_id` vindo do corpo da requisição: nos webhooks ele sai do `token_webhook`, nas rotas admin da URL conferida no banco.
- Busca vetorial filtra `cliente_id` e `agente_id` no `WHERE`.
- Webhook do Chatwoot com assinatura inválida responde 200 e registra Falha. NUNCA 401: o Chatwoot silencia o bot na conversa.
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
- Ação do menu roda em `com_voltar` (subshell, para o Esc voltar): variável alterada lá dentro some, a não ser que saia por `devolve`.
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
