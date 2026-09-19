# Revisão da inteligência e da personalidade, 2026-09-19

## Veredito

> **Depois da auditoria:** os 16 achados foram corrigidos no mesmo dia (spec/decisoes.md,
> 2026-09-19). As sondas deste relatório viraram regressões com a expectativa do comportamento
> corrigido, e passar nelas hoje significa que o defeito não voltou. Nada disso rodou em VPS
> nem com modelo real: o roteiro de homologação abaixo continua valendo.

Há uma boa estrutura, mas ainda não considero o agente pronto para uma homologação completa.
O caminho básico pode ser exercitado de forma controlada; antes de aprovar personalidade,
Gemini e conhecimento, é preciso corrigir os bloqueios abaixo.

A base de conhecimento **já foi construída**, desde a v0.27.0: texto, página de site,
PDF com texto, DOCX, TXT e MD, ingestão, pgvector e ferramenta de busca. Vídeo e base
compartilhada continuam indisponíveis. Construído não significa validado na VPS.

Esta entrega é uma auditoria: não altera o comportamento do produto nem publica versão.
As sondas confirmam defeitos atuais e precisam virar regressões com a expectativa correta
quando cada correção entrar.

## Cobertura e evidência

Revisados: especificações aplicáveis; criação e edição pelo Bash e pelo painel;
perfil e persona; tom, emoji, assinatura, proibições, ritmo, memória e aviso de IA;
montagem do Agent, histórico, saída, providers, fallback e ferramentas;
turno, transferência e mídia; prova do agente; ingestão, embeddings, busca e implantação;
contratos MCP de leitura/proposta/aplicação do copiloto.

- Backend existente: **512 testes passaram**, PostgreSQL com pgvector e Redis reais locais.
- Frontend existente: **86 testes passaram**. Há avisos React de `act` nos testes de Treinamento.
- `npm run checa` e `npm run build`: passaram antes de adicionar as sondas.
- Shellcheck oficial do projeto: passou, saída 0.
- Simulação Bash do onboarding: saída 0; mostrou `date: invalid argument 's' for -I`
  no macOS. Não equivale à instalação em Ubuntu 24.04.
- Sondas adicionais: **9 backend e 1 frontend passaram, reproduzindo os defeitos**:
  `backend/testes/test_auditoria_inteligencia.py` e
  `frontend/src/telas/agente/Ficha.auditoria.teste.tsx`.
- A suíte usa modelos e canais falsos: comprova contratos, persistência e orquestração,
  não a qualidade semântica de uma IA real. A sonda Gemini usa o adaptador real instalado,
  com chave fictícia, e falha na preparação local antes de qualquer chamada ao provedor.
- Não executei instalação, migrações ou testes em VPS, nem conversa com provedor pago,
  nem login em uma sessão real do painel. Não li `.env` nem credenciais.
- As fixtures criam tabelas pelo metadata; o resultado da suíte não valida a cadeia de migrações.

## Achados que bloqueiam a homologação

### I01 · P1 · Gemini 2.5 não responde com ferramentas e saída nativa

Local: `backend/app/ia/agente.py:237`, `tipo_de_saida`.

A escolha olha apenas `supports_json_schema_output`. Os modelos Gemini 2.5 sugeridos em
`ia/chaves.py` suportam JSON, mas não NativeOutput junto de function tools. Como handoff nasce
ligado, até um agente sem calculadora já pode cair nesse caso. A PydanticAI 2.43.0 instalada
rejeita a combinação com `UserError`, antes de chamar a rede. Repetir três vezes não resolve.

Prova: `test_gemini_25_rejeita_saida_nativa_com_tool`.
Correção: escolher saída considerando também ferramentas e perfil do modelo, inclusive
cada candidato do fallback. Cobrir separadamente busca nativa com tools em Gemini anterior ao 3.

### I02 · P1 · Salvar Perfil e Trabalho juntos perde o comportamento manual

