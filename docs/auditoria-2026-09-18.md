# Auditoria técnica de 18/09/2026

## Parecer

A base tem organização por domínio, contratos de canal, testes úteis e migrações consistentes. Entretanto, há falhas de confiabilidade que permitem perder respostas, responder durante atendimento humano e reutilizar arquivos de um cliente excluído em outro cliente. A prioridade recomendada é corrigir esses caminhos antes de ampliar o uso em produção.

Foram registrados **22 achados na base auditada: 6 P1, 14 P2 e 2 P3**. Oito sondas executáveis confirmam comportamentos defeituosos; uma delas cobre dois achados. Há também uma revisão parcial, separada, do painel em desenvolvimento e uma tabela de divergências da especificação. Não foi encontrada evidência suficiente para declarar um incidente ou vazamento real ocorrido.

P1 significa corrigir antes de ampliar a operação; P2, corrigir no próximo ciclo de manutenção; P3, organização e manutenção. As prioridades consideram o cenário documentado de uma instalação com operador global e `/admin` local. Não são pontuações CVSS.

## Recorte e método

- Referência Git no início: `e12af66311717eb7d35b68845f1b41ff01a486d2`, versão publicada `v0.17.0`.
- Leitura das oito specs, instruções, documentação, estrutura de backend/setup/deploy, modelos, prompts e testes. Revisão cruzada dos fluxos de criação, webhook, turno, mídia, handoff, remoção e atualização.
- Inspeção estática, execução da suíte, sondas de falha com provedores simulados, Postgres e Redis reais e ciclo Alembic em banco descartável.
- O workspace mudou durante a auditoria: surgiram implementação de painel, migração `0014`, dependências e alterações em arquivos existentes. Os resultados de 266 testes e 13 migrações se referem ao estado anterior a essas alterações. Não certificam o novo painel.
- Arquivos preexistentes ou criados por trabalho concorrente foram preservados. A auditoria acrescenta apenas documentação e sondas explícitas, sem corrigir código de produção.
- `.env` não foi lido, impresso ou modificado. O instalador real não foi executado. Não houve publicação, chamada real a provedores ou acesso à VPS.

[Inventário de arquivos e identificação do recorte](auditoria-2026-09-18-inventario.md). O inventário identifica a superfície, não implica teste funcional individual de todo arquivo.

## Verificações executadas

| Verificação | Resultado | Limite |
| --- | --- | --- |
| `cd backend && uv run --offline pytest -q` | 266 passaram, 8,40 s | Provedores e canais externos simulados; anterior ao painel concorrente |
| Oito sondas da auditoria | 8 passaram; 0,55 s na reexecução do arquivo definitivo | Passar confirma o defeito descrito, não uma correção |
| Shellcheck dos scripts de setup/lib/deploy | Sem erros | Não comprova comportamento de systemd/Docker/Ubuntu |
| Onboarding simulado com Bash 5 | Saída 0 | macOS emitiu oito avisos de `date -Is`; rede e serviços simulados |
| Parse sintático dos arquivos Python inspecionados | Sem erros | Não substitui execução ou análise de tipos |
| Alembic: upgrade head, check, downgrade base, upgrade head, check | Sucesso nas 13 migrações; sem novas operações detectadas | Banco local descartável, removido ao fim; não incluiu a `0014` concorrente |

Comandos de verificação do shell:

```bash
uvx --offline --from shellcheck-py shellcheck -x -P SCRIPTDIR setup/instalar.sh setup/asimov.sh setup/install.sh setup/lib/*.sh deploy/*.sh
ASIMOV_TTY=setup/testes/respostas.txt /opt/homebrew/bin/bash setup/testes/simula_onboarding.sh
```

O segundo comando registra o executável Bash 5 desta máquina; adaptar o caminho em outra máquina. Não equivale a executar `setup/instalar.sh` na VPS.

As sondas ficam em [backend/testes/auditoria_2026_09_18.py](../backend/testes/auditoria_2026_09_18.py). O nome evita coleta normal. Executar explicitamente, **somente com Postgres e Redis dedicados a testes**, pois as fixtures apagam dados dessas bases:

