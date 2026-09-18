# Auditoria de copy, 2026-09-18

Todo texto que alguém lê: documentação, telas do terminal, painel no navegador, popups, páginas
servidas, descrições de ferramenta, mensagens dos canais e o banco de ícones. Cobriu `README.md`,
`docs/`, `modelos/`, `setup/`, `backend/app/` e `frontend/src/`.

**Método.** Cinco varreduras por área, com a mesma régua, mais medição direta: as frases de tela do
terminal foram extraídas do código (407 frases) e a copy do painel foi lida do navegador com o
painel rodando, tela por tela e passo por passo, em vez de lida no fonte. Cada achado grave foi
conferido à mão antes de entrar aqui; um achado que não se confirmou está registrado no fim.

**Resultado:** 4 achados graves corrigidos nesta passada, 1 questão de privacidade corrigida,
e cerca de 180 achados de jargão, verbosidade e vocabulário inconsistente, listados para decisão.

## O que já foi corrigido

| # | Onde | O que era |
|---|---|---|
| 1 | `spec/decisoes.md`, `backend/testes/test_waha.py` | Dois celulares de DDD 51 e um identificador de contato colhidos numa VPS de teste, num repositório público. Trocados por números de exemplo. A regra do projeto (`spec/arquitetura.md`) já proibia telefone em código |
| 2 | `setup/lib/waha.sh` | O aviso da API não oficial dizia que o WhatsApp oficial "entra numa próxima versão". Ele existe desde a v0.15.0, na opção logo acima. O texto empurrava o operador para a opção arriscada dizendo que a segura não existia |
| 3 | `setup/lib/whatsapp.sh`, `docs/whatsapp-oficial.md` (2x) | "Desde 1º de outubro de 2026 a resposta é cobrada", com a cobrança ainda a duas semanas de começar. Passado virou futuro |
| 4 | `backend/app/canais/waha/canal.py` | O aviso de transferência mandava reagir com 👍 "em qualquer mensagem da conversa com o contato". Só funciona para quem tem o aparelho do agente (`_reacao` exige `fromMe`), e o aviso vai para outro número ou grupo. Quem recebia lia uma instrução impossível. Agora o `/retomar` vem primeiro e o 👍 aparece como o caso de quem está com o aparelho |
| 5 | `frontend/src/telas/agente/Onboarding.tsx` | "o destino se escolhe depois": não existe tela nenhuma para isso. `handoff_destino` não aparece uma única vez em `telas/` |
| 6 | `backend/app/plataforma/publico.py` | `/privacidade` e `/icone-app.png` são públicos e sem sessão, e o erro 503 devolvia o caminho absoluto dentro do contêiner. O caminho foi para o log |
| 7 | `frontend/src/design/icones.ts` | `Record<string, string>` fazia `keyof typeof ICONES` virar `string`: nome de ícone inventado compilava e saía um `<svg>` vazio, sem erro. Com `as const satisfies`, o compilador recusa |
| 8 | `README.md` | A lista "o setup pergunta, nesta ordem" descrevia a tela de modelos, que saiu na v0.20.0, e não citava a oferta do painel. Dizia "sete passos" para um popup de oito e "modelos" para a aba "Configurações". Prometia que tudo do painel se faz no terminal: Chat e Contatos não existem lá |
| 9 | `docs/whatsapp-oficial.md`, `setup/lib/whatsapp.sh` | "Risco de bloqueio: nenhum" no WhatsApp oficial. A conta pode ser suspensa por violar política, inclusive a de IA citada no mesmo documento |

## O que ficou para decidir

### 1. As palavras internas viraram vocabulário de tela

É o achado de fundo, e explica um terço da lista. `handoff`, `webhook`, `buffer`, `turno`,
`fallback` e `token` são nomes do banco e do código que vazaram para a tela de quem não é
desenvolvedor. Nas 407 frases do terminal: handoff 20 vezes, token 14, webhook 4, buffer 4.
No painel, que deveria estar limpo, o pior caso é a aba Configurações da ficha, que explica ao
operador que "quem confere se o nome existe é **o backend**".

Vale decidir a tradução uma vez e aplicar de um golpe:

| Palavra | Onde aparece | Proposta |
|---|---|---|
| handoff | 20 frases do terminal, 4 do painel, 6 mensagens de canal | passar a conversa para uma pessoa |
| webhook | 4 do terminal, 5 do painel | endereço que o canal chama |
| turno | 6 lugares do painel, 3 do terminal | resposta |
| buffer | 4 frases e um item de menu | tempo de espera antes de responder |
| fallback | opção de menu e rótulo | reserva |
| backend, no disco, de pé | ficha, onboarding, Canais | apagar |

### 2. Verbosidade, medida

Blocos de três ou mais linhas de explicação antes de uma pergunta, no terminal: 17 ocorrências.
Os piores:

- **WhatsApp oficial** (`setup/lib/whatsapp.sh`): cerca de 18 linhas antes do primeiro "Continuar?".
- **Erro de token sem conta** (mesmo arquivo): 9 linhas de explicação numa tela de erro.
- **Horas até voltar sozinho** (`setup/lib/waha.sh`): 3 dicas em cada um dos três canais, e a tela
  aparece em toda criação e toda edição.

