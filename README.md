# Asimov Agentes

Setup da Asimov Academy que transforma uma VPS vazia numa plataforma de **agentes de IA de atendimento**, pronta para evoluir com vibecoding no Claude Code ou no Codex.

Um comando instala tudo: Docker, banco, HTTPS, a API dos agentes e o agente de código. No final você tem um agente respondendo no Chatwoot e um projeto com `AGENTS.md` para continuar construindo.

## O que você ganha

- **Agente respondendo no Chatwoot**: o setup cria o bot e liga na caixa de entrada sozinho.
- **Agente no WhatsApp, sem Chatwoot**: pareie um número lendo o QR code no próprio terminal. É a API **não oficial** (WAHA): a Meta não homologa nem dá suporte, e o número pode ser bloqueado, então use um chip só para o agente. O WhatsApp roda num contêiner na sua VPS, que só sobe quando você cria o primeiro agente assim e se atualiza sozinho toda semana, voltando para a versão anterior se algum número não reconectar.
- **Agente nativo para testar**: sem canal nenhum, você conversa com ele no terminal com o mesmo buffer, digitando, ferramentas, consumo e handoff, e liga num canal quando estiver pronto.
- **Atendimento com cara de gente**: espera o contato terminar de mandar as mensagens (buffer), mostra "digitando" e responde em mensagens curtas.
- **Entende áudio, imagem e PDF**: transcreve áudio, lê foto de documento e PDF, e não processa de novo o mesmo arquivo reenviado.
- **Passa para uma pessoa**: quando o contato pede, o agente transfere a conversa no Chatwoot para o atendente ou time escolhido, com um resumo em nota privada. Devolver a conversa para Pendente faz o agente voltar. No WhatsApp direto, o número ou grupo que você escolher recebe o aviso com o resumo e um código. Se alguém da equipe simplesmente responder pelo celular, o agente cala sozinho na hora. Para devolver a conversa a ele, reaja com 👍 em qualquer mensagem ou mande `/retomar <código>`; sem nada disso, ele volta no prazo que você definir.
- **Modelo por função**: resposta, fallback, visão e transcrição, cada um com seu provedor (OpenAI, Anthropic, Gemini ou Groq). Se o modelo principal cair, o fallback responde.
- **Uma empresa ou várias**: use só para a sua empresa ou revenda agentes para empresas clientes, com os dados de cada uma isolados.
- **Painel no navegador, se você quiser**: em `app.<seu-domínio>`, com visão geral, agentes, canais, conversas e contatos. Criar e configurar agente acontece num popup guiado, com prévia do jeito que ele vai falar e uma conversa de teste no fim. Nasce desligado: quem prefere o terminal continua com a API exatamente como sempre foi.
- **Pronto para vibecoding**: projeto com testes, `AGENTS.md` e `CLAUDE.md` para o agente de código entender e evoluir.

## Antes de começar

- VPS com **Ubuntu 24.04**, pelo menos 2 GB de RAM e 20 GB livres, com acesso root por SSH
- Um **domínio** onde você consiga criar um registro DNS
- **Chatwoot** com acesso de administrador, para agentes no Chatwoot (WhatsApp direto e agente nativo não precisam)
- Para agentes no **WhatsApp oficial** (Cloud API da Meta), um app e um número preparados na Meta: passo a passo com links em [docs/whatsapp-oficial.md](docs/whatsapp-oficial.md)
- Para agentes no **WhatsApp pela WAHA** (API não oficial), um **número de WhatsApp** só para o agente (o WhatsApp pode bloquear número que responde demais)
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
4. O registro DNS `bot.<seu-domínio>` (ele mostra o IP e espera propagar)
5. Se quer o painel no navegador, em `app.<seu-domínio>` (pede um registro DNS novo e mostra o código do primeiro acesso). Com o painel ligado, o primeiro agente pode nascer por lá
6. Canal do primeiro agente (Chatwoot, WhatsApp oficial, WhatsApp pela WAHA ou nativo). Todo canal pergunta a IA que responde: provedor, modelo e, na primeira vez daquele provedor, a chave de API, testada na hora e guardada cifrada no banco. No Chatwoot: URL e token de administrador (pedido uma vez e guardado), conta, caixa de entrada, quem recebe o handoff e nome do agente. No WhatsApp oficial: os dados do app da Meta, o número da conta e o template do aviso de handoff ([como preparar](docs/whatsapp-oficial.md)). Na WAHA: nome, ferramentas, o QR code para parear o número e quem recebe o handoff