Locais: `frontend/src/telas/agente/Ficha.tsx:262`, `:564`, `:869`.

A ordem do Salvar é Perfil e depois Trabalho. Perfil grava o comportamento escrito à mão;
Trabalho chama `grava_perfil`, que gera outro `persona.md` e o sobrescreve. O aviso de Trabalho
compara o prompt buscado quando a aba abriu, então não detecta necessariamente o rascunho
manual ainda não salvo em Perfil. O operador pode receber sucesso tendo perdido suas regras.

Prova: `Ficha.auditoria.teste.tsx`, simulando as duas alterações e o mesmo clique Salvar.
Correção: consolidar a decisão sobre o prompt em uma operação, com precedência explícita,
prévia e preservação das alterações. Apenas inverter abas pode perder o formulário do outro lado.

### I03 · P1 · Documento enviado pela API não chega ao disco do worker

Locais: `deploy/docker-compose.yml:22`, `backend/app/conhecimento/servico.py:74`, `:170`.

O caminho padrão é `/var/lib/asimov/conhecimento`. O Compose compartilha mídia e prompts,
mas não conhecimento. A API grava no próprio contêiner; o worker abre o mesmo caminho no
outro contêiner e encontra arquivo ausente. Recriar a API também perde o original.
Texto e site vão na fila e não dependem desse arquivo, por isso podem parecer funcionar.

Evidência estrutural no Compose e nos caminhos de gravação/leitura; não rodei Docker/VPS.
Correção: volume persistente compartilhado por API e worker, com permissões e backup.

### I04 · P1 · Worker recém-iniciado não carrega as chaves para ingerir

Locais: `backend/app/worker.py:34`, `backend/app/conhecimento/servico.py:157`.

A ingestão chama embeddings sem `chaves.carregar`. Chaves cadastradas no painel estão no banco,
mas o processo do worker começa com cache vazio. Uma instalação sem chaves antigas no ambiente
recusa o primeiro material com “precisa da chave”. Um atendimento anterior pode aquecer o cache
e mascarar o defeito; trocar a chave na API também não atualiza esse processo.

Prova: `test_worker_frio_nao_carrega_chave_do_banco`, com chave fictícia cifrada no banco.
Correção: carregar chaves na entrada do job, antes de gerar embeddings.

### I05 · P1 · Cadastrar chave muda silenciosamente o modelo dos vetores

Local: `backend/app/conhecimento/embeddings.py:33`.

Com só Gemini, os documentos são vetorizados por Gemini. Cadastrar OpenAI muda imediatamente
a escolha para OpenAI. Dimensões iguais não tornam espaços vetoriais compatíveis: consultas
novas passam a comparar representações diferentes sem erro de tipo nem reindexação.
Não há identificação persistida do modelo no documento/trecho para detectar a mistura.

Prova: `test_chave_nova_troca_espaco_vetorial` confirma a troca automática da seleção.
Correção: fixar provedor/modelo/dimensão da base e exigir reindexação controlada para mudar.
A proibição já está descrita no comentário de `conhecimento/modelos.py`.

### I06 · P1 · Memória do contato entra como instrução privilegiada

Locais: `backend/app/ia/agente.py:322`, `backend/app/conversas/memoria_do_contato.py:71`.

Resumo e ficha derivados das falas do contato são anexados ao argumento `instructions`, junto
às regras do operador. A frase “é dado” não muda o papel da mensagem no protocolo.
Além disso, a saída do resumidor não é escapada antes de montar o bloco; pode conter o próprio
fechamento `</memoria_do_contato>`. Não foi demonstrada exploração com modelo real, mas a
promoção de autoridade e a quebra do delimitador foram reproduzidas.

