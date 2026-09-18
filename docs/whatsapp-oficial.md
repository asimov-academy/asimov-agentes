# WhatsApp oficial: como preparar a Meta

Passo a passo para deixar um número pronto na **Cloud API oficial da Meta** e criar o agente com
`asimov novo-agente`. Se você quer testar rápido, sem número próprio e sem verificar empresa, vá
para [Caminho rápido: número de teste](#caminho-rápido-número-de-teste) no fim.

O setup pede quatro dados. Cada passo abaixo entrega um deles:

| Dado | Onde aparece | Passo |
|---|---|---|
| ID da conta de WhatsApp Business (WABA ID) | Painel do app, em WhatsApp > Configuração da API | [4](#4-conta-de-whatsapp-business-e-número) |
| ID do app | Painel do app, em Configurações do app > Básico | [8](#8-id-do-app-e-chave-secreta) |
| Token de acesso permanente | Configurações do negócio > Usuários do sistema | [7](#7-usuário-do-sistema-e-token-permanente) |
| Chave secreta do app | Painel do app, em Configurações do app > Básico | [8](#8-id-do-app-e-chave-secreta) |

Você **não** precisa colar nenhuma URL de webhook no painel da Meta. Quem faz isso é a própria
plataforma, quando o agente é criado: ela liga os webhooks do app, inscreve a conta e aponta o
webhook daquele número para o endereço do agente.

## O que esperar de prazo e de custo

- **Verificação do negócio**: de algumas horas a alguns dias, e pode pedir documento da empresa.
- **Aprovação do nome de exibição**: em geral 1 a 2 dias.
- **Aprovação do template**: costuma sair em minutos.
- **Custo**: a Meta cobra por conversa, pela [tabela de preços](https://developers.facebook.com/docs/whatsapp/pricing).
  A conta precisa de forma de pagamento para o número sair do modo de teste.

## 1. Portfólio de negócios (Business Manager)

1. Abra o [Gerenciador de Negócios](https://business.facebook.com/settings) e crie um portfólio de
   negócios, se ainda não tiver um. Use o nome real da empresa, igual ao do documento.
2. Em **Configurações do negócio > Informações do negócio**, preencha nome legal, endereço,
   telefone e site. A verificação compara o que está aqui com o documento.

Se você atende várias empresas (modo revenda), o normal é **um portfólio por empresa cliente**,
cada um com o próprio app, número e token. Um agente da plataforma corresponde a um número.

## 2. Verificar o negócio

1. Vá ao [Centro de Segurança](https://business.facebook.com/settings/security).
2. Clique em **Iniciar verificação** e siga os passos: documento da empresa (contrato social, CNPJ
   ou equivalente) e comprovação de endereço ou telefone.
3. Acompanhe o resultado ali mesmo. Referência: [verificação do negócio](https://www.facebook.com/business/help/2058515294227817).

Sem verificar, o número fica com limites baixos e o nome de exibição não é aprovado. Dá para
desenvolver e testar antes, com o número de teste.

## 3. Criar o app

1. Abra [Meus Apps](https://developers.facebook.com/apps) e clique em **Criar app**.
2. Em caso de uso, escolha **Conectar-se com clientes pelo WhatsApp** (a Meta chama de "Connect
   with customers through WhatsApp").
3. Ligue o app ao portfólio de negócios do passo 1.
4. Em **Adicionar produtos**, confirme que **WhatsApp** aparece configurado.

Referência: [primeiros passos da Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started).

## 4. Conta de WhatsApp Business e número

1. No painel do app, abra **WhatsApp > Configuração da API**.
2. Escolha ou crie a **conta de WhatsApp Business** (WABA). Anote o **ID da conta de WhatsApp
   Business**: é o primeiro dado que o setup pede.
3. Em **Número de telefone**, clique em **Adicionar número de telefone**. Use um número que:
   - possa receber SMS ou ligação para confirmar;
   - **não** esteja em uso no aplicativo do WhatsApp nem no WhatsApp Business. Se estiver, apague a
     conta naquele número antes, senão a Meta recusa.
4. Confirme o código que chegar.

O número da Cloud API não roda no celular. Ninguém responde pelo aparelho: quem atende usa o
Chatwoot, ou recebe o aviso de handoff no próprio WhatsApp (passo 9).

Os números da conta também ficam em [WhatsApp Manager > Números de telefone](https://business.facebook.com/wa/manage/phone-numbers/).

## 5. Forma de pagamento

1. Abra [WhatsApp Manager](https://business.facebook.com/wa/manage/) e vá em **Configurações da
   conta > Cobrança e pagamentos**, ou direto nas
   [formas de pagamento](https://business.facebook.com/billing_hub/payment_settings).
2. Adicione um cartão à conta de WhatsApp Business.

Sem isso o número só fala com os destinatários de teste cadastrados.

## 6. Nome de exibição

Em [Números de telefone](https://business.facebook.com/wa/manage/phone-numbers/), abra o número e
defina o **nome de exibição**, que é o que o contato vê. As regras da Meta:

- precisa representar a empresa de verdade, com pelo menos 3 caracteres;
- sem URL, sem telefone, sem emoji, sem pontuação estranha;
- sem tudo em maiúsculas, a não ser que seja sigla;
- não pode conter WhatsApp, WA, Insta, FB, Meta nem Facebook.

Referência: [sobre o nome de exibição](https://www.facebook.com/business/help/338047025165344).

Ative também a **verificação em duas etapas** do número (PIN de 6 dígitos), que a Meta exige.

## 7. Usuário do sistema e token permanente

O token de teste da tela de configuração vale 24 horas. O agente precisa de um permanente.

1. Abra [Configurações do negócio > Usuários do sistema](https://business.facebook.com/settings/system-users).
2. Clique em **Adicionar**, dê um nome (por exemplo `agente-atendimento`) e escolha a função
   **Administrador**.
3. Selecione o usuário criado e clique em **Adicionar ativos**:
   - o **app** do passo 3, com **Gerenciar app**;
   - a **conta de WhatsApp Business** do passo 4, com **Gerenciar contas do WhatsApp Business**.
4. Clique em **Gerar token**, escolha o app e marque as permissões:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
   - `business_management`
5. Em validade, escolha **Nunca expira**.
6. Copie o token. **Ele aparece uma vez só.** Se perder, gere outro.

Referência: [token permanente com usuário do sistema](https://developers.facebook.com/docs/whatsapp/business-management-api/get-started).

O token vai para a plataforma e é guardado criptografado no banco. Ele nunca aparece em log, na
resposta da API nem no `.env`.

## 8. ID do app e chave secreta

1. No painel do app, abra **Configurações do app > Básico**
   (`https://developers.facebook.com/apps/<ID_DO_APP>/settings/basic/`).
2. Copie o **ID do app**, que fica no topo.
3. Em **Chave secreta do app**, clique em **Mostrar** e copie.

A chave secreta é o que prova que o webhook veio da Meta: cada corpo chega assinado com ela
(`X-Hub-Signature-256`) e a plataforma recusa o que não confere.

## 9. Template do aviso de handoff

Quando o agente passa a conversa para uma pessoa, ele manda um aviso com o resumo para o número que
você escolher. Esse número normalmente nunca falou com o agente, e a Meta só entrega mensagem para
quem não escreveu nas últimas 24 horas se ela for um **template aprovado**.

1. Abra [WhatsApp Manager > Modelos de mensagem](https://business.facebook.com/wa/manage/message-templates/)
   e clique em **Criar modelo**.
2. Categoria **Utilidade**, idioma **Português (BR)**, nome `aviso_handoff`.
3. No corpo, use exatamente três variáveis:

```
O agente passou uma conversa para voce.

Contato: {{1}}
Resumo: {{2}}
Codigo: {{3}}

Responda /retomar neste chat quando terminar.
```

4. Envie para aprovação. O setup lista só os templates aprovados com três variáveis, então se o seu
   tiver outra forma ele não vai aparecer na lista.

Sem template o handoff continua funcionando, mas o aviso só chega se quem recebe tiver escrito ao
agente nas últimas 24 horas. Referência:
[modelos de mensagem](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates).

## 10. Criar o agente

Na VPS:

```bash
asimov novo-agente
```

Escolha **WhatsApp oficial** e responda: conta de WhatsApp Business, ID do app, token de acesso,
chave secreta, número (o setup lista os da conta), nome do agente, empresa, ferramentas, horas até
o agente voltar sozinho, quem o agente atende e, por fim, o número que recebe o handoff e o
template do passo 9.

No fim, mande uma mensagem para o número e o agente responde.

## Conferir se funcionou

- `asimov agentes` mostra o agente, o canal e o webhook dele.
- `asimov consumo` mostra os turnos e as falhas dos últimos dias.
- Nada acontece quando você manda mensagem? Veja o log da API:

```bash
source deploy/compose.sh && dc logs -n 100 api
```

Linha `webhook_verificado` quer dizer que a Meta conferiu o endereço. Linha `webhook_aceito` quer
dizer que a mensagem chegou.

## Erros comuns

| O que acontece | Causa provável | O que fazer |
|---|---|---|
| A Meta recusa o token de acesso | token de teste (24 h) ou sem as permissões | refaça o passo 7, com as três permissões e "Nunca expira" |
| A Meta recusa apontar o webhook | o usuário do sistema não tem o app ou a conta como ativo | passo 7, item 3 |
| O agente não recebe nada | alguém mexeu na configuração do webhook pelo painel da Meta | `asimov editar`, opção **WhatsApp**, **Refazer o webhook na Meta** |
| Aviso de handoff não chega | fora da janela de 24 h e sem template aprovado | passo 9; `asimov consumo` mostra a falha `handoff_incompleto` |
| Só alguns números recebem resposta | número de teste com destinatários cadastrados | passo 5, adicione forma de pagamento |
| Não consigo adicionar o número | ele está em uso no app do WhatsApp | apague a conta do WhatsApp naquele número e tente de novo |

## Caminho rápido: número de teste

Para testar a plataforma antes de resolver verificação, pagamento e nome de exibição:

1. Faça os passos 3, 4 (usando o **número de teste** que a Meta oferece na tela de configuração da
   API), 7 e 8.
2. Em **WhatsApp > Configuração da API**, cadastre em **Para** até 5 números que vão conversar com
   o agente. O número de teste só fala com esses.
3. Crie o agente sem template (o setup deixa seguir sem). Para testar o handoff, mande primeiro uma
   mensagem qualquer do número que vai receber o aviso para o número do agente: isso abre a janela
   de 24 horas e o aviso chega em texto.

Quando o número de verdade estiver pronto, crie outro agente com ele.

## WhatsApp oficial ou WAHA

| | Oficial (Cloud API) | WAHA |
|---|---|---|
| Homologação | da Meta | nenhuma, é API não oficial |
| Risco de bloqueio | nenhum | o número pode ser bloqueado sem aviso |
| Custo | por conversa, tabela da Meta | só a VPS |
| Preparação | os passos deste documento | ler um QR code no terminal |
| Número | não roda no celular | é o seu celular, alguém pode responder pelo aparelho |
| Aviso de handoff | template aprovado fora da janela de 24 h | mensagem comum |

Para testar ideia e prompt, a WAHA resolve em minutos. Para produção com número da empresa, o
oficial é o caminho.