Se algo falhar, ele mostra o motivo. Rode o mesmo comando de novo e ele continua de onde parou.

## Depois de instalar

Mande uma mensagem na caixa de entrada do Chatwoot e o agente responde. Com um agente nativo, converse com `asimov conversar`.

| Comando | O que faz |
|---|---|
| `asimov` | Menu: criar, listar, editar e remover agentes, ver consumo e falhas |
| `asimov novo-agente` | Cria outro agente no Chatwoot, no WhatsApp ou nativo, para empresa nova ou existente |
| `asimov conversar` | Conversa de teste com qualquer agente aqui no terminal, mostrando cada etapa, tokens, custo e ferramentas; nada vai para o canal |
| `asimov agentes` | Lista agentes, empresas e webhooks |
| `asimov editar` | Muda nome, tempo de buffer, mensagens por resposta, modelos ou handoff de um agente |
| `asimov remover` | Remove um agente, apagando o bot dele no Chatwoot ou desconectando o número do WhatsApp |
| `asimov consumo` | Turnos, tokens, custo estimado e falhas dos últimos 7 e 30 dias |
| `asimov handoff` | Troca quem recebe a conversa passada pelo agente |
| `asimov painel` | Liga ou desliga o painel no navegador e gera o código do primeiro acesso |
| `asimov diagnostico` | Diz a versão instalada e se cada endereço está respondendo |
| `asimov atualizar` | Baixa a versão nova e republica |

**Personalidade do agente:** edite `~/asimov-agentes/prompts/<empresa>/<agente>/persona.md`. O resumo que vai para o atendente no handoff segue `resumo_handoff.md`, na mesma pasta. A mudança vale na próxima mensagem.

**Handoff no Chatwoot:** enquanto a conversa está Aberta, o agente fica calado. Para devolver, marque a conversa como Pendente.

**Painel no navegador (opcional):** ligue com `asimov painel`. Ele pede o registro DNS de
`app.<seu-domínio>` e mostra um código de uso único para você criar a senha na primeira vez. Lá dentro:

| Tela | O que faz |
|---|---|
| Visão geral | Se está tudo de pé, o que passou do prazo, turnos, custo e quanto o agente resolveu sozinho, comparado com o período anterior |
| Agentes | Lista e o popup do agente: criar em oito passos, e depois perfil, comunicação, trabalho (o prompt), ferramentas, configurações e uma conversa de teste |
| Canais | Se cada canal respondeu agora, com o QR code do WhatsApp e reiniciar a sessão |
| Chat | As conversas, o histórico, quem falou, o custo de cada turno e devolver ao agente uma conversa que está com uma pessoa |
| Contatos | Quem já falou com algum agente, por nome ou telefone |

A operação nasce na API, e painel e terminal chamam a mesma rota. Navegar pelas conversas e pelos
contatos, por enquanto, só no painel. O painel nunca fala com `/admin`, e `app.<domínio>/admin` e `/webhook` respondem 404.

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
- `frontend/`: painel do operador no navegador (React, Vite, Tailwind), construído dentro da imagem e servido pela própria API
- `prompts/`: prompts de cada agente
- `deploy/`: Docker Compose, Caddy (HTTPS automático) e scripts de publicação

Nada é carregado de CDN: fonte, CSS e JavaScript saem da sua VPS.

## O que vem por aí

- Base de conhecimento (RAG) por agente: subir documento e o agente responder com base nele
- Backup e limpeza automática de mídia antiga

## Licença

MIT. Pode usar, modificar e distribuir, mantendo o crédito à [Asimov Academy](https://asimov.academy).