```bash
cd backend
uv run --offline pytest -q testes/auditoria_2026_09_18.py
```

Ao corrigir os achados, transformar as sondas em regressões da suíte normal com expectativas do comportamento correto. Não manter expectativas defeituosas como critérios de produto.

## Achados P1

### A01. Reentrega não recupera mensagem gravada sem agendamento

**Evidência:** `backend/app/conversas/webhook.py:186`, ramo `if not nova` em `:199`, e `conversas/buffer.py:33`. **Reproduzido:** `test_a01_reentrega_nao_recupera_fila`.

O webhook confirma a gravação antes de agendar. Se a fila falha, responde 500; quando o provedor reenvia, a deduplicação retorna 200 sem tentar agendar. A mensagem permanece no banco sem turno até outro evento eventualmente provocar processamento. A pausa por intervenção humana também ocorre depois da gravação e merece o mesmo tratamento de recuperação.

**Correção:** persistir a intenção de processamento na mesma transação da mensagem, com despachante recuperável, ou mecanismo equivalente de reconciliação. Deduplicar conteúdo não pode eliminar trabalho pendente. **Aceite:** falhar Redis após o commit, reenviar e recuperar um único processamento sem duplicar mensagens.

### A02. Falha no envio é registrada como entrada respondida

**Evidência:** `conversas/turno.py`, `_envia` e chamada seguinte a `repo.marca_respondido`. **Reproduzido:** `test_a02_envio_falho_marca_respondido`.

`_envia` captura a exceção, interrompe os envios e devolve apenas a quantidade enviada. O turno avança `respondido_ate`, mesmo com zero envios ou envio parcial, e pode retornar `respondido`. A próxima execução deixa de considerar a entrada pendente. Também existe a janela inversa: envio externo bem-sucedido e queda antes de gravar o resultado podem produzir duplicação na retomada.

**Correção:** estado persistente de saída por fragmento, distinguir preparado/enviado/falho e estratégia de idempotência conforme o canal. Só concluir a entrada quando cumprida a política de entrega. **Aceite:** falha no primeiro e no segundo fragmento, recuperação após queda e ausência de reenvio dos fragmentos confirmados.

### A03. Expiração do buffer descarta resposta sem mensagem nova

**Evidência:** `conversas/buffer.py:37`; verificações do token em `conversas/turno.py`. **Reproduzido:** `test_a03_token_expirado_descarta_sem_mensagem_nova`.

O token dura `max(buffer_segundos * 10, 60)`. Com buffer de 8 segundos, são 80 segundos desde o agendamento, incluindo espera de fila, mídia e modelo. A expiração é interpretada como substituição por nova mensagem. Não há necessariamente outro job que recupere a entrada. A sonda acelera a expiração no Redis; não simula uma chamada real de 80 segundos.

**Correção:** separar revisão da conversa de expiração operacional, com versão persistente ou renovação e reconciliação apropriadas. **Aceite:** fila atrasada e modelo lento sem mensagem nova ainda produzem resposta; mensagem realmente nova invalida apenas o turno anterior.

### A04. Intervenção humana durante o modelo não cancela o envio

**Evidência:** `conversas/turno.py`, `_turno` e `_envia`; ação `PAUSAR` em `conversas/webhook.py`. **Reproduzido:** `test_a04_humano_intervem_durante_modelo_e_bot_responde`.

O direito de falar é consultado no início. A pausa que chega durante a geração não invalida a execução, e `_envia` não relê o status depois da geração ou da espera de digitação. A sonda confirmou resposta com a conversa já em `humano`. Desativação do agente durante a execução apresenta risco semelhante, ainda não reproduzido separadamente.

**Correção:** cancelamento por revisão de controle e revalidação imediatamente antes de cada envio. **Aceite:** humano assume durante geração e entre fragmentos; nenhum fragmento posterior à pausa deve sair.

### A05. Novo cliente pode herdar prompt de cliente excluído

**Evidência:** `agentes/servico.py:93`, `_cria_prompts`, e remoções de cliente/agente. **Reproduzido:** `test_a06_prompt_reutilizado_por_novo_cliente`.

