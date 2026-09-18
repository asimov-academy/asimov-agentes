# Etapa 1: O que o app faz

## Nome provisório

Asimov Academy (provisório, exibido no banner do setup)

## O que o app faz

Um setup de instalação guiada, rodado numa VPS com o comando `bash <(curl -sSL setup.dominio.art.br)`, no estilo do Setup Orion. Ele prepara uma VPS Ubuntu 24.04 com domínio e entrega o mínimo para operar agentes de IA de atendimento no WhatsApp (API oficial ou não oficial pela WAHA) e no Chatwoot, já pronto para ser evoluído com vibecoding (Claude Code ou Codex). O setup é o ponta pé inicial: cria as dependências e a estrutura, e a partir daí o operador evolui tudo em vibecoding. A instalação é multitenant: quem instala pode criar vários agentes, um para cada cliente (empresa) que atende. Faz parte de uma metodologia para criar agentes de IA com vibecoding.

## Solução atual e por que falha

Hoje a VPS e o projeto de cada agente são montados à mão ou com um script simples que só instala dependências e cria um esqueleto de projeto, sem canais, sem recursos de atendimento e sem suporte a vários clientes numa instalação (assumido). Isso não escala para alunos nem para quem já atende várias empresas (o dono do projeto atende 3).

## Funções essenciais da primeira versão

1. Instalação com um comando só: `bash <(curl -sSL setup.dominio.art.br)`.
2. Tela de boas-vindas com o nome do script em ASCII, versão, texto sobre o que instala, licença e aceite `Y/N`.
3. Preparação automática da VPS vazia: confere Ubuntu 24.04, atualiza o sistema e instala o básico, com passos numerados no formato `1/15 - [ OK ] - descrição`.
4. Onboarding guiado por perguntas no terminal, curto e colorido: modo de uso (só a própria empresa ou revenda para empresas clientes), domínio, e-mail para o SSL e o assistente de código. Nada de IA aqui desde a v0.20.0: modelo e provedor são escolha de cada agente, e a chave é pedida uma vez, testada na hora e guardada cifrada no banco.
5. Conferência de que `bot.<dominio>` aponta para a VPS antes de configurar o SSL.
6. Firewall, banco, SSL e projeto base instalados, junto com Node, Python (uv) e o agente de código escolhido pelo operador: Claude Code ou Codex. Logo depois, a instalação entra na conta desse assistente (v0.25.0): é a assinatura do operador que move o copiloto do painel, e pular só deixa o painel sem copiloto.
7. Criação de vários agentes, cada um ligado a um cliente (empresa), numa mesma instalação.
8. Conexão de cada agente a um canal escolhido no script: Chatwoot já existente, WhatsApp pela API oficial (Cloud API da Meta), WhatsApp não oficial pela WAHA instalada na própria VPS (QR code no terminal) ou nativo, sem canal, para conversar com o agente só no terminal.
9. Transcrição de áudio (Whisper na OpenAI ou Groq, ou o próprio Gemini).
10. Leitura de imagens e documentos com uma IA de visão, com cache por arquivo: a mesma mídia reenviada não é processada de novo.
11. Buffer de mensagens, efeito digitando e divisão das respostas em várias mensagens. Se o modelo de resposta falhar, o fallback responde.
12. Base de conhecimento com RAG por agente.
13. Handoff para humano: no Chatwoot, transferência da conversa; no WhatsApp direto (oficial ou WAHA), pausa do agente para o contato, aviso com resumo para o número ou grupo da empresa e retomada por comando ou por tempo.
14. Tratamento de erro: repetição automática de falhas passageiras; se persistir, para com `[ ERRO ]`, motivo, o que fazer e log em arquivo; ao rodar de novo, retoma de onde parou.
15. Comando `asimov` na VPS: sem argumento abre o menu (criar, conversar, listar, editar e remover agente, ver consumo e falhas, painel, conta de IA, token do Chatwoot e diagnóstico); também `asimov novo-agente` (para empresa nova ou existente, conforme o modo), `conversar`, `handoff`, `painel`, `ia`, `diagnostico` e `atualizar`. Base de conhecimento entra no mesmo comando na fase 6.
16. Resumo final com o que foi instalado, webhooks e próximos passos para abrir o projeto no Claude Code ou no Codex.
17. Registro de consumo e falha por turno (modelo, tokens, custo, latência, erro), para saber o custo por cliente e depurar (assumido).
18. Geração de `AGENTS.md` (fonte única) e `CLAUDE.md` (uma linha, `@AGENTS.md`) no projeto instalado, ao final do setup, curtos e só com o que o agente de código não descobre lendo o código, para o operador evoluir o agente em vibecoding com Claude Code ou Codex.

