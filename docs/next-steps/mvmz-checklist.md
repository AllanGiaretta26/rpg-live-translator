# Próximas sessões: checklist MV/MZ

## Estabilização do modo MV/MZ

- [x] Ocultar ou reescrever o aviso de overlay sobre área capturada quando o modo ativo for `RPG Maker MV/MZ`.
- [x] Confirmar em teste manual que `Fonte MV/MZ` sempre corresponde ao texto visível no jogo.
- [x] Confirmar em teste manual que `Traducao MV/MZ` não reaproveita cache contaminado.
- [x] ~~Validar falas com uma linha, múltiplas linhas, escolhas e~~ texto rolante.
- [x] Testar avanço rápido de diálogos para confirmar que traduções antigas não sobrescrevem falas novas.

## Cache e diagnósticos

- [x] Adicionar limpeza manual de traduções contaminadas no cache.
- [x] Isolar cache de tradução MV/MZ por caminho do projeto ativo.
- [x] Adicionar ação para reprocessar a fala atual quando o cache for inválido.
- [x] Persistir erros de tradução em lote com `entry_id`, origem, texto fonte e mensagem do erro.
- [x] Adicionar botão ou aba para consultar os erros do último lote.
- [x] Mostrar contagem de entradas do catálogo com tradução já cacheada.
- [x] Adicionar busca de entrada do catálogo por ID.
- [x] Adicionar retradução forçada por ID do catálogo.
- [x] Garantir que `Reprocessar fala atual` substitui cache antigo com nova tradução.

## Tradução em lote

- [x] Adicionar filtro de lote por tipo de texto: `message`, `choice`, `speaker`, `scrolling_text`.
- [x] Adicionar filtros de lote para database: `item_name`, `item_description`, `skill_name`, `skill_description`.
- [x] Adicionar filtros de lote para `actor_name` e `system_term`.
- [x] Adicionar filtros de lote para `weapon`, `armor`, `state`, `class`, `enemy`, `skill_message` e `troop`.
- [x] Definir se `speaker` deve entrar no lote por padrão ou ficar desativado.
- [x] Adicionar pausa/resumo do lote sem perder progresso.
- [x] Evitar retraduzir entradas cujo cache foi validado como bom.
- [x] Melhorar status final do lote com tempo total e média por tradução.
- [x] Paginar visualização do catálogo em blocos de 500 entradas.

## Plugin MV/MZ

- [x] Testar compatibilidade do `LiveTranslatorBridge.js` em jogos MV e MZ diferentes.
- [x] Verificar comportamento com jogos Steam sem acesso ao Plugin Manager.
- [ ] Criar instalador/registrador de plugin para copiar o arquivo e atualizar `plugins.js` com backup.
- [ ] Adicionar desinstalador/restaurador do plugin usando o backup.
- [x] Documentar recuperação caso update da Steam sobrescreva `plugins.js`.

## UX do modo RPG Maker

- [x] Separar melhor na UI o modo Universal do modo MV/MZ.
- [x] Desativar controles de captura quando o modo MV/MZ estiver ativo.
- [x] Deixar a interface mais elegante e intuitiva.
- [ ] Destacar endpoint da bridge e estado do servidor local.
- [ ] Adicionar botão para copiar o endpoint da bridge.
- [ ] Adicionar status de plugin conectado/última requisição recebida.

## Futuro sem overlay

- [x] Avaliar exportação de patch traduzido para pasta separada, sem sobrescrever o jogo original.
- [x] Adicionar geração de patch JSON MV/MZ para mensagens, escolhas, texto rolante e speaker opcional.
- [x] Adicionar aplicação de patch com backup automático e restauração do último backup.
- [x] Expandir patch para database como `Skills.json` e `Items.json`.
- [x] Expandir patch para `Actors.json` e termos de `System.json`.
- [x] Preservar códigos RPG Maker como `\N[1]` durante tradução/cache/patch.
- [x] Preservar placeholders de batalha como `%1`, `%2` e `%3`.
- [x] Quebrar linhas longas de mensagens ao gerar patch.
- [x] Preservar prefixos visuais como `\#` em continuações geradas pela quebra
  automática do patch.
