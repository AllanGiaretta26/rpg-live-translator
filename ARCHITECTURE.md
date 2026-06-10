# ARCHITECTURE.md

# RPG Live Translator — Arquitetura do Projeto

Este documento descreve a arquitetura **real** do código em `src/live_translator/`.
Quando houver dúvida entre este documento e o código, o código vence — e o ponto
de partida para conferir é sempre `app/bootstrap.py` (composition root).

---

## 1. Visão geral

Aplicativo desktop Windows-first, em Python 3.13+, que traduz textos de jogos
RPG Maker para pt-BR em tempo real. Existem **dois modos de operação**
(`OperationMode` em `domain/models.py`):

| Modo | Como funciona | Quando usar |
| --- | --- | --- |
| `UNIVERSAL` | Captura de tela (MSS) → OCR via Ollama vision → tradução via Ollama → overlay PySide6 | Qualquer jogo/janela |
| `RPG_MAKER_MV_MZ` | Lê o catálogo JSON do jogo + recebe a fala atual via bridge HTTP local (plugin `LiveTranslatorBridge.js`) — **sem OCR** | Jogos MV/MZ com acesso à pasta `data/` |

Resultados são cacheados em SQLite (por texto normalizado e por hash perceptual
de imagem). O estilo arquitetural é um **monólito modular desktop** em quatro
camadas, com contratos `Protocol` no domínio e injeção de dependência manual no
bootstrap.

```txt
UI  ──────────────┐
                  ▼
            Application
                  ▼
               Domain  ◄────── Infrastructure
```

---

## 2. Regras de dependência (invariantes)

Estas regras são o que mantém o projeto testável e robusto. Violações devem ser
tratadas como bug em review.

1. **Domain não importa nada externo.** Nada de PySide6, mss, sqlite3,
   requests, PIL etc. em `domain/`. Apenas stdlib (`dataclasses`, `enum`,
   `pathlib`, `typing`).
2. **Application depende só de Domain.** Os serviços de aplicação recebem
   dependências pelos contratos `Protocol` de `domain/interfaces.py`; nunca
   instanciam adaptadores concretos.
3. **UI nunca toca infraestrutura.** A UI fala com serviços de Application
   (`CaptureLoopService`, `ModeSettingsService`, …), nunca com SQLite, Ollama,
   MSS ou parsers diretamente.
4. **Infrastructure implementa os Protocols do Domain.** Bibliotecas externas
   só aparecem aqui e em `ui/`.
5. **Imports de desktop são lazy/guardados.** `pyside6` e `mss` só podem ser
   importados no topo de módulo dentro de `ui/` e
   `infrastructure/capture/`. Em qualquer outro lugar (especialmente
   `app/bootstrap.py`), o import fica dentro de função e protegido por
   `try/except ImportError` — é isso que permite rodar testes e CI sem GUI.
6. **O único lugar que liga implementação a contrato é `app/bootstrap.py`.**
   Nenhum outro módulo decide "qual" implementação usar.
7. **Banco só é acessado por repositories** (`infrastructure/persistence/`).
   Prompts só existem em `infrastructure/translation/prompt_builder.py`.

Checagem rápida de violações:

```powershell
# Domain importando infra/UI (deve retornar vazio)
Get-ChildItem src/live_translator/domain -Filter *.py |
    Select-String "import (PySide6|mss|sqlite3|requests|PIL)"
# Imports desktop no topo de módulo fora dos lugares permitidos (deve retornar vazio)
Get-ChildItem src/live_translator -Recurse -Filter *.py |
    Where-Object { $_.FullName -notmatch '\\(ui|capture)\\' } |
    Select-String "^(import|from) (PySide6|mss)"
```

---

## 3. Estrutura real de pastas