O caminho depende dos slugs de empresa e agente; arquivos existentes são preservados. Após excluir ambos e recriar os mesmos nomes, o novo `cliente_id` é diferente, mas aponta ao prompt antigo. Isso pode levar instruções ou informações do cliente anterior para o novo atendimento. A sonda gravou apenas um marcador fictício em diretório temporário.

**Correção:** vincular arquivos à identidade imutável do cliente e controlar explicitamente reaproveitamento dentro dessa identidade. **Aceite:** UUID diferente nunca herda arquivos automaticamente; restauração intencional do mesmo cliente continua possível.

### A06. Lock pode vencer enquanto o job ainda executa

**Evidência:** `plataforma/config.py`, `lock_ttl_segundos=240`; `worker.py:61`, `job_timeout=300`; `conversas/buffer.py`, lock sem renovação. **Análise estática.**

Há uma janela de execução permitida após o fim da exclusividade. Um novo evento pode conseguir o lock enquanto o job anterior ainda envia ou transfere. A comparação de token ao liberar protege o lock do sucessor, mas não impede efeitos concorrentes do antecessor. Depende de duração e interleaving; não foi feito ensaio de 240 segundos.

**Correção:** lease renovável com cancelamento ao perder posse e proteção contra efeitos de um executor antigo; alinhar limites de operação. **Aceite:** dois jobs sob atraso controlado nunca enviam simultaneamente, inclusive após expiração e retomada do worker.

## Achados P2

### A07. Falhas assíncronas da Cloud API são ignoradas

**Evidência:** `canais/whatsapp/canal.py`, `interpretar`, ramo `statuses`, e envio de handoff. **Reproduzido:** segunda parte de `test_a08_whatsapp_perde_segunda_mensagem_e_ignora_falha`.

Um status `failed`, inclusive com código `131047`, vira `IGNORAR`. O fallback para template depende da exceção síncrona de envio. Se a rejeição chegar depois como status, não há reconciliação da saída, registro adequado da falha ou acionamento desse fallback. A sonda comprova o descarte do payload, não frequência ou comportamento da Meta em produção.

**Correção/aceite:** guardar o ID externo e tratar estados de entrega idempotentemente; validar aviso fora da janela em VPS com template aprovado e conferir resultado assíncrono.

### A08. Webhook oficial lê apenas o primeiro elemento do lote

**Evidência:** `canais/whatsapp/canal.py`, `_mudanca` e `mensagens[0]`. **Reproduzido:** primeira parte de `test_a08_whatsapp_perde_segunda_mensagem_e_ignora_falha`.

O parser retorna uma única mudança e uma única mensagem. Um envelope com duas mensagens aceita só a primeira; confirmar o envelope não recupera a segunda. **Correção/aceite:** contrato que permita múltiplos eventos, percorrendo entradas, mudanças e mensagens; deduplicar cada evento e testar lotes mistos e reentrega.

### A09. Limite do histórico corta também entradas ainda pendentes

**Evidência:** `conversas/repo.py:149`, limite padrão 40; `_turno` separa pendentes somente depois dessa consulta. **Análise estática.**

Mais de 40 mensagens antes do processamento podem excluir entradas ainda não respondidas do contexto. O avanço do marcador até a última entrada passa a tratá-las como concluídas. **Correção/aceite:** consultar pendências separadamente do histórico limitado; definir limite explícito e tratamento visível para excesso, sem descartá-lo silenciosamente; testar rajada de 41 ou mais mensagens.

### A10. Retomada automática escolhe canal do agente, não da conversa

**Evidência:** `handoff/servico.py:261`, uso de `_canal_do_agente`; contraste com `agentes/servico.py`, `canal_da_conversa`. **Análise estática.**

O terminal cria conversa nativa até para agente de canal externo. Na retomada por tempo, o código pode chamar Chatwoot/WhatsApp com identificador do terminal ou deixar a pausa nativa no Redis. **Correção/aceite:** resolver canal e credenciais pela conversa em toda retomada; testar terminal de agente Chatwoot, WAHA e oficial até vencer o prazo.

