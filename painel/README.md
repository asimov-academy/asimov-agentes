# Painel web

Protótipo estático do painel em `app.<dominio>`, para validar as telas e as funções. O painel de
verdade já começou e mora em `backend/app/painel/`: este protótipo segue sendo onde as telas que
ainda não existem lá são desenhadas antes. Estudo, score e estado: `docs/painel-web.md`.

Para ver o painel de verdade, ligue com `asimov painel` na VPS.

## Abrir

Abra `painel/prototipo/index.html` no navegador. Não precisa de servidor, de build nem de internet.
Para ver como fica no celular, use a vista responsiva do navegador.

Senha do login: qualquer coisa, é protótipo.

## Telas

| Arquivo | O que valida |
|---|---|
| `index.html` | Entrar com a senha do operador |
| `primeiro-acesso.html` | Código de uso único vindo de `asimov painel`, criação da senha |
| `assistente.html` | O primeiro acesso funcionando como o setup: empresa, canal, conexão, jeito de responder, handoff e teste. `assistente.html?primeira=1` mostra o texto de primeira vez |
| `inicio.html` | Dash: saúde, conversas agora, o que está parado com gente, custo, falhas |
| `agentes.html` | Lista por empresa e por canal |
| `agente.html` | Ficha, ferramentas, prompt, modelos, canal e handoff |
| `conversas.html` | Sessões ativas, com filtro por agente e por situação |
| `conversa.html` | Histórico de uma conversa e devolver ao agente |
| `consumo.html` | Turnos, tokens e custo por agente |
| `whatsapp.html` | Números, QR code e sessões da WAHA |
| `teste.html` | Conversa de teste com o turno (modelo, latência, tokens, custo) |

## Como isso vira o painel de verdade

- `painel.js` tem um objeto `api` que é o único lugar que sabe de onde vêm os dados. Hoje resolve do
  `dados.js`; cada método já traz no comentário a rota que vai chamar. Trocar o corpo por `fetch` não
  muda nenhuma tela.
- O que `montaCasca()` escreve vira `base.html` do Jinja2; cada `.html` vira um template que herda dela.
- `painel.css` vira `backend/app/painel/estaticos/painel.css` sem mudança.
- Onde a tela mostra `rota a construir`, falta backend. As demais já existem hoje na API.

## Já construído no backend

`backend/app/painel/` tem entrar, primeiro acesso com código de uso único, sessão no Redis, freio de
tentativa, início e lista de agentes, com 29 testes. As telas de ficha do agente, ferramentas,
prompt, conversas, consumo, WhatsApp e o assistente continuam só aqui no protótipo.

## O que ainda não existe na API

- `GET /admin/conversas` e `GET /admin/conversas/{id}` (conversas e mensagens)
- `GET /admin/handoffs` (hoje só dá para ver conversa em handoff mensagem por mensagem)
- `GET/PUT .../agentes/{id}/prompt` (hoje o `persona.md` só por SSH)
- Falhas paginadas (hoje vêm as 10 últimas junto do consumo)
- Usuário do painel, sessão, código de primeiro acesso e freio de tentativa

## Dados de exemplo

`dados.js`, com Loja Exemplo, Clínica Exemplo e os agentes Ana, Bia, Caio e Duda. O repositório é
público: nada de cliente, domínio ou número real aqui.