19. Painel do operador no navegador, em `app.<dominio>`, opcional e desligado por padrão: visão geral, agentes, canais, conversas, contatos e funil, com todo onboarding e toda configuração de agente num popup grande. Com a conta de IA vinculada, ele ganha um copiloto que opera a plataforma conversando em português, pela assinatura do operador, e que nunca muda nada sem o operador confirmar.

## Fora de escopo

- Front de CRM (a pessoa pode usar um front próprio).
- Instalação de outras ferramentas além da estrutura do agente.
- Instalação do Chatwoot (a integração com um Chatwoot já existente entra; ver função 8).
- Evolution API (a WhatsApp não oficial é a WAHA, spec/decisoes.md).
- Telegram (trocado pela WAHA e pelo agente nativo antes da fase 5).
- Modo shadow (agente respondendo em nota privada antes de liberar para o contato).
- Hooks do Claude Code no projeto gerado para bloquear ações proibidas (ler `.env`, `docker compose down -v`, editar migração aplicada); por enquanto as proibições ficam no `AGENTS.md`, em testes e no `publicar.sh`.
- Atualização automática da plataforma. `asimov atualizar` existe e é do operador: ele decide quando rodar, porque uma atualização sozinha sobrescreveria o que ele mudou em vibecoding. Só a imagem da WAHA se atualiza sozinha, por timer no host.

## Modo de condução

Modo proposta. A pessoa é técnica (escreve scripts bash, usa Claude Code, PydanticAI, VPS) e aceita termos técnicos.

Vocabulário: "script", "setup", "VPS", "domínio", "agente" (agente de IA de atendimento), "cliente" (empresa atendida por quem instala), "alunos" (quem aprende a metodologia e roda o setup), "handoff", "buffer", "base de conhecimento", "vibecoding".

## Implicações técnicas

- Tipo de uso: negócio. Quem instala é operador técnico (dono do projeto, alunos, clientes da metodologia); quem conversa com os agentes é o público final dos clientes, via WhatsApp (oficial ou não oficial) ou Chatwoot.
- Plataforma: a instalação e a operação acontecem no terminal da VPS via SSH; o atendimento acontece no celular do público final, pelos canais. Sem front nesta versão, então a criação e configuração de agentes precisa de uma interface sem tela (API e/ou CLI) (derivado).
- Integrações externas: WhatsApp Cloud API (webhook público com HTTPS), WAHA (WhatsApp não oficial, container na VPS com webhook interno), Chatwoot API (Agent Bot com webhook de saída e API para responder e transferir conversa), subdomínio `bot.<dominio>` apontado para a VPS como endpoint dos webhooks, Whisper para transcrição, modelo com visão para imagens e documentos, LLM do agente com provedor e modelo configuráveis por agente (OpenAI, Anthropic, Gemini), embeddings para o RAG, Let's Encrypt para SSL, DNS do domínio.
- Internet obrigatória: webhooks dos canais e APIs de IA dependem dela.
- Importação de dados: não há planilha ou sistema para importar; a base de conhecimento de cada agente é carregada a partir de documentos enviados pelo operador (derivado).
- Multitenant desde a primeira versão: todo dado (agente, canal, conversa, base de conhecimento) pertence a um cliente e é isolado por ele em toda consulta.
- O script precisa ser idempotente e seguro para rodar de novo na mesma VPS (derivado), e o projeto gerado deve vir preparado para evolução com Claude Code (derivado da metodologia de vibecoding).