### A11. Política pública interpola HTML sem escape

**Evidência:** `plataforma/publico.py:40`, substituições em `:57`. **Reproduzido:** `test_a05_html_sem_escape`.

Empresa, agente e contato entram diretamente no HTML. Valores administrativos com tags podem gerar HTML ativo na página pública. A sonda confirma `<script>` no resultado; não foi executado exploit em navegador. O vetor exige controlar esses valores administrativos, não é acesso anônimo ao cadastro.

**Correção/aceite:** escape apropriado por contexto ou template com autoescape; testar nomes com tags, aspas e caracteres especiais preservando apresentação textual.

### A12. Atualização aceita modelo obrigatório vazio

**Evidência:** validação `valida_modelos`, que pula valores falsos, e edição de agente. **Reproduzido:** `test_a07_modelo_obrigatorio_aceita_string_vazia`.

`PATCH` com `modelo_conversa: ""` retorna 200 e persiste configuração que não resolve um modelo válido. **Correção/aceite:** distinguir campo omitido, opcional e obrigatório; validar antes de persistir e responder 422. Revisar também nomes só com espaços, comprimentos contra as colunas e tamanho do slug após o sufixo de exclusão lógica.

### A13. Credenciais passam por argumentos de processos do setup

**Evidência:** `setup/lib/agente.sh:12`, `dados=(--data "$corpo")`, e montagem de credenciais com `jq --arg` nos fluxos de canal. **Análise estática.**

O JSON pode conter credenciais e vai no argv do `curl`; argumentos de `jq` também podem conter tokens. Em host que permite inspeção de processos por outro usuário, isso expõe segredos durante a execução. Não foi inspecionada credencial real.

**Correção/aceite:** transportar segredo por entrada padrão ou arquivo temporário com acesso restrito e limpeza garantida; validar a lista de argumentos usando apenas valores fictícios. A proteção já aplicada ao header administrativo não cobre o corpo.

### A14. Tratamento de erro pode revelar tokens de URL e dados pessoais

**Evidência:** `main.py`, `erro_interno`; `conversas/webhook.py:196`; registros com `repr(erro)` em turno/handoff. **Análise estática.**

O handler registra `request.url.path`, que pode incluir token do webhook. Exceções de banco/provedor podem conter parâmetros, texto ou URLs; truncar não anonimiza. Nas rotas administrativas a resposta inclui a exceção completa. Logs de acesso também precisam de verificação na implantação. Não foi demonstrado vazamento real, nem feita inspeção de logs de clientes.

**Correção/aceite:** erros públicos estáveis, IDs de correlação e saneamento centralizado; configurar ocultação de caminhos sensíveis nos logs. Injetar erro com marcadores fictícios e comprovar sua ausência em resposta e logs.

### A15. Atualização sobrescreve personalizações sem recuperação

**Evidência:** `setup/install.sh:38`, extração direta no destino; orientação de editar `modelos/privacidade.html` em `setup/lib/whatsapp.sh`. **Análise estática.**

Arquivos distribuídos são substituídos, inclusive o modelo de privacidade que o operador é orientado a personalizar e código alterado localmente. Não há prévia de conflitos, backup ou troca transacional. **Correção/aceite:** separar configuração personalizável da distribuição e aplicar atualização com snapshot, migração e rollback definido; testar personalização e interrupção da extração. Checksum obrigatório está no planejamento da fase 7 e continua pendente.

### A16. Publicação alternativa não recarrega o Caddy

**Evidência:** `deploy/publicar.sh:24`, `dc up -d api worker caddy`; contraste com `sobe_servicos` em `setup/lib/instalacao.sh`. **Análise estática.**

A correção de reload está no setup, mas não no script de publicação. Alterar Caddyfile montado sem recriar o contêiner deixa regras antigas em memória. **Correção/aceite:** concentrar a ativação da configuração num fluxo único e validar rota pública nova após atualização com contêiner já existente.

### A17. Limpeza diária remove no máximo 500 mídias