```txt
src/live_translator/
  app/
    main.py                     # entry point (python -m live_translator.app.main)
    bootstrap.py                # composition root + AppRuntime + fallbacks headless

  domain/
    models.py                   # dataclasses frozen com validação em __post_init__
    interfaces.py               # contratos Protocol
    errors.py                   # erros de domínio
    translation_quality.py      # heurísticas de validação de tradução (crítico)

  application/
    capture_loop_service.py     # tick de captura, pause/resume, busy flag, last_error
    translation_pipeline_service.py  # pipeline universal (frame → overlay)
    capture_preview_service.py  # salva preview da região capturada
    profile_settings_service.py # perfil ativo (janela + região)
    overlay_settings_service.py # posição/opacidade/fonte do overlay
    mode_settings_service.py    # modo ativo + todo o fluxo de catálogo MV/MZ
    rpg_maker_runtime_service.py# processa fala recebida pelo bridge
    rpg_maker_patch_service.py  # export/apply/restore de patch MV/MZ
    geometry.py                 # regras puras de geometria

  infrastructure/
    capture/
      mss_screen_capture.py     # ScreenCapture via MSS
      win32_window_detector.py  # detecção de janela Win32
    image/
      image_hasher.py           # hash perceptual (ImageHasher)
      image_change_detector.py  # detecção de mudança de frame
      image_preprocessor.py     # pré-processamento
    persistence/
      sqlite_connection.py      # SQLiteConnectionManager (schema único por instância)
      translation_cache_repository.py   # TranslationCache (com scope)
      image_cache_repository.py         # ImageCache
      settings_repository.py            # SettingsRepository (key/value)
      game_profile_repository.py        # GameProfileRepository
      rpg_maker_catalog_repository.py   # RpgMakerTextCatalog
      catalog_translation_error_repository.py  # erros do batch
    translation/
      ollama_client.py          # HTTP client (timeout, is_available)
      ollama_translator.py      # Translator
      ollama_vision_text_extractor.py   # TextExtractor (OCR por vision)
      prompt_builder.py         # único lugar com prompts
    rpgmaker/
      project_detector.py       # detecta projeto MV/MZ (www/data ou data)
      json_text_parser.py       # extrai textos preservando origem exata
      runtime_bridge_server.py  # servidor HTTP local do bridge
      plugin/LiveTranslatorBridge.js    # plugin que roda dentro do jogo

  ui/                           # PySide6: main_window, overlay_window,
                                # region_selector_window, geometrias
  config/
    defaults.py                 # constantes DEFAULT_*
    settings.py                 # AppSettings (pydantic-settings + fallback dataclass)

  scripts/                      # create_profile, capture_region (dev)
```

---

## 4. Composition root e robustez de inicialização

`bootstrap()` monta o grafo de objetos inteiro e devolve um `AppRuntime`
(dataclass frozen com todos os serviços). `AppRuntime.start()`:

1. checa `ollama_client.is_available()` — se o Ollama estiver fora do ar,
   **avisa no overlay e segue**; o app nunca deixa de abrir por causa disso;
2. inicia o bridge HTTP do RPG Maker se `rpg_maker_bridge_enabled`;
3. roda a UI (`ui.run()`).

### Degradação headless (padrão a preservar)

Cada dependência de desktop tem um fallback nulo, escolhido por
`try/except ImportError` no bootstrap:

| Dependência ausente | Fallback |
| --- | --- |
| `mss` | `NullScreenCaptureService` |
| `pyside6` (overlay) | `ConsoleOverlay` (imprime no stdout) |
| `pyside6` (UI) | `ConsoleUiApp` (imprime "pronto" e encerra) |

Nota: `MSSScreenCapture` importa `mss` lazy dentro de `capture_region`, então
na prática o módulo importa mesmo sem a lib e o `NullScreenCaptureService` só
cobre o caso de falha de import do próprio adaptador; o bootstrap headless
funciona de qualquer forma porque nenhuma captura ocorre no start.

É por isso que a suíte de testes e o CI executam o `bootstrap()` completo sem
display nem Ollama (verificado por `tests/unit/test_architecture_rules.py` e
`tests/unit/app/test_bootstrap_headless.py`). **Nunca** transforme esses
imports em imports de topo de módulo fora de `ui/` e `infrastructure/capture/`.

### Injeção para testes

`bootstrap(settings=…, overlay_factory=…, ui_factory=…)` permite substituir
overlay e UI por fakes. Testes de fluxo devem usar esses pontos de injeção em
vez de monkeypatch profundo.

