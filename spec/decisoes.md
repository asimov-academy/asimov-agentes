# Decisões

Log de mudanças na spec. Cada entrada: data, o que mudou, por quê e quais arquivos de `spec/` foram atualizados. Entrada mais nova no topo.

## 2026-09-16: Ajustes da Fase 1 na construção

- **Estado do setup em arquivo CHAVE=VALOR (`~/.asimov/estado`), não JSON.** A tela 1 roda antes de o `jq` ser instalado; um formato que o Bash lê sozinho evita dependência. Atualizados spec/arquitetura.md e spec/fases.md.
- **Token do webhook guardado duas vezes: hash SHA-256 (busca pela URL) e cifrado (o menu mostra a URL de novo).** spec/dados.md fala só em "segredo único"; nenhum dos dois fica em claro.
- **Deduplicação de Mensagem por `(conversa_id, id_externo)`**, não por agente. O id de mensagem do Chatwoot é único na instância, então o efeito é o mesmo com um índice mais simples.
- **`conversation_updated` do Chatwoot é aceito e ignorado na Fase 1.** Retomada e transferência são da Fase 3. Conversa fora de `pending` já não recebe resposta: o turno relê o status no Chatwoot antes de falar.
- **Mensagem só com anexo é gravada sem gerar turno.** Áudio, imagem e documento são da Fase 2.
- **Scripts `deploy/testar.sh` e `deploy/nova_migracao.sh` criados** além de `deploy/publicar.sh`, porque o `AGENTS.md` gerado precisa de comandos exatos e curtos para o agente de código.
- **Agent Bot do Chatwoot criado antes com URL provisória.** O Chatwoot só mostra o secret ao criar o bot, e a URL definitiva só existe depois que o agente é criado. A tela 6 orienta criar com `https://bot.<dominio>/aguardando` e trocar no fim.
- **Pacote baixado pelo `install.sh` exclui `spec/`, `AGENTS.md` e `CLAUDE.md`** (`.gitattributes` com `export-ignore`). O setup gera os arquivos do operador e não sobrescreve os de desenvolvimento quando encontra `spec/`.

## 2026-09-16: Spec inicial concluída

- Seis etapas concluídas: spec/visao.md, spec/usuarios.md, spec/telas.md, spec/dados.md, spec/arquitetura.md e spec/fases.md.
- Arquivos de contexto deste repositório seguem a mesma regra definida para o projeto gerado (spec/arquitetura.md, seção 11): `AGENTS.md` é a fonte única e `CLAUDE.md` contém só `@AGENTS.md`, em vez de duas cópias do mesmo conteúdo.
- Primeiro canal construído: Chatwoot (spec/fases.md, Fase 1).