**Evidência:** `midia/repo.py:40`, máximo 500; `midia/servico.py`, limpeza de lote único; cron diário em `worker.py`. **Análise estática.**

Acima de 500 arquivos elegíveis novos por dia, o atraso cresce. A promessa de exclusão em um a dois dias deixa de valer e o disco pode encher. **Correção/aceite:** paginação até esgotar elegíveis ou orçamento com reagendamento, métrica de atraso e tratamento de órfãos; testar mais de um lote.

### A18. Extração de PDF bloqueia o processamento assíncrono

**Evidência:** `midia/extracao.py:130`, `PdfReader` e `extract_text` de todas as páginas dentro da função assíncrona. **Análise estática.**

O limite de páginas para visão vem depois da extração integral. Limite de bytes não garante limite de CPU/memória de PDF comprimido. Um documento custoso pode bloquear outros jobs no mesmo processo. **Correção/aceite:** execução isolada com limites de páginas, tempo e memória antes de extração extensa; comprovar que um arquivo lento não interrompe outra conversa. Não foram usados PDFs hostis nesta auditoria.

### A19. Cancelamento da criação pode concluir etapa sem agente

**Evidência:** `setup/lib/agente.sh`, `fluxo_novo_agente` e `tela_primeiro_agente` em `:361`; cancelamentos bem-sucedidos nos fluxos de canal. **Análise estática.**

Há saídas com retorno 0 sem criação, enquanto a tela inicial grava `agente_id` sem exigir ID preenchido. A presença da chave é usada para pular a etapa em retomadas. **Correção/aceite:** distinguir cancelamento de criação concluída, validar ID e só então persistir etapa; simular recusa e reinício nos três canais.

### A20. Health positivo não significa atendimento operacional

**Evidência:** `main.py`, `/health`; `deploy/docker-compose.yml` e verificação de publicação. **Análise estática.**

A saúde verifica API, banco e Redis, não execução do worker ou idade dos jobs. O worker pode estar parado com API saudável e mensagens acumuladas. **Correção/aceite:** heartbeat do worker, métricas de fila/pendências e alarme com prazo explícito; parar apenas o worker e detectar indisponibilidade de atendimento.

## Achados P3

### A21. Regras de camadas e escopo de repositório divergem da implementação

Rotas, por exemplo `agentes/rotas.py`, acessam `repo` diretamente, contra a regra de rota chamar serviço. Listagens globais, resolução por token, páginas por slug e jobs globais têm exceções legítimas ao `cliente_id` obrigatório, mas o AGENTS só documenta `acessos/`. O webhook genérico também conhece a vigia da WAHA. Isso não demonstra sozinho vazamento entre clientes, mas torna a regra difícil de aplicar e auditar.

**Ação/aceite:** mover orquestração para serviços, explicitar as poucas consultas globais e sua autorização, manter operações de canal no contrato; testes de acesso cruzado e lint arquitetural que expressem a regra real.

### A22. Verificação reprodutível e higiene do repositório incompletas

Não há workflow de CI no recorte. A suíte cria o esquema por metadata; portanto, sozinha não valida migrações, embora o ciclo separado desta auditoria tenha passado. As fixtures executam operações destrutivas nos endereços `TESTE_DATABASE_URL`/`TESTE_REDIS_URL` sem uma barreira forte contra apontar para ambiente errado. `caixa.bin` é um dump de terminal rastreado, com caracteres de controle e URL; seu conteúdo não foi reproduzido no relatório e não se afirma que contenha segredo.

**Ação/aceite:** CI com bancos descartáveis, migração de base e de versão anterior, shellcheck e simulação; exigir identificação de banco de teste antes de apagar; revisar origem/sanitização do dump e removê-lo da distribuição se não necessário. Os valores de custo e modelo também merecem rastrear o provedor efetivamente usado no fallback, pois `Turno.modelo` registra a configuração principal.

## Especificação e documentação

Não foram reescritas decisões de produto para acomodar defeitos. Resolver estas divergências explicitamente antes da próxima fase:

