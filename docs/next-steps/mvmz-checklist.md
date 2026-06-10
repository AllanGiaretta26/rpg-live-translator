# Proximas Sessoes: Checklist MV/MZ

## Estabilizacao do modo MV/MZ

- [x] Ocultar ou reescrever o aviso de overlay sobre area capturada quando o modo ativo for `RPG Maker MV/MZ`.
- [x] Confirmar em teste manual que `Fonte MV/MZ` sempre corresponde ao texto visivel no jogo.
- [x] Confirmar em teste manual que `Traducao MV/MZ` nao reaproveita cache contaminado.
- [x] ~~Validar falas com uma linha, multiplas linhas, escolhas e~~ texto rolante.
- [x] Testar avanco rapido de dialogos para confirmar que traducoes antigas nao sobrescrevem falas novas.

## Cache e diagnosticoS

- [x] Adicionar limpeza manual de traducoes contaminadas no cache.
- [x] Isolar cache de traducao MV/MZ por caminho do projeto ativo.
- [x] Adicionar acao para reprocessar a fala atual quando o cache for invalido.
- [x] Persistir erros de traducao em lote com `entry_id`, origem, texto fonte e mensagem do erro.
- [x] Adicionar botao ou aba para consultar os erros do ultimo lote.
- [x] Mostrar contagem de entradas do catalogo com traducao ja cacheada.
- [x] Adicionar busca de entrada do catalogo por ID.
- [x] Adicionar retraducao forcada por ID do catalogo.
- [x] Garantir que `Reprocessar fala atual` substitui cache antigo com nova traducao.

## Traducao em lote

- [x] Adicionar filtro de lote por tipo de texto: `message`, `choice`, `speaker`, `scrolling_text`.
- [x] Adicionar filtros de lote para database: `item_name`, `item_description`, `skill_name`, `skill_description`.
- [x] Adicionar filtros de lote para `actor_name` e `system_term`.
- [x] Adicionar filtros de lote para `weapon`, `armor`, `state`, `class`, `enemy`, `skill_message` e `troop`.
- [x] Definir se `speaker` deve entrar no lote por padrao ou ficar desativado.
- [x] Adicionar pausa/resumo do lote sem perder progresso.
- [x] Evitar retraduzir entradas cujo cache foi validado como bom.
- [x] Melhorar status final do lote com tempo total e media por traducao.
- [x] Paginar visualizacao do catalogo em blocos de 500 entradas.

## Plugin MV/MZ

- [x] Testar compatibilidade do `LiveTranslatorBridge.js` em jogos MV e MZ diferentes.
- [x] Verificar comportamento com jogos Steam sem acesso ao Plugin Manager.
- [ ] Criar instalador/registrador de plugin para copiar o arquivo e atualizar `plugins.js` com backup.
- [ ] Adicionar desinstalador/restaurador do plugin usando o backup.
- [ ] Documentar recuperacao caso update da Steam sobrescreva `plugins.js`.

## UX do modo RPG Maker

- [x] Separar melhor na UI o modo Universal do modo MV/MZ.
- [x] Desativar controles de captura quando o modo MV/MZ estiver ativo.
- [x] Deixar a interface mais elegante e intuitiva.
- [ ] Destacar endpoint da bridge e estado do servidor local.
- [ ] Adicionar botao para copiar o endpoint da bridge.
- [ ] Adicionar status de plugin conectado/ultima requisicao recebida.

## Futuro sem overlay

- [x] Avaliar exportacao de patch traduzido para pasta separada, sem sobrescrever o jogo original.
- [x] Adicionar geracao de patch JSON MV/MZ para mensagens, escolhas, texto rolante e speaker opcional.
- [x] Adicionar aplicacao de patch com backup automatico e restauracao do ultimo backup.
- [x] Expandir patch para database como `Skills.json` e `Items.json`.
- [x] Expandir patch para `Actors.json` e termos de `System.json`.
- [x] Preservar codigos RPG Maker como `\N[1]` durante traducao/cache/patch.
- [x] Preservar placeholders de batalha como `%1`, `%2` e `%3`.
- [x] Quebrar linhas longas de mensagens ao gerar patch.
- [x] Preservar prefixos visuais como `\#` em continuacoes geradas pela quebra
  automatica do patch.
- [x] Evitar que textos so de pontuacao/controle, como `...`, sejam enviados ao
  modelo e virem falas inventadas.
- [x] Rejeitar marcadores visuais inesperados como `€`, `¥` e `￥` quando nao
  existem no texto original.
- [x] Expandir catalogo e patch para `Weapons.json`, `Armors.json` e `States.json`.
- [x] Expandir catalogo e patch para `Classes.json`, `Enemies.json` e eventos de batalha em `Troops.json`.
- [x] Expandir catalogo e patch para cenas custom em `Scenario.json`.
- [x] Usar prompts por tipo de texto para nomes, descricoes, termos e mensagens de batalha.
- [x] Documentar riscos de patch em jogos com plugins customizados.

## Robustez do projeto

### Guard-rails de arquitetura

- [x] Criar teste de arquitetura em pytest que falha se `domain/` importar
  PySide6, mss, sqlite3, requests ou PIL (checagem da secao 2 da ARCHITECTURE.md).
  Ver `tests/unit/test_architecture_rules.py`.