---

## 5. Modo universal — pipeline de tradução

`TranslationPipelineService.process_frame(image)` processa cada frame com
short-circuits nesta ordem (cada etapa evita o custo das seguintes):

```txt
1. ImageChangeDetector.has_changed?      → não mudou: retorna
2. ImageHasher + ImageCache.get_by_hash  → hit válido: overlay e retorna
3. TextExtractor.extract (Ollama vision) + DefaultTextNormalizer
4. filtro _looks_like_non_game_text      → descarta vazamento de prompt do OCR
5. TranslationCache.get_by_text          → hit válido: salva no image_cache, overlay
6. Translator.translate (Ollama)
7. salva nos dois caches
8. OverlayRenderer.show_text
```

Todo hit de cache (imagem ou texto) passa por
`looks_like_invalid_translation` antes de ir ao overlay; hit contaminado é
tratado como miss e re-traduzido — o mesmo contrato dos fluxos MV/MZ
(runtime, lote, contagem e patch).

O pipeline mantém o contexto de falas deliberadamente vazio (a propriedade
`context` existe para os testes garantirem que ele nunca acumula — falas
anteriores não vazam para a tradução atual) e expõe `last_diagnostic` / `last_timing_summary`, consumidos pelo painel de
Status da UI — diagnóstico é parte do contrato, não detalhe interno.

### Loop de captura (`CaptureLoopService`)

- `tick()` é chamado por timer da UI; retorna se processou um frame.
- Flag `is_busy` impede frames concorrentes (não processa um novo frame
  enquanto outro está em andamento).
- `pause()`/`resume()` controlam o estado; `last_error_message` +
  `clear_last_error()` capturam falhas **sem derrubar o app** — erro de captura
  ou de pipeline vira mensagem na UI, nunca exceção não tratada.

---

## 6. Modo RPG Maker MV/MZ

Três fluxos independentes, todos orquestrados por `ModeSettingsService`:

### 6.1 Importação de catálogo (somente leitura)

```txt
Usuário aponta a pasta do jogo
  → FileSystemRpgMakerProjectDetector.detect (www/data ou data; MV/MZ)
  → RpgMakerJsonTextParser.parse_project
  → SQLiteRpgMakerTextCatalogRepository.replace_project_entries
```

O parser cobre `Map*.json`, `CommonEvents.json`, `System.json`, bancos
(`Items`, `Skills`, `Weapons`, `Armors`, `States`, `Classes`, `Enemies`,
`Actors`, `Troops`) e `Scenario.json`. Cada `RpgMakerTextEntry` carrega um
`RpgMakerTextOrigin` com a origem exata (arquivo/evento/página/comando/parâmetro
ou id/campo de banco) — é isso que torna o write-back do patch seguro.

### 6.2 Tradução em lote do catálogo

`translate_catalog_entries()` traduz entradas pendentes com progresso
(`CatalogTranslationProgress`), valida cada resultado com
`translation_quality`, e registra falhas em
`CatalogTranslationErrorRepository` (limpo a cada novo lote) em vez de abortar.
`clear_contaminated_catalog_cache()` remove do cache traduções que ficaram
inválidas segundo as heurísticas atuais.

### 6.3 Runtime bridge (fala ao vivo, sem OCR)

```txt
Jogo (plugin LiveTranslatorBridge.js)
  → POST http://127.0.0.1:8765/rpgmaker/text   (host/porta configuráveis)
  → RpgMakerRuntimeBridgeServer
  → RpgMakerRuntimeService.process_text
       cache (com scope do projeto) → tradução se necessário → overlay
```

O servidor expõe `is_running` / `last_error`; `start()` retorna `bool` em vez
de lançar — porta ocupada não derruba o app. O serviço expõe os mesmos
`last_diagnostic` / `last_timing_summary` do pipeline universal.

### 6.4 Patch (export / apply / restore)

`RpgMakerPatchService` gera JSON traduzido a partir de **catálogo + cache
existente apenas** — nunca chama o Ollama. Salvaguardas:

- valida que o texto original ainda bate com o JSON do jogo antes de
  substituir (jogo atualizado ⇒ entrada pulada e reportada, não corrompida);
- quebra linhas respeitando limites configuráveis
  (`patch_message_line_limit`, `…_face_line_limit`, `…_description_line_limit`);
- escreve em `exports/patches/<game>-ptBR-<timestamp>/data/` com relatório;
- `apply_patch` faz backup em `backups/patches/...` **antes** de tocar nos
  arquivos do jogo; `restore_latest_backup` desfaz.

**Invariante:** o app nunca modifica arquivos do jogo fora das ações explícitas
de apply/restore.

---

## 7. Qualidade de tradução é correção, não estilo

`domain/translation_quality.py` é o guardião contra traduções
contaminadas e é o coração da qualidade do patch MV/MZ.
`looks_like_invalid_translation()` rejeita:

- vazamentos de prompt/contexto na resposta do modelo;
- perda de códigos de escape do RPG Maker (`\N[1]`, `\V[2]`, `\C[3]`,
  `\I[64]`) e placeholders `%1`;
- marcadores de moeda inesperados no início (`€`/`¥`/`￥`);
- nomes/descrições longos demais para o tipo (`RpgMakerTextType`).

Regras de robustez:

- **Cache hit que falha na validação é tratado como miss** e re-traduzido —
  cache contaminado não se propaga para overlay nem patch.
- A contagem de "cache hits" do catálogo só conta traduções válidas, alinhada
  ao que lote e patch consideram hit real.
- Ao mudar prompt ou comportamento de tradução, **atualize as heurísticas e
  seus testes na mesma mudança** (`tests/unit/domain/test_translation_quality.py`).

---

## 8. Cache e escopo

Dois caches complementares, consultados nessa ordem no modo universal:

| Cache | Chave | Resolve |
| --- | --- | --- |
| `image_cache` | hash perceptual da imagem | mesma caixa de diálogo parada na tela |
| `translations` | texto-fonte normalizado (+ `scope`) | mesma fala em frames diferentes |

### Escopo (`scope`)

Todo o `TranslationCache` Protocol aceita `scope: str | None`. Traduções MV/MZ
usam o caminho do projeto ativo como escopo
(`ModeSettingsService.get_rpg_maker_cache_scope()`), para que jogos diferentes
nunca compartilhem/contaminem cache. O modo universal usa escopo nulo (global).
Ao adicionar qualquer consulta nova ao cache, propague o `scope`.

### Consultas em lote

Fluxos que checam muitos textos (contagem de cache do catálogo, limpeza de
cache contaminado) usam `get_many_by_text`, que resolve a lista inteira em uma
consulta (com chunking para o limite de parâmetros do SQLite). Não escreva
loops `get_by_text` — é o anti-padrão N+1.

---

## 9. Persistência (SQLite)

`SQLiteConnectionManager` abre uma conexão nova por operação (`open()`), mas
cria/migra o schema **uma única vez por instância** (com lock); cada conexão só
configura estado barato (`PRAGMA foreign_keys`). DDL fora do caminho quente é
intencional — não mover `CREATE TABLE` para dentro de `open()`.

Tabelas: `translations` (unique por texto normalizado + escopo),
`image_cache` (unique por hash), `game_profiles`, `settings` (key/value),
catálogo MV/MZ e erros de lote. O schema autoritativo está em
`sqlite_connection.py` e nos repositories — não duplique DDL em docs.

Falha de cache é não-fatal: o fluxo segue sem cache e registra log.

---

## 10. Configurações

- `config/defaults.py` concentra as constantes `DEFAULT_*` (URL/modelo/timeout
  do Ollama, intervalo de captura, caminhos, host/porta do bridge, limites de
  quebra de linha do patch).
- `config/settings.py` define `AppSettings` via `pydantic-settings`, lendo env
  com prefixo `LIVE_TRANSLATOR_` (ex.:
  `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT`) e arquivo `.env`.
- Existe um **fallback dataclass sem pydantic** no mesmo módulo — ao adicionar
  um campo, **adicione nas duas definições** e em `defaults.py`.
