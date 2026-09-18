# Inventário da auditoria de 18/09/2026

Referência: `e12af66311717eb7d35b68845f1b41ff01a486d2`. 166 arquivos rastreados. O identificador abaixo é o objeto Git da referência, não o hash do workspace em alteração.

Inventário de superfície: arquivos binários e lockfiles não receberam revisão textual linha a linha. Segredos `.env` foram excluídos da leitura. `.env.example` é listado como modelo público, sem reproduzir seu conteúdo. O dump `caixa.bin` teve somente formato e metadados inspecionados.

| Área | Arquivos |
| --- | ---: |
| `(raiz)` | 8 |
| `backend` | 117 |
| `deploy` | 7 |
| `docs` | 1 |
| `modelos` | 6 |
| `prompts` | 1 |
| `setup` | 18 |
| `spec` | 8 |

## Arquivos da referência

| Arquivo | Objeto Git |
| --- | --- |
| `.env.example` | `3da80f13c215` |
| `.gitattributes` | `623ecba941d9` |
| `.gitignore` | `900c4bbabe15` |
| `AGENTS.md` | `bab66f75e1ba` |
| `CLAUDE.md` | `43c994c2d361` |
| `LICENSE` | `98caa9e46588` |
| `README.md` | `0097e568151b` |
| `backend/.dockerignore` | `15c2a74649ef` |
| `backend/Dockerfile` | `a88377e43eea` |
| `backend/alembic.ini` | `d26235351349` |
| `backend/app/__init__.py` | `e69de29bb2d1` |
| `backend/app/acessos/__init__.py` | `e69de29bb2d1` |
| `backend/app/acessos/modelos.py` | `ae99ef5dfc73` |
| `backend/app/acessos/repo.py` | `43645c485745` |
| `backend/app/acessos/servico.py` | `69d54dbc4d3c` |
| `backend/app/agentes/__init__.py` | `e69de29bb2d1` |
| `backend/app/agentes/modelos.py` | `e201532d220d` |
| `backend/app/agentes/repo.py` | `0fc8789cf0f7` |
| `backend/app/agentes/rotas.py` | `5aee46c9fd6c` |
| `backend/app/agentes/servico.py` | `79f6eff14b04` |
| `backend/app/canais/__init__.py` | `e69de29bb2d1` |
| `backend/app/canais/base.py` | `4db56c67a9da` |
| `backend/app/canais/chatwoot/__init__.py` | `e69de29bb2d1` |
| `backend/app/canais/chatwoot/assinatura.py` | `a9e6ede9557b` |
| `backend/app/canais/chatwoot/canal.py` | `67d09390ca21` |
| `backend/app/canais/nativo/__init__.py` | `e69de29bb2d1` |
| `backend/app/canais/nativo/canal.py` | `9ca6835fd326` |
| `backend/app/canais/nativo/memoria.py` | `bf3492c263b9` |
| `backend/app/canais/nativo/rotas.py` | `9b587d494921` |
| `backend/app/canais/nativo/servico.py` | `7922c1f856b2` |
| `backend/app/canais/registro.py` | `bc23599dd8df` |
| `backend/app/canais/waha/__init__.py` | `e69de29bb2d1` |
| `backend/app/canais/waha/api.py` | `0c0dd93927cf` |
| `backend/app/canais/waha/assinatura.py` | `f5868a6c5c4f` |
| `backend/app/canais/waha/canal.py` | `8c7050ffd8e0` |
| `backend/app/canais/waha/rotas.py` | `cc0b95012bef` |
| `backend/app/canais/waha/vigia.py` | `a992ca36baf4` |
| `backend/app/canais/whatsapp/__init__.py` | `e69de29bb2d1` |
| `backend/app/canais/whatsapp/api.py` | `f13eb5339b4f` |
| `backend/app/canais/whatsapp/assinatura.py` | `893c425921d0` |
| `backend/app/canais/whatsapp/canal.py` | `b708acdfeccc` |
| `backend/app/canais/whatsapp/rotas.py` | `cd399d6453a3` |
| `backend/app/clientes/__init__.py` | `e69de29bb2d1` |
| `backend/app/clientes/modelos.py` | `47dd7c768ae6` |
| `backend/app/clientes/repo.py` | `8492065fb20c` |
| `backend/app/clientes/rotas.py` | `ca6f7a24e0e6` |
| `backend/app/clientes/servico.py` | `d067cbff4b4d` |
| `backend/app/consumo/__init__.py` | `e69de29bb2d1` |
| `backend/app/consumo/modelos.py` | `fcd20eec7446` |
| `backend/app/consumo/repo.py` | `f7602748b722` |
| `backend/app/consumo/rotas.py` | `5b61525ca732` |
| `backend/app/consumo/servico.py` | `f1e20d49e94b` |
| `backend/app/conversas/__init__.py` | `e69de29bb2d1` |
| `backend/app/conversas/buffer.py` | `49a0b64e7313` |
| `backend/app/conversas/divisao.py` | `0665b573669f` |
| `backend/app/conversas/modelos.py` | `e8a22687db36` |
| `backend/app/conversas/repo.py` | `0b4e0a8ea3e6` |
| `backend/app/conversas/turno.py` | `9a738058ae76` |
| `backend/app/conversas/webhook.py` | `e22ca2adff69` |
| `backend/app/handoff/__init__.py` | `e69de29bb2d1` |
| `backend/app/handoff/modelos.py` | `80dd2045e256` |
| `backend/app/handoff/repo.py` | `81f1a85b39d7` |
| `backend/app/handoff/rotas.py` | `c2add362c8e7` |
| `backend/app/handoff/servico.py` | `aa31200097d8` |
| `backend/app/handoff/tool.py` | `90fc1dd7c311` |
| `backend/app/ia/__init__.py` | `e69de29bb2d1` |
| `backend/app/ia/agente.py` | `f273eec5b827` |
| `backend/app/ia/contexto.py` | `d47be178af59` |
| `backend/app/ia/ferramentas/__init__.py` | `d13ca28707d7` |
| `backend/app/ia/ferramentas/base.py` | `433c346e659c` |
| `backend/app/ia/ferramentas/busca_web.py` | `55d13ce3f4c0` |
| `backend/app/ia/ferramentas/calculadora.py` | `c9dcb08a6b83` |
| `backend/app/ia/ferramentas/registro.py` | `dbafec144602` |
| `backend/app/ia/provedores.py` | `95309d861175` |
| `backend/app/main.py` | `0cf018f63aaa` |
| `backend/app/midia/__init__.py` | `e69de29bb2d1` |
| `backend/app/midia/extracao.py` | `3114ac4e23c4` |
| `backend/app/midia/modelos.py` | `823696181aa3` |
| `backend/app/midia/repo.py` | `fca4619e556e` |
| `backend/app/midia/servico.py` | `6e59bfc90842` |
| `backend/app/modelos.py` | `d1baed051e4a` |
| `backend/app/plataforma/__init__.py` | `e69de29bb2d1` |
| `backend/app/plataforma/admin.py` | `dd9260621436` |
| `backend/app/plataforma/banco.py` | `4d25255ef396` |
| `backend/app/plataforma/config.py` | `04485adb6a13` |
| `backend/app/plataforma/cripto.py` | `510bd21649c6` |
| `backend/app/plataforma/log.py` | `8c501b99f656` |
| `backend/app/plataforma/publico.py` | `8c2c861f9ed9` |
| `backend/app/plataforma/textos.py` | `97f09fb3b8ed` |
| `backend/app/worker.py` | `e835bfbc596c` |
| `backend/migrations/env.py` | `edc42bd93a52` |
| `backend/migrations/script.py.mako` | `e67e8893a805` |
| `backend/migrations/versions/20260916_0001_schema_inicial.py` | `e94f9e9e2adc` |
| `backend/migrations/versions/20260916_0002_modelo_fallback.py` | `cd06021816e2` |
| `backend/migrations/versions/20260916_0003_midia.py` | `ed0903b9f410` |
| `backend/migrations/versions/20260916_0004_conversa_respondido_ate.py` | `50d535a555c0` |
| `backend/migrations/versions/20260916_0005_handoff.py` | `ae138154c98e` |
| `backend/migrations/versions/20260916_0006_acesso_canal.py` | `ad313730da9c` |
| `backend/migrations/versions/20260917_0007_digitacao_ferramentas.py` | `3adde6db626a` |
| `backend/migrations/versions/20260917_0008_conversa_canal.py` | `c362cd40e57f` |
| `backend/migrations/versions/20260917_0009_ferramentas_sem_padrao.py` | `da6b370ed032` |
| `backend/migrations/versions/20260917_0010_contatos_permitidos.py` | `cb4abd11bf9c` |
| `backend/migrations/versions/20260918_0011_midia_arquivo_apagado.py` | `368d3677af16` |
| `backend/migrations/versions/20260918_0012_sem_handoff_template.py` | `c63b51d70d8e` |
| `backend/migrations/versions/20260918_0013_emojis.py` | `e7b70c7fdf52` |
| `backend/pyproject.toml` | `9a5ee763fa35` |
| `backend/testes/__init__.py` | `e69de29bb2d1` |
| `backend/testes/conftest.py` | `ec4d60f65830` |
| `backend/testes/test_acessos.py` | `346d9bf5ef71` |
| `backend/testes/test_admin_e_credenciais.py` | `170627dfb8b5` |
| `backend/testes/test_calculadora.py` | `890145084288` |
| `backend/testes/test_chatwoot_conexao.py` | `65459e8c46eb` |
| `backend/testes/test_ferramentas_e_digitacao.py` | `3200ba1f64a9` |
| `backend/testes/test_handoff.py` | `aff18eb3c324` |
| `backend/testes/test_isolamento.py` | `72b3e6669799` |
| `backend/testes/test_menu_operador.py` | `9b85077cb3a5` |
| `backend/testes/test_midia.py` | `8f75afc88546` |
| `backend/testes/test_nativo.py` | `ece9fb6577d8` |
| `backend/testes/test_publico.py` | `3350df56ab79` |
| `backend/testes/test_turno.py` | `debb495b4b6d` |
| `backend/testes/test_waha.py` | `f4fee7a82921` |
| `backend/testes/test_webhook_chatwoot.py` | `81e9eb93db7e` |
| `backend/testes/test_whatsapp.py` | `45e5fa76d3fb` |
| `backend/uv.lock` | `a271bb347012` |
| `caixa.bin` | `5362ab1d4b5e` |
| `deploy/Caddyfile` | `0cf82f3b7312` |
| `deploy/atualiza_waha.sh` | `4ed8522fbf7f` |
| `deploy/compose.sh` | `f4ffcdfdde54` |
| `deploy/docker-compose.yml` | `967819490f14` |
| `deploy/nova_migracao.sh` | `4e5eade6bc1d` |
| `deploy/publicar.sh` | `e0cd261d7939` |
| `deploy/testar.sh` | `81c1ecfe4221` |
| `docs/whatsapp-oficial.md` | `06c81c986162` |
| `modelos/AGENTS.md.tmpl` | `7b2f7db0dc74` |
| `modelos/gerar_icone.py` | `d0f61cc4c26a` |
| `modelos/icone-app.png` | `4bbd90202ef5` |
| `modelos/privacidade.html` | `d2071476f66d` |
| `modelos/prompts/persona.md` | `c1eb4e2d986a` |
| `modelos/prompts/resumo_handoff.md` | `a6c47bff6021` |
| `prompts/.gitkeep` | `e69de29bb2d1` |
| `setup/asimov.sh` | `ca2f360f39ec` |
| `setup/instalar.sh` | `24c4f744f3d1` |
| `setup/install.sh` | `f98ea1d3b420` |
| `setup/lib/agente.sh` | `0613e05b2079` |
| `setup/lib/base.sh` | `e5549534fb46` |
| `setup/lib/conversa.sh` | `f07621152e00` |
| `setup/lib/dados.sh` | `a4da4138c3c2` |
| `setup/lib/dns.sh` | `0d5fb4091be7` |
| `setup/lib/estado.sh` | `c6d13461ba65` |
| `setup/lib/final.sh` | `49ac1ba4a5b1` |
| `setup/lib/instalacao.sh` | `af01e375a587` |
| `setup/lib/menu.sh` | `1851589346a9` |
| `setup/lib/sistema.sh` | `0a2a0c41319d` |
| `setup/lib/ui.sh` | `b1f4b92b17ec` |
| `setup/lib/waha.sh` | `fd1c373d1017` |
| `setup/lib/whatsapp.sh` | `674aa27abecb` |
| `setup/testes/respostas.txt` | `85ac141a22d4` |
| `setup/testes/simula_onboarding.sh` | `deb7a7bbf116` |
| `spec/arquitetura.md` | `c8d360275be4` |
| `spec/dados.md` | `839be768f22f` |
| `spec/decisoes.md` | `514478c9f4ab` |
| `spec/estado.md` | `d0ee82bfacdc` |
| `spec/fases.md` | `50f0844c18fb` |
| `spec/telas.md` | `03450924ecc1` |
| `spec/usuarios.md` | `57d5c57bd940` |
| `spec/visao.md` | `245c4b3eee6c` |