- [x] Evitar que textos só de pontuação/controle, como `...`, sejam enviados ao
  modelo e virem falas inventadas.
- [x] Rejeitar marcadores visuais inesperados como `€`, `¥` e `￥` quando não
  existem no texto original.
- [x] Expandir catálogo e patch para `Weapons.json`, `Armors.json` e `States.json`.
- [x] Expandir catálogo e patch para `Classes.json`, `Enemies.json` e eventos de batalha em `Troops.json`.
- [x] Expandir catálogo e patch para cenas custom em `Scenario.json`.
- [x] Usar prompts por tipo de texto para nomes, descrições, termos e mensagens de batalha.
- [x] Documentar riscos de patch em jogos com plugins customizados.

## Robustez do projeto

### Guard-rails de arquitetura

- [x] Criar teste de arquitetura em pytest que falha se `domain/` importar
  PySide6, mss, sqlite3, requests ou PIL (checagem da seção 2 da ARCHITECTURE.md).
  Ver `tests/unit/test_architecture_rules.py`.
- [x] Criar teste de arquitetura que falha se houver import de topo de módulo de
  `pyside6`/`mss` fora de `ui/` e `infrastructure/capture/`.
- [x] Criar teste que garante que `bootstrap()` completo roda sem desktop nem
  Ollama, com fallbacks `ConsoleOverlay`/`ConsoleUiApp` ativos.
  Ver `tests/unit/app/test_bootstrap_headless.py`. Nota: `mss` é importado lazy
  dentro de `capture_region`, então o fallback `NullScreenCaptureService` não é
  acionado pela ausência da lib — o bootstrap headless funciona mesmo assim.

### Correções em infrastructure/translation (análise de 2026-06-10)

- [x] Mover `application/translation_quality.py` para `domain/` — feito em
  2026-06-10; `ollama_translator.py` agora importa do Domain e o guard-rail
  `test_infrastructure_does_not_import_application_or_ui` passou a valer
  (`tests/unit/test_architecture_rules.py`).
- [x] Mover `client.generate(prompt)` para dentro do `try` no loop de retry do
  `OllamaTranslator.translate` — JSON inválido do modelo deve acionar o prompt
  de retry, não abortar o loop. Feito em 2026-06-10.
- [x] Tratar `error.HTTPError` separado de `error.URLError` no `OllamaClient`,
  lendo o corpo do erro para distinguir "Ollama fora do ar" de "modelo não
  instalado" (404) — feito em 2026-06-10; 404 vira `OllamaModelNotFoundError`,
  outros status viram `OllamaError` com código e detalhe do corpo.
- [x] Classificar timeout embrulhado em `URLError(reason=TimeoutError)` como
  `OllamaTimeoutError`, não como erro de conexão — feito em 2026-06-10.
- [x] Rejeitar tradução se marcadores `__LT_RPG_TOKEN` (ou variação mutilada)
  sobrarem no texto após o `restore()` da máscara. Feito em 2026-06-10 —
  detecção case-insensitive de `LT_RPG_TOKEN` após o restore.
- [x] Simplificar prompt do `OllamaVisionTextExtractor` para OCR-only — feito
  em 2026-06-12; `build_vision_ocr_prompt` pede apenas `source_text` e instrui
  a transcrever sem traduzir/corrigir (a tradução já era feita em chamada
  separada pelo `OllamaTranslator`).
- [x] Enviar `options.temperature = 0` e `keep_alive` no `generate()` para
  traduções determinísticas e modelo carregado entre frames — feito em
  2026-06-12 (`keep_alive` padrão de 15m, campo do `OllamaClient`).
- [x] Usar timeout curto dedicado (1-2s) em `is_available()` em vez do timeout
  cheio de requisição — feito em 2026-06-12 (2s, limitado pelo timeout
  configurado se este for menor).