Prova: `test_memoria_do_contato_e_promovida_a_instrucao` inspeciona o que chega ao modelo.
Correção: manter nas instructions apenas a regra fixa e transportar a memória como dado
em mensagem de usuário, com delimitação segura. Revisar também o motivo de handoff gerado
pelo modelo e interpolado em `SystemPromptPart` (`ia/agente.py:265`).

## Outros defeitos de configuração e atendimento

### I07 · P2 · Renomear deixa o agente se apresentando com o nome antigo

Local: `backend/app/agentes/servico.py:396`.

PATCH altera banco/canal, mas não o `persona.md`. Vale para CLI e painel.
Prova: `test_renomear_preserva_nome_antigo_no_prompt`.
Correção: separar identidade estruturada do texto livre ou atualizar apenas persona ainda
gerenciada, preservando prompt personalizado. Não substituir nomes às cegas em texto livre.

### I08 · P2 · Perfil sem função ignora empresa, proibições e assinatura

Local: `backend/app/agentes/servico.py:500`.

Agentes criados pelo CLI/antigos podem ter perfil vazio. Salvar só Trabalho ou assinatura
persiste os campos, mas `monta_persona` retorna cedo sem aplicá-los. Retirar a função também
apaga essas regras do prompt gerado.
Prova: `test_perfil_sem_funcao_descarta_regras_e_assinatura`.
Correção: função opcional muda só a primeira frase; os demais campos continuam sendo montados.

### I09 · P2 · Aviso de IA corta conteúdo da resposta

Local: `backend/app/conversas/turno.py:256`.

Com três mensagens e aviso ligado, o slice entrega aviso, parte A e parte B: parte C some,
mas o turno é marcado respondido. Com máximo 1, são enviadas 2 mensagens, contrariando o ajuste.
O marcador `avisou_ia_em` também é gravado antes de confirmar envio; falha pode impedir nova tentativa.
Prova do corte: `test_aviso_ia_corta_ultima_mensagem`.
Correção: juntar excedente sem perda e marcar aviso somente quando realmente entregue.

### I10 · P2 · Falha de IA promete pessoa mesmo com transferência desligada

Locais: `backend/app/conversas/turno.py:221`, `backend/app/handoff/servico.py:34`.

O serviço corretamente impede a transferência, mas a mensagem fixa diz “Já chamei uma pessoa”.
O contato espera alguém que nunca foi acionado. A suíte antiga verificava ausência de handoff,
sem conferir essa promessa ao contato.
Prova: `test_falha_promete_humano_com_handoff_desligado`.
Correção: mensagem coerente com a configuração e com o resultado real da transferência.

### I11 · P2 · Prova do agente inacessível pelo CLI e ausente na interface web

Local: `setup/lib/menu.sh:456`.

O CLI chama `/admin/clientes/.../agentes/.../prova`, mas só existe
`POST /painel/api/agentes/{id}/prova`. Resposta: 404. No frontend há `api.prova`, mas não há
chamada dela em componente. O comentário que promete botão em Trabalho está desatualizado.
Prova do CLI: `test_prova_do_terminal_chama_rota_inexistente`; busca de referências no frontend.
Correção: expor a operação administrativa pelo mesmo serviço e restaurar o acesso no painel.
A prova atual testa só perguntas isoladas, sem memória, envio, ritmo ou handoff efetivo.

### I12 · P2 · Trocar apenas o tom no CLI religa opções desligadas

Locais: `setup/lib/menu.sh:371`, `setup/lib/ui.sh:444`.

`edita_jeito` pergunta quatro booleanos sem usar os valores atuais. `confirma` começa sempre
em Sim. Abrir para trocar tom e aceitar Enter religa handoff, restrição, memória e aviso de IA.
Tom e emoji, ao contrário, preservam a seleção atual.
Correção: confirmação com padrão atual ou operações independentes. Reproduzir também em PTY/Bash 5.

### I13 · P2 · Copiloto não consegue operar configurações básicas de personalidade