| Fonte | Divergência | Ajuste proposto |
| --- | --- | --- |
| `spec/estado.md` e `spec/fases.md` | Estado registra validação da fase 4; checklist da fase ainda a deixa pendente | Sincronizar evidências e situação |
| `spec/estado.md`, “O que reaproveitar” | Ainda diz faltar cron de retomada e expansão de conexão que já existem | Remover instruções vencidas |
| `README.md` | WhatsApp oficial aparece como futuro | Refletir recurso construído e validações ainda pendentes |
| `spec/visao.md` | Atualização automática/manual de instalação fora de escopo, mas comando de atualização existe | Descrever alcance real e o que fica para fase 7 |
| `spec/arquitetura.md` | Retenção de mídia de 90 dias não acompanha limpeza atual após um dia | Definir separadamente retenção do arquivo, texto extraído e conversa |
| `spec/arquitetura.md` | Backup diário descrito como disponível, sem implementação correspondente | Identificar como futuro até implementar e testar restauração |
| `spec/dados.md` | Padrão de retomada do Chatwoot diverge das quatro horas do setup | Unificar padrão e semântica de ausência de prazo |
| `spec/fases.md` | Ignorar todo `fromMe` conflita com pausa por mensagem humana `source=app` | Registrar comportamento vigente |
| `spec/arquitetura.md` | Nomes/identidade dos jobs divergem de `processar_turno` e token por evento | Documentar contrato atual após corrigir A01/A03 |
| `spec/arquitetura.md` | Promete recusar arquivo de segredos com permissões abertas | Implementar checagem ou corrigir promessa; escrever com modo 600 não equivale a recusar arquivo existente |
| Specs de ferramentas/conhecimento | Busca vetorial e rotas futuras se misturam ao disponível | Marcar explicitamente fase 6, sem contar ausência planejada como defeito |
| `spec/usuarios.md` | Papel do operador não reflete conversa de teste nativa para todo canal | Atualizar permissões e casos de uso |
| `docs/whatsapp-oficial.md`, setup e histórico de versões | Falam de 01/10/2026 como data já ocorrida em revisão de 18/09/2026 | Corrigir temporalidade e verificar condições em fonte oficial antes de publicar |
| Documentação do WhatsApp | Expressões categóricas sobre ausência de bloqueio e orientação de app por número | Evitar garantia não comprovada e distinguir configuração recomendada de exigência técnica |

Preço, política comercial e detalhes atuais da Meta não foram validados conclusivamente por fonte primária nesta revisão. Essas afirmações precisam de verificação externa própria; o relatório não recomenda preço ou interpretação jurídica.

## Painel: revisão parcial de trabalho concorrente

`docs/painel-web.md`, `painel/` e, depois, `backend/app/painel/` surgiram como trabalho não publicado. Não fazem parte da versão testada acima. As observações abaixo são do conteúdo encontrado durante a revisão e precisam ser reconferidas quando esse trabalho estabilizar:

1. **Falha de criação de senha reproduzida no runtime local.** `painel/servico.py`, `cifra_senha`, usa `hashlib.scrypt(n=32768, r=8, p=1)` sem `maxmem`. A chamada equivalente com senha fictícia falhou com `memory limit exceeded`. O limite padrão de OpenSSL varia por runtime. Definir limite suficiente explicitamente e testar na imagem Ubuntu/Python da implantação. A criação de acesso chama essa função depois de consumir o código de uso único, agravando a recuperação da falha.
2. **Checagem de origem por prefixo não compara origens.** `_mesma_origem` usa `startswith(base_url)`, aceitando por exemplo origem com hostname que apenas começa pelo nome legítimo. Comparar esquema, host e porta normalizados; definir política para cabeçalhos ausentes e proxies. `SameSite=Strict` oferece defesa adicional, mas não torna essa comparação correta. Não foi demonstrado ataque completo contra o painel publicado.
3. **Unicidade do operador só por consulta.** O modelo diz ter uma linha, mas não impõe unicidade global. Dois códigos válidos e cadastros concorrentes podem passar pela consulta de ausência antes de inserir. Garantir exclusão mútua transacional/restrição, e consumir o código de forma recuperável caso a criação falhe.
4. **Protótipo não é contrato de API.** Dados de consumo, representação de destino do handoff e campos de canal divergem da API. A apresentação em reais não corresponde ao custo estimado em dólares sem conversão definida. Alterações em memória somem na navegação. Isso é aceitável como demonstração, mas invalida a premissa de conectar o mock à API sem adaptação.
5. **Escopo novo exige specs.** Painel público com login, sessão e primeiro acesso altera arquitetura, usuários, telas, implantação e fases. Registrar essa decisão e seus testes antes de tratá-lo como recurso pronto. A nova migração `0014` não foi incluída no ciclo de migração concluído pela auditoria.