- [x] Deduplicar `_DESCRIPTION_TYPES` (definido em `ollama_translator.py` e
  `prompt_builder.py`) e o bloco repetido de instruções "Preserve exatamente...".
  Feito em 2026-06-10: conjuntos públicos em `domain/translation_quality.py`
  (`NAME_OR_TERM_TYPES`, `DESCRIPTION_TYPES`, `BATTLE_MESSAGE_TYPES`) e blocos
  compartilhados `_ESCAPE_CODE_GUARDRAILS`/`_TOKEN_AND_SYMBOL_GUARDRAILS` no
  `prompt_builder` (o prompt de retry passou a usar a lista completa de códigos).
- [x] Corrigir "português brasileiro" hardcoded em `build_translation_prompt`,
  que ignora o parâmetro `target_language`. Feito em 2026-06-10.
- [x] Derivar o limite de 95 caracteres do `build_compact_description_prompt` —
  feito em 2026-06-10, derivado dos limites de descrição do domain (52 x 2 - 9),
  que são os mesmos usados pela validação `looks_like_overlong_description`.

### Resiliência do Ollama

- [ ] Adicionar retry com backoff curto no `OllamaClient` para falhas
  transitórias (conexão recusada, timeout), sem travar o tick de captura.
- [ ] Diferenciar na UI "Ollama fora do ar" de "modelo não instalado".
- [ ] Expor tempo da última resposta do Ollama no painel de Status.

### Persistência e dados

- [ ] Adicionar versionamento de schema no SQLite (tabela `schema_version`)
  para migrações futuras seguras.
- [ ] Adicionar ação de backup/export do banco de cache (`data/app.sqlite3`).
- [ ] Tratar banco corrompido na inicialização: renomear e recriar em vez de
  quebrar o app.

### Qualidade de tradução

- [x] Melhorar o prompt principal de tradução — feito em 2026-06-12:
  diretrizes de estilo (`_STYLE_GUIDELINES`: naturalidade, tom da cena,
  siglas HP/MP/TP/EXP), texto a traduzir movido para o fim do prompt (modelos
  locais seguem melhor instruções que antecedem o payload) e `temperature = 0`
  no `generate()`. Frases distintivas das diretrizes entraram em
  `_PROMPT_LEAK_MARKERS` para rejeitar eco do prompt.
- [x] Enviar falas anteriores como contexto na tradução em lote MV/MZ — feito
  em 2026-06-12: `_build_dialogue_contexts` no `ModeSettingsService` acumula
  até `batch_context_lines` falas (default 4, env
  `LIVE_TRANSLATOR_RPG_MAKER_BATCH_CONTEXT_LINES`, 0 desativa) do mesmo bloco
  evento/página, sem vazar entre eventos; lotes filtrados (ex.: só choices)
  ainda recebem as messages vizinhas. Tradução individual segue sem contexto
  (follow-up possível).
- [x] Adicionar métrica de rejeição do `translation_quality` no status do lote
  (quantas traduções foram descartadas e por qual regra) — feito em 2026-06-12:
  `invalid_translation_reason` no domain nomeia a regra; o lote conta os
  descartes de cache em `CatalogTranslationResult.rejected_by_rule` e o status
  final na UI mostra "cache descartado por regra: ...".
- [x] Criar corpus de regressão com pares fonte/tradução reais para validar
  mudanças de prompt sem rodar o jogo — feito em 2026-06-12:
  `tests/data/translation_regression_corpus.json` (pares válidos que não podem
  virar falso positivo + pares inválidos com a regra esperada), rodado por
  `tests/unit/domain/test_translation_regression_corpus.py`. Ao mudar prompt
  ou heurística, adicionar pares novos ao corpus.

### CI e empacotamento

- [ ] Adicionar workflow de CI (GitHub Actions) rodando `ruff check` e `pytest`
  em Windows.
- [ ] Avaliar empacotamento com PyInstaller para distribuição sem Python
  instalado.

## Validação antes de merge

- [x] Rodar `.venv\Scripts\python.exe -m ruff check .`.
- [x] Rodar `.venv\Scripts\python.exe -m pytest`.
- [x] Testar manualmente o modo Universal para garantir que OCR/captura não regrediu.
- [x] Testar manualmente o modo MV/MZ com plugin atualizado.
- [x] Atualizar README, CHANGELOG e relatório da fase antes do commit final.
