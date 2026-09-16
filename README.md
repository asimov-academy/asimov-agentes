# Asimov Agentes

Setup da Asimov Academy que transforma uma VPS vazia numa plataforma de **agentes de IA de atendimento**, pronta para evoluir com vibecoding no Claude Code ou no Codex.

Um comando instala tudo: Docker, banco, HTTPS, a API dos agentes e o agente de código. No final você tem um agente respondendo no Chatwoot e um projeto com `AGENTS.md` para continuar construindo.

## O que você ganha

- **Agente respondendo no Chatwoot**: o setup cria o bot e liga na caixa de entrada sozinho.
- **Atendimento com cara de gente**: espera o contato terminar de mandar as mensagens (buffer), mostra "digitando" e responde em mensagens curtas.
- **Modelo por função**: resposta, fallback, visão e transcrição, cada um com seu provedor (OpenAI, Anthropic, Gemini ou Groq). Se o modelo principal cair, o fallback responde.
- **Uma empresa ou várias**: use só para a sua empresa ou revenda agentes para empresas clientes, com os dados de cada uma isolados.
- **Pronto para vibecoding**: projeto com testes, `AGENTS.md` e `CLAUDE.md` para o agente de código entender e evoluir.

## Antes de começar

- VPS com **Ubuntu 24.04**, pelo menos 2 GB de RAM e 20 GB livres, com acesso root por SSH
- Um **domínio** onde você consiga criar um registro DNS
- **Chatwoot** com acesso de administrador
- Chave de API de pelo menos um provedor: OpenAI, Anthropic, Gemini ou Groq

## Instalação

Na VPS, como root:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/asimov-academy/asimov-agentes/main/setup/install.sh)
```

O setup pergunta, nesta ordem:

1. Se os agentes são só da sua empresa ou para empresas clientes
2. Domínio e e-mail para o certificado SSL
3. Claude Code ou Codex
4. Provedor e modelo para resposta, fallback, visão e transcrição, com as chaves de API
5. O registro DNS `bot.<seu-domínio>` (ele mostra o IP e espera propagar)
6. URL e token de administrador do Chatwoot, conta, caixa de entrada e nome do agente

Se algo falhar, ele mostra o motivo. Rode o mesmo comando de novo e ele continua de onde parou.

## Depois de instalar

Mande uma mensagem na caixa de entrada do Chatwoot e o agente responde.

| Comando | O que faz |
|---|---|
| `asimov novo-agente` | Cria outro agente, para empresa nova ou existente |
| `asimov agentes` | Lista agentes e empresas |
| `asimov atualizar` | Baixa a versão nova e republica |

**Personalidade do agente:** edite `~/asimov-agentes/prompts/<empresa>/<agente>/persona.md`. A mudança vale na próxima mensagem.

**Evoluir com vibecoding:**

```bash
cd ~/asimov-agentes && claude
```

Troque `claude` por `codex` se escolheu o Codex. Depois de mudar o código, publique:

```bash
./deploy/publicar.sh
```

Ele roda os testes antes e não publica nada se algum falhar.

## Como funciona

```
WhatsApp ─► Chatwoot ─► bot.<domínio>/webhook ─► API ─► fila (buffer) ─► worker ─► modelo de IA
                                                                              │
Chatwoot ◄──────────────────── resposta em mensagens curtas ◄─────────────────┘
```

- `setup/`: instalador e comando `asimov`
- `backend/`: API (FastAPI), worker (arq), agente (PydanticAI), Postgres e Redis
- `prompts/`: prompts de cada agente
- `deploy/`: Docker Compose, Caddy (HTTPS automático) e scripts de publicação

## O que vem por aí

- Áudio, imagens e PDFs enviados pelo contato
- Passar a conversa para um humano no Chatwoot
- WhatsApp oficial e Telegram direto, sem Chatwoot
- Base de conhecimento (RAG) por agente
- Editar e remover agentes e ver consumo pelo `asimov`

## Licença

MIT. Pode usar, modificar e distribuir, mantendo o crédito à [Asimov Academy](https://asimov.academy).