- Configurações editáveis pela UI (modo ativo, projeto MV/MZ, posição do
  overlay, perfil ativo) são persistidas no SQLite via `SettingsRepository`,
  não em `.env`.

---

## 11. Tratamento de erros — mapa de falhas

Princípio: **toda falha de dependência externa degrada para um estado visível e
recuperável; nada derruba o app.**

| Falha | Comportamento |
| --- | --- |
| Ollama indisponível no start | aviso no overlay, app continua |
| Ollama falha/timeout em runtime | erro registrado (`last_error_message` / erros de lote), frame/entrada pulado |
| Modelo não instalado no Ollama (HTTP 404) | `OllamaModelNotFoundError` com instrução de `ollama pull` — distinto de "fora do ar" |
| Resposta inválida do modelo | rejeitada por `translation_quality`, tratada como miss/erro de lote |
| `pyside6`/`mss` ausentes | fallbacks console/null via `ImportError` |
| Porta do bridge ocupada | `start()` retorna `False`, `last_error` preenchido |
| Caminho do projeto MV/MZ ficou inválido (jogo movido/atualizado) | runtime ignora a fala com diagnóstico "projeto MV/MZ inacessível" — sem HTTP 500 por linha |
| Região/perfil inválido | validação em `__post_init__` dos modelos (`ValueError` na borda) |
| JSON do jogo mudou desde o import | entrada do patch é pulada e reportada |
| SQLite falhou | segue sem cache, loga |

Os modelos de domínio validam invariantes no `__post_init__` (região com
dimensões positivas, textos não vazios, opacidade em (0,1]…), então dados
inválidos falham cedo e perto da origem.

---

## 12. Testes

- A suíte roda **sem** desktop nem Ollama: não adicione testes que exijam
  servidor Ollama vivo, display, `pyside6` ou `mss`.
- Layout espelha o pacote: `tests/unit/<layer>/...` e `tests/integration/`;
  nomes `test_<module>.py` / `test_<behavior>()`.
- Teste contra os Protocols com fakes/mocks; SQLite real só em banco
  temporário nos testes de integração.
- Prioridades de cobertura (em ordem de criticidade):
  1. `translation_quality` — qualquer mudança de prompt/heurística;
  2. pipeline com mocks (ordem dos short-circuits, escopo de cache);
  3. parser/patch MV/MZ (origem preservada, validação de write-back, backup);
  4. repositories (escopo, lote, unicidade);
  5. normalização e detecção de mudança de imagem.

```powershell
.venv\Scripts\python.exe -m pytest          # suíte completa
ruff check . ; ruff format .                # lint/format (linha 88, py313)
```

---

## 13. Regras para agentes de código e contribuição

- Comece a leitura por `app/bootstrap.py`; é o mapa de como tudo se conecta.
- Peça/faça mudanças pequenas, por módulo, respeitando os Protocols existentes.
- Ao criar um serviço novo: contrato em `domain/interfaces.py` (se precisar de
  infra), implementação em `infrastructure/`, orquestração em `application/`,
  fiação **apenas** no `bootstrap()` e no `AppRuntime`.
- Ao adicionar setting: `defaults.py` + as duas definições de `AppSettings` +
  passagem explícita no `bootstrap()`.
- Código, comentários, docs e strings de UI em **português brasileiro**.
- Commits com assunto curto no imperativo.

---

## 14. Evolução e limites conhecidos

Mantenha o monólito enquanto o app rodar em uma única máquina. Considere
separar processos apenas se o OCR/tradução travar a UI de forma irrecuperável,
ou se o modelo precisar rodar em outra máquina. Primeira evolução possível:
`Desktop UI → Local Translation Server → Ollama/OCR/Cache`.

Limites conhecidos do modo MV/MZ:

- plugins que montam texto por script não aparecem no catálogo (o bridge
  runtime cobre parte disso);
- variáveis e códigos de controle precisam ser preservados (vigiado por
  `translation_quality`);
- textos renderizados como imagem continuam dependendo do modo universal;
- jogos empacotados/criptografados podem exigir fallback para OCR.