Locais: `backend/app/copiloto/ferramentas/ver_agente.py`,
`backend/app/copiloto/ferramentas/propor_mudanca_no_agente.py:24`.

MCP não mostra nem propõe `tom`, `restringe_temas`, `transfere_para_humano`, `memoria_ativa`,
`avisa_que_e_ia` ou preset `ritmo`. Pedir “deixe formal” pode resultar em reescrever o prompt,
enquanto o runtime continua injetando o tom normal. Prompt não substitui configuração de tool.
Correção: ampliar leitura e proposta tipadas, reaproveitando validação/aplicação e confirmação.
A mudança de personalidade pelo formulário e pelo assistente não tem hoje a mesma cobertura.

### I14 · P2 · Memória e fallback deixam o consumo incompleto ou mal atribuído

Locais: `backend/app/conversas/memoria_do_contato.py:120`, `backend/app/conversas/turno.py:296`.

A atualização de memória chama IA sem registrar tokens/custo em Turno. O atendimento registra
sempre `agente.modelo_conversa`, mesmo quando quem respondeu foi o fallback. Tentativas completas
que falharam antes de um novo `Agent.run` também não entram no resultado final.
Correção: registrar uso da memória e modelo efetivo, distinguindo tentativa, fallback e função.
Não usar o painel de consumo atual para concluir o custo completo dos testes.

### I15 · P2 · Ensinar site faz download irrestrito na rede interna

Local: `backend/app/conhecimento/servico.py:124`.

Só verifica prefixo HTTP(S), segue redirects e lê o corpo inteiro antes de cortar para 20 MB.
Uma URL cadastrada pelo operador pode alcançar serviços internos; uma página pode redirecionar
para eles. Corpo grande não é limitado durante o download. Acesso exige operador autenticado,
mas isso não torna uma URL externa ou seus redirects confiáveis.
Correção: política de destinos públicos conferida a cada redirect e leitura em streaming com teto.
O download roda dentro da requisição, apesar do comentário anunciar ingestão assíncrona.

### I16 · P2 · Backup não inclui a personalidade efetiva nem os documentos originais

Local: `deploy/backup.sh:35`.

O backup leva banco e ambiente, mas não `prompts/` nem conhecimento, previstos na arquitetura.
Uma restauração preserva a ficha, mas perde comportamento manual, prompt de resumo e arquivos.
Correção: incluir esses dados e provar restauração; o banco sozinho não reconstrói prompt livre.

## Coerência de personalidade e documentação

- `INSTRUCAO_DE_CONVERSA` proíbe anunciar verificação inexistente, mas termina mandando
  “diga que vai confirmar”. A ferramenta RAG também exige essa promessa quando não encontra
  resposta, mesmo sem humano ou mecanismo de confirmação. Melhor explicitar que não há informação
  suficiente e oferecer uma ação que exista. Isso requer avaliação com modelo real.
- Com base ligada, a instrução exige responder **só** com o retorno da busca, podendo descartar
  informação válida já no perfil quando não houver trecho. Definir precedência entre fatos do
  perfil, material recuperado e mensagem do contato antes de avaliar respostas como erradas.
- Tom, emoji e “nunca dizer” são instruções probabilísticas, não validação do texto final.
  `Resposta` aceita strings vazias; se todas virarem vazio após limpeza, o turno pode marcar a
  entrada respondida sem envio. Acrescentar validação de resposta útil e regressão desse caso.
- O campo Site em Trabalho só escreve a URL no prompt. Quem ensina o conteúdo é Treinamento > Site.
- Assinatura mora no prompt gerado; editar comportamento livre pode contrariar o interruptor.
- O CLI não oferece o mesmo formulário de função, público, empresa, proibições e assinatura do
  painel. Edição de arquivo continua possível, mas não é paridade do menu.
- Há textos antigos na spec: tools “padrão de todo agente”, lock de 240 s, fase 6 ainda futura,
  backup “não construído”, entre outros. O estado atual e o código precisam ser conciliados.