No painel, o rodapé da prévia ("Conversa de mentira, montada no navegador. Nenhum modelo foi
chamado e nada foi cobrado.") se repete nos oito passos do popup.

### 3. O mesmo canal tem três nomes

| Canal | Terminal | Painel | Mensagens de erro |
|---|---|---|---|
| WAHA | WhatsApp pela WAHA | WhatsApp pelo aparelho | "da waha" |
| nativo | Nativo | Só conversa de teste | "do nativo" |

O nome do painel é o bom: diz o que é, sem nome de fornecedor. As mensagens de erro interpolam
`canal.nome`, a chave interna, e saem em minúsculas. "WAHA" continua certo no item de menu que
atualiza o contêiner.

O mesmo vale para **empresa** e **cliente**: a API diz "cliente não encontrado" em dois lugares e
"empresa não encontrada" em doze.

### 4. O painel esconde limitações que o terminal conta

O terminal exige confirmação do risco da API não oficial (bloqueio do número, usar um chip
separado). O cartão "WhatsApp pelo aparelho" no painel só diz "Não é a API oficial". O cartão do
WhatsApp oficial não diz que a Meta cobra por mensagem. Como o onboarding novo é o do painel, é por
lá que a maioria vai escolher o canal.

### 5. Descrições de ferramenta

- **Calculadora**: boa. Diz quando usar, quando não usar e o que fazer com o erro. É o modelo.
- **Busca na web**: fraca para os dois públicos. Para a IA, não tem uma linha de "quando não usar",
  e é a candidata a estourar o teto de 8 chamadas por turno. Para o operador, fala em "4 mil tokens
  de entrada por turno" em vez de dizer que encarece a conversa.
- **Passar para uma pessoa**: o "quando não usar" existe, mas longe da ficha que o modelo lê na
  hora de decidir.

### 6. Banco de ícones

50 ícones, cópia fiel do design system, nomenclatura `familia-substantivo` sem exceção. **26 são
usados e 24 estão mortos.** Em compensação, sete telas improvisam com um ícone de outro significado,
e dois glifos são desenhados à mão no componente enquanto o banco tem o equivalente (`stat-loading`
está morto enquanto o `Botao` redesenha o mesmo spinner).

Falta no banco: um chevron (um painel de navegação sem seta direcional), um check solto, e
`sys-logout`, `sys-menu`, `act-copy`, `comm-send` e `nav-user`, que são exatamente os improvisos.
Sobram duas duplicatas byte a byte (`act-cancel`/`sys-close`, `comm-comment`/`nav-messages`).

O teste que proíbe SVG solto só varre `src/telas`, e os dois desenhos à mão estão em `src/design`.

### 7. Documentação

- **`README.md`**: revisão, não reescrita. Além do que já foi corrigido, o Chatwoot ainda aparece
  como se fosse o produto em quatro pontos estruturais: a linha de abertura, o primeiro item da
  lista, o "depois de instalar" e o diagrama, que põe o Chatwoot no caminho obrigatório.
- **`docs/whatsapp-oficial.md`**: o melhor texto do repositório, honesto sobre limites. As duas
  correções urgentes já entraram.
- **`docs/painel-web.md`**: 419 linhas recomendando Jinja2 e HTMX e descartando React e Vite, que
  foi exatamente o que se construiu, mais uma seção inteira dizendo que a chave do provedor não pode
  sair do `.env`, o que a v0.20.0 desmentiu. Como está, ensina o errado a quem abrir. Precisa de um
  aviso de "estudo histórico" no topo ou de ser reduzido ao que sobreviveu.
- **`docs/auditoria-2026-09-18.md`**: apresenta como abertos os seis P1 corrigidos na v0.18.0. Três
  linhas de nota no topo resolvem.
- **`modelos/AGENTS.md.tmpl`**: não tem uma linha sobre o painel nem sobre `frontend/`, que é metade
  do que o agente de código encontra na VPS.

### 8. Estados vazios e erros sem saída

Cinco telas do painel mostram erro sem botão de tentar de novo, contra o que a `spec/frontend.md`
pede. Cinco frases diferentes dizem a mesma coisa ("algo não voltou", "a consulta não voltou", "a
lista não veio", "a busca não voltou", "a ficha não abriu"). O código de referência do erro é lido
da API, guardado, e nenhuma tela mostra: quem pede ajuda não tem o número.

Nas mensagens de canal, várias interpolam o nome da classe da exceção (`ConnectTimeout`) ou o código
HTTP cru na frase que o operador lê.

## O que não se confirmou

A varredura acusou uma frase cortada no meio em `setup/lib/menu.sh`, entre duas chamadas de `dica`.
Conferido na tela: as duas linhas saem coladas e a frase fecha certo. Não é defeito.

## O que está limpo

- **Travessão**: zero em todo o repositório, em todas as áreas. A regra está cumprida.
- **Dado de cliente real**: nenhum nome de empresa, URL de Chatwoot ou IP de VPS. Os IPs são da
  faixa de documentação, os domínios são de exemplo ou de terceiros conhecidos. Os telefones eram a
  única exceção, e foram trocados.
- **Cruzamento entre telas**: a "aba Trabalho", citada em dois lugares, existe mesmo.
- **LICENSE**: MIT, crédito à Asimov Academy, consistente com o README.
- **Contraste**: nenhum texto do painel abaixo dos 4,5:1 da WCAG AA (v0.20.3).