- [x] Criar teste de arquitetura que falha se houver import de topo de modulo de
  `pyside6`/`mss` fora de `ui/` e `infrastructure/capture/`.
- [x] Criar teste que garante que `bootstrap()` completo roda sem desktop nem
  Ollama, com fallbacks `ConsoleOverlay`/`ConsoleUiApp` ativos.
  Ver `tests/unit/app/test_bootstrap_headless.py`. Nota: `mss` e importado lazy
  dentro de `capture_region`, entao o fallback `NullScreenCaptureService` nao e
  acionado pela ausencia da lib — o bootstrap headless funciona mesmo assim.

### Correcoes infrastructure/translation (analise de 2026-06-10)

- [x] Mover `application/translation_quality.py` para `domain/` — feito em
  2026-06-10; `ollama_translator.py` agora importa do Domain e o guard-rail
  `test_infrastructure_does_not_import_application_or_ui` passou a valer
  (`tests/unit/test_architecture_rules.py`).
- [x] Mover `client.generate(prompt)` para dentro do `try` no loop de retry do
  `OllamaTranslator.translate` — JSON invalido do modelo deve acionar o prompt
  de retry, nao abortar o loop. Feito em 2026-06-10.
- [x] Tratar `error.HTTPError` separado de `error.URLError` no `OllamaClient`,
  lendo o corpo do erro para distinguir "Ollama fora do ar" de "modelo nao
  instalado" (404) — feito em 2026-06-10; 404 vira `OllamaModelNotFoundError`,
  outros status viram `OllamaError` com codigo e detalhe do corpo.
- [x] Classificar timeout embrulhado em `URLError(reason=TimeoutError)` como
  `OllamaTimeoutError`, nao como erro de conexao — feito em 2026-06-10.
- [x] Rejeitar traducao se marcadores `__LT_RPG_TOKEN` (ou variacao mutilada)
  sobrarem no texto apos o `restore()` da mascara. Feito em 2026-06-10 —
  deteccao case-insensitive de `LT_RPG_TOKEN` apos o restore.
- [ ] Simplificar prompt do `OllamaVisionTextExtractor` para OCR-only — o
  `translated_text` pedido no prompt e descartado, gastando tokens por frame.
- [ ] Enviar `options.temperature = 0` e `keep_alive` no `generate()` para
  traducoes deterministicas e modelo carregado entre frames.
- [ ] Usar timeout curto dedicado (1-2s) em `is_available()` em vez do timeout
  cheio de requisicao.
- [x] Deduplicar `_DESCRIPTION_TYPES` (definido em `ollama_translator.py` e
  `prompt_builder.py`) e o bloco repetido de instrucoes "Preserve exatamente...".
  Feito em 2026-06-10: conjuntos publicos em `domain/translation_quality.py`
  (`NAME_OR_TERM_TYPES`, `DESCRIPTION_TYPES`, `BATTLE_MESSAGE_TYPES`) e blocos
  compartilhados `_ESCAPE_CODE_GUARDRAILS`/`_TOKEN_AND_SYMBOL_GUARDRAILS` no
  `prompt_builder` (o prompt de retry passou a usar a lista completa de codigos).
- [x] Corrigir "portugues brasileiro" hardcoded em `build_translation_prompt`,
  que ignora o parametro `target_language`. Feito em 2026-06-10.
- [x] Derivar o limite de 95 caracteres do `build_compact_description_prompt` —
  feito em 2026-06-10, derivado dos limites de descricao do domain (52 x 2 - 9),
  que sao os mesmos usados pela validacao `looks_like_overlong_description`.

### Resiliencia do Ollama

- [ ] Adicionar retry com backoff curto no `OllamaClient` para falhas
  transitorias (conexao recusada, timeout), sem travar o tick de captura.
- [ ] Diferenciar na UI "Ollama fora do ar" de "modelo nao instalado".
- [ ] Expor tempo da ultima resposta do Ollama no painel de Status.

### Persistencia e dados

- [ ] Adicionar versionamento de schema no SQLite (tabela `schema_version`)
  para migracoes futuras seguras.
- [ ] Adicionar acao de backup/export do banco de cache (`data/app.sqlite3`).
- [ ] Tratar banco corrompido na inicializacao: renomear e recriar em vez de
  quebrar o app.

### Qualidade de traducao

- [ ] Adicionar metrica de rejeicao do `translation_quality` no status do lote
  (quantas traducoes foram descartadas e por qual regra).
- [ ] Criar corpus de regressao com pares fonte/traducao reais para validar
  mudancas de prompt sem rodar o jogo.

### CI e empacotamento

- [ ] Adicionar workflow de CI (GitHub Actions) rodando `ruff check` e `pytest`
  em Windows.
- [ ] Avaliar empacotamento com PyInstaller para distribuicao sem Python
  instalado.

## Validacao antes de merge

- [x] Rodar `.venv\Scripts\python.exe -m ruff check .`.
- [x] Rodar `.venv\Scripts\python.exe -m pytest`.
- [x] Testar manualmente o modo Universal para garantir que OCR/captura nao regrediu.
- [x] Testar manualmente o modo MV/MZ com plugin atualizado.
- [x] Atualizar README, CHANGELOG e relatorio da fase antes do commit final.