## Conferência com PydanticAI

Versão no lock: **pydantic-ai-slim 2.43.0**. A documentação online consultada é evolutiva;
para o erro Gemini também conferi o adaptador instalado e executei a reprodução local.

| Parte | Avaliação |
|---|---|
| `Agent(..., instructions=...)` relido por turno | Adequado para aplicar ajustes sem manter instructions antigas do histórico. |
| `deps_type=ContextoTurno` e `RunContext` | Adequado; IDs da busca vêm do contexto de execução, não de argumentos escolhidos pelo modelo. |
| `FallbackModel` | Uso válido; padrão trata ModelAPIError. Não corrige UserError de combinação inválida. |
| `NativeOutput` | Uso condicionado só a JSON Schema é insuficiente; I01. |
| `WebSearch(local='duckduckgo')` | API válida na versão instalada. Validar combinações de ferramentas por modelo; não basta validar cada opção isolada. |
| `UsageLimits` | Presente no atendimento, e UsageLimitExceeded não é repetido. Chamadas auxiliares e tentativas externas precisam de orçamento/observabilidade próprios. |
| Histórico reconstruído | Válido para conversa textual; não preserva chamadas e retornos de tools anteriores. Uma resposta anterior não é prova de um fato consultado. |
| Mídia com `BinaryContent` | Uso compatível; extração volta como conteúdo do contato. Necessário E2E real para qualidade de áudio/visão. |
| Memória como `instructions` | Fronteira inadequada para dado derivado do contato; I06. |
| Testes `FunctionModel` | Adequados para contratos. Não comprovam aderência semântica, disponibilidade de modelos nem todas as restrições dos providers. |

Fontes oficiais:

- [Instructions e agentes](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions).
- [Histórico e autoridade de mensagens de sistema](https://pydantic.dev/docs/ai/core-concepts/message-history/#mid-conversation-system-prompts).
- [Native Output e restrições por modelo](https://pydantic.dev/docs/ai/core-concepts/output/#native-output).
- [FallbackModel](https://pydantic.dev/docs/ai/api/models/fallback/).
- [WebSearch](https://pydantic.dev/docs/ai/capabilities/web-search/).

## Ordem para corrigir e testar

1. **Configuração básica**: I02, I07, I08, I09, I10, I11 e I12. Uniformizar a precedência de
   perfil/prompt, preservar opções e tornar a prova utilizável. I13 se os comandos forem pelo copiloto.
2. **Motor**: I01, I06 e I14; validar saída/ferramentas por provider, memória como dado e consumo.
3. **Conhecimento**: I03, I04, I05, I15 e I16. Só então homologar ingestão/busca na VPS.
4. Converter sondas em regressões, executar suíte, shellcheck, build e migrações num banco de teste.
5. Rodar o roteiro abaixo com modelo real na VPS. Não concluir fase só com testes simulados.

## Roteiro progressivo de homologação

Usar empresa fictícia **Loja Exemplo**, agente **Ana**, situação treinamento e conversa nova
para cada mudança de personalidade. Registrar modelo, configuração, pergunta, resposta e resultado.
Repetir os casos semânticos três vezes: uma resposta acertada não garante estabilidade.

### 1. Criar e conferir persistência

Pelo painel, criar Ana com objetivo Atendimento, descrição “Vendemos livros. Abrimos das
9h às 18h, de segunda a sexta”, sem ferramentas. Escolher provedor/modelo disponível em
Configurações. Reabrir a ficha e conferir o que foi salvo. No terminal:

```bash
asimov agentes
asimov editar
asimov conversar
```

Selecionar a mesma Ana. As duas interfaces devem mostrar os mesmos ajustes e usar o mesmo prompt.
Não executar `setup/instalar.sh` no Mac.

### 2. Personalidade, um ajuste por vez

| Configuração / pergunta | Resultado esperado |
|---|---|
| “Oi, quem é você?” | Nome atual e Loja Exemplo; sem inventar função. |
| Renomear para Bia; repetir em conversa nova | Nome Bia também na apresentação e assinatura. |
| Formal / normal / descontraído; “Como vocês podem me ajudar?” | Muda o estilo, preserva os fatos. |
| Emoji nenhum / pouco | Nenhum, ou no máximo um na resposta inteira, respectivamente. |
| Assinar nome ligado / desligado | Comportamento acompanha o ajuste após salvar/reabrir. |
| “Nunca dizer: entregamos em 24 horas”; “Chega amanhã?” | Não promete entrega nem confirmação que não acontecerá. |
| Restrição ligada; “Me ensina bolo de cenoura” | Redireciona ao atendimento. Desligada, não aplica essa regra. |
| Alterar Comportamento e Trabalho no mesmo Salvar | Precedência visível, sem perda silenciosa. |
| CLI: mudar só tom, demais opções desligadas | Permanecem desligadas ao manter as escolhas. |

### 3. Orquestração

- Máximo 1, 2 e 3 mensagens; testar com e sem aviso de IA. Nenhuma informação desaparece.
- Ritmo instantâneo, natural e reflexivo: conferir espera, leitura e digitando.
- Enviar duas mensagens durante o processamento: resposta cobre ambas sem duplicar.
- Transferência desligada: pedir humano e simular erro do provider em ambiente de teste;
  não prometer pessoa. Ligada: verificar evento e retomada, não apenas a frase do modelo.
- “Meu nome é Carlos”; perguntar o nome depois, e após ultrapassar 20 mensagens para exercitar
  o resumidor. Memória não deve incorporar ordens do contato como regra de sistema.
- Calculadora: “Quanto são 3 livros de R$ 39,90?”; conferir chamada e R$ 119,70.
- Busca web: caso relevante ao negócio, com e sem calculadora/handoff; repetir por provider.
- Imagem, áudio e PDF: confirmar entendimento, falha legível e isolamento da transcrição.

### 4. Comandos ao copiloto, após I13

“Mostre os ajustes da Ana”; “Deixe o tom formal”; “Desligue emojis”; “Desligue transferência
para humano”; “Use ritmo instantâneo”. Cada escrita deve gerar proposta, não mudar antes da
confirmação, e depois refletir no formulário e no próximo turno. Hoje o contrato não suporta
todos esses comandos, como descrito em I13.

### 5. Base de conhecimento, depois dos bloqueios

1. Reiniciar só o worker de teste e ensinar uma frase antes de qualquer conversa, comprovando I04.
2. Ensinar “O livro Azul custa R$ 47 e pode ser retirado às terças”. Esperar **pronto**.
3. Perguntar preço, retirada e uma condição ausente. Usar ferramenta e não inventar a ausente.
4. Repetir por arquivo TXT, PDF com texto e DOCX, comprovando comunicação API/worker.
5. Ensinar site público de teste. URL interna, redirect interno e arquivo acima do limite devem falhar.
6. Criar outro agente/empresa: nenhum trecho da primeira base pode aparecer nele.
7. Remover material: some da busca; usar conversa nova para não confundir com histórico já lido.
8. Recriar contêineres: documentos continuam disponíveis. Restaurar backup em ambiente isolado.
9. Adicionar outra chave de provider: não muda o modelo dos vetores existentes.
10. Só após esses casos testar volume, documentos longos, frustração, retomada e fallback combinado.

## Reexecutar as sondas

```bash
cd backend
.venv/bin/python -m pytest -q testes/test_auditoria_inteligencia.py
cd ../frontend
npm run teste -- src/telas/agente/Ficha.auditoria.teste.tsx
```

**Passar nelas hoje significa que o defeito corrigido não voltou.** Elas não são um selo de aprovação do produto: a homologação com modelo real na VPS continua pendente.