## Cobertura por área e limites

| Área | O que foi examinado | Principal resultado |
| --- | --- | --- |
| Acessos e plataforma | Chave admin, cifra, configuração, logging, páginas públicas, saúde | A11, A13, A14, A20; não houve teste de penetração remoto |
| Clientes e agentes | CRUD, validação, exclusão lógica, prompts e conexão | A05, A12, A21 |
| Conversas e fila | Deduplicação, buffer, lock, histórico, watermark e envio | A01 a A04, A06, A09 |
| Canais | Contrato, Chatwoot, nativo, WAHA e Cloud API | A07, A08, A10; funcionamento real depende de VPS/provedor |
| Handoff | Pausa humana, resumo, aviso, retomada manual e por tempo | A04, A07, A10; template fora da janela continua pendente |
| IA e ferramentas | Configuração, fallback, ferramentas isoladas, mídia como dados | Limites de execução e atribuição de custo merecem reforço; não houve avaliação de qualidade com modelos reais |
| Mídia | Download, cache, extração, limites e retenção | A17, A18; revisar também arquivos órfãos em corridas de cache |
| Dados | Modelos, consultas, 13 migrações e isolamento | Migrações passaram; ampliar restrições compostas de propriedade entre entidades como defesa adicional |
| Setup e operação | Telas, cancelamento, segredos, atualização e publicação | A13, A15, A16, A19; sem teste real de terminal Hostinger nesta sessão |
| Testes e dependências | Suite, lockfile, fixtures e automação | A22; não foi executada auditoria CVE/SBOM nem build Docker |
| Specs e materiais | Oito specs, README, modelos, prompts e guia WhatsApp | Divergências listadas acima; identidade visual não foi redesenhada |
| Painel concorrente | Estudo, mock e primeiros arquivos de backend | Revisão parcial separada, sem aceite de lançamento |

A estrutura por domínio e a separação de canal são boas bases. Foram encontrados controles positivos como credenciais cifradas, comparação de assinatura, administração fora do Caddy, lock com liberação condicionada à posse e dados de mídia separados das instruções de sistema. Isso não elimina os defeitos de fluxo descritos.

Não realizados: aceites em VPS Ubuntu 24.04, build e recuperação real de contêineres, carga prolongada, indisponibilidade real dos provedores, avaliação de prompt injection com modelos reais, auditoria de infraestrutura/DNS/TLS em produção, scan de vulnerabilidades de dependências, revisão jurídica ou teste de restauração de backup. Fases 6 e 7 incompletas são escopo planejado, não regressões automaticamente.

## Ordem proposta de correção

1. A01, A02 e A05: recuperação transacional, estado de saída e separação dos arquivos por identidade de cliente.
2. A03, A04 e A06: revisão de conversa, cancelamento e exclusividade durante todo o efeito externo.
3. A07 a A12: reconciliar canal oficial, lotes, pendências, retomada, escape e validação.
4. A13 a A20: segredos/logs, atualização segura, retenção, isolamento da extração e observabilidade.
5. A21 e A22: alinhar arquitetura documentada e executável, automatizar regressão e migração.
6. Revalidar o painel estabilizado e executar os aceites reais ainda pendentes da fase 5. Implementar backup e restauração conforme fase 7 antes de depender da instalação para dados sem outra cópia.

Nenhuma fase foi declarada concluída pela auditoria. A decisão de publicar correções depende dos testes específicos acima, da suíte normal, do shellcheck e dos aceites na VPS definidos pelo projeto.