## Workspace concorrente no fechamento do inventário

Os arquivos abaixo estavam modificados ou não rastreados. Arquivos da própria auditoria são omitidos desta lista. A lista registra presença, não aceite do conteúdo. O painel continuava em construção; novos arquivos podem surgir depois deste recorte.

```text
 M .env.example
 M backend/app/main.py
 M backend/app/modelos.py
 M backend/app/plataforma/config.py
 M backend/pyproject.toml
 M backend/testes/conftest.py
 M backend/uv.lock
 M deploy/Caddyfile
 M deploy/docker-compose.yml
?? .claude/launch.json
?? backend/app/painel/__init__.py
?? backend/app/painel/estaticos/painel.css
?? backend/app/painel/modelos.py
?? backend/app/painel/paginas/agentes.html
?? backend/app/painel/paginas/base.html
?? backend/app/painel/paginas/entrar.html
?? backend/app/painel/paginas/inicio.html
?? backend/app/painel/paginas/primeiro_acesso.html
?? backend/app/painel/repo.py
?? backend/app/painel/rotas.py
?? backend/app/painel/rotas_admin.py
?? backend/app/painel/servico.py
?? backend/migrations/versions/20260918_0014_usuario_painel.py
?? backend/testes/test_painel.py
?? deploy/caddy/painel.caddy
?? docs/painel-web.md
?? painel/README.md
?? painel/prototipo/agente.html
?? painel/prototipo/agentes.html
?? painel/prototipo/assistente.html
?? painel/prototipo/consumo.html
?? painel/prototipo/conversa.html
?? painel/prototipo/conversas.html
?? painel/prototipo/dados.js
?? painel/prototipo/index.html
?? painel/prototipo/inicio.html
?? painel/prototipo/painel.css
?? painel/prototipo/painel.js
?? painel/prototipo/primeiro-acesso.html
?? painel/prototipo/teste.html
?? painel/prototipo/whatsapp.html
?? setup/lib/painel.sh
```

## Artefatos desta auditoria

- `docs/auditoria-2026-09-18.md`: parecer, achados, recomendações e limites.
- `docs/auditoria-2026-09-18-inventario.md`: este inventário.
- `backend/testes/auditoria_2026_09_18.py`: oito sondas explícitas de comportamento defeituoso.
- `spec/estado.md`: referência ao relatório, sem mudança de versão ou fase.
