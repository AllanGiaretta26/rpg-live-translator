# Auditoria do projeto — 2026-06-10

Auditoria completa do código em `src/live_translator/` antes de iniciar as
correções pendentes, para mapear interdependências e evitar que um fix isolado
crie regressões em outro fluxo.

Escopo coberto: todas as camadas (domain, application, infrastructure, ui),
bootstrap, persistência, bridge HTTP, patch MV/MZ e threading.

---

## 1. O que está sólido (não mexer sem motivo)

| Área | Evidência |
| --- | --- |
| Overlay thread-safe | `OverlayWindow` usa `Signal` bridge (`show_requested`/`hide_requested`) para marshalling à thread da GUI — chamadas de workers são seguras (`ui/overlay_window.py:72-85`). |
| Loop de captura | `CaptureLoopService` tem lock de estado, flag `in_flight` contra frames concorrentes, rollback do agendamento em falha de thread e error handler que nunca derruba o app. |
| UI ↔ worker do lote | Padrão correto: worker thread → `Queue` → `QTimer` polling na thread da GUI (`main_window.py:1283-1367`). Sem toques cross-thread em widgets. |
| Persistência | Migração de schema com rebuild da tabela `translations` (scope + dedup), upsert por `ON CONFLICT`, chunking de 500 no `get_many_by_text`, conexão por operação com commit/rollback. |
| Patch MV/MZ | Valida texto-fonte antes de substituir, ordena substituições em ordem descendente (preserva índices ao mudar tamanho de lista), largura visível ignora códigos de escape, backup com manifest antes de aplicar. |
| Bridge HTTP | Limite de payload (1 MB), validação de `Content-Length`, erros JSON tratados, exceções viram 500 logado. |
| Camadas | Nenhuma violação UI→infra nem application→infra/ui. Única violação: item 2.1 abaixo. |
| Settings | As duas definições de `AppSettings` (pydantic e dataclass) estão em sync hoje (15 campos idênticos). |

---

## 2. Achados, por prioridade

### 2.1 Violação de camada: infraestrutura importa Application (ALTO) — RESOLVIDO 2026-06-10

`infrastructure/translation/ollama_translator.py:9` importa 7 funções de
`application/translation_quality.py`. O módulo é stdlib puro — pertence ao
domínio.

**Consumidores que precisam mudar juntos**: `ollama_translator.py`,
`mode_settings_service.py`, `rpg_maker_patch_service.py`,
`rpg_maker_runtime_service.py` e os testes
(`tests/unit/application/test_translation_quality.py`).

### 2.2 Modo universal NÃO valida cache contaminado (ALTO) — RESOLVIDO 2026-06-10

`TranslationPipelineService.process_frame` aceita qualquer hit de cache sem
passar por `looks_like_invalid_translation` — tanto o hit por **imagem**
(linha 97-102) quanto o hit por **texto** (linha 117-127). Já o runtime MV/MZ,
o lote, a contagem e o patch validam todo hit. Consequência: tradução
contaminada antiga continua aparecendo no overlay do modo universal para
sempre (e o hit de texto ainda a propaga para o image_cache).

### 2.3 Runtime MV/MZ refaz detecção de projeto no disco a cada fala (ALTO) — RESOLVIDO 2026-06-10

`RpgMakerRuntimeService.process_text` → `_cache_scope()` →
`ModeSettingsService.get_rpg_maker_cache_scope()` → `detector.detect(path)`
(I/O de filesystem) **a cada POST do plugin**. Pior: `detect()` lança
`RpgMakerProjectDetectionError` se o caminho salvo ficou inválido (jogo
movido/atualizado pela Steam) — toda fala vira HTTP 500 sem mensagem útil no
overlay. Precisa de: cache do scope + degradação com diagnóstico claro.

### 2.4 Retry de prompt não cobre JSON inválido (MÉDIO) — RESOLVIDO 2026-06-10

`ollama_translator.py:89`: `client.generate(prompt)` fora do `try`; um
`OllamaInvalidResponseError` de JSON malformado aborta o loop em vez de
acionar o prompt de retry.

### 2.5 Classificação de erros do OllamaClient (MÉDIO) — RESOLVIDO 2026-06-10

- `error.HTTPError` é capturado pelo `except error.URLError` (subclasse) —
  404 "modelo não instalado" vira "Ollama is unavailable".
- Timeout embrulhado em `URLError(reason=TimeoutError)` vira
  `OllamaConnectionError` em vez de `OllamaTimeoutError`.

### 2.6 Marcadores de máscara sem validação pós-restore (MÉDIO) — RESOLVIDO 2026-06-10

`_mask_rpg_maker_tokens`/`restore()`: marcador `__LT_RPG_TOKEN_N__` mutilado
pelo modelo sobra no texto final. Para códigos `\{`, `\.`, `\^` (mascarados
mas não cobertos por `missing_rpg_maker_escape_codes`), o lixo passa para
cache e patch.

### 2.7 N+1 de cache no lote e no export do patch (MÉDIO) — RESOLVIDO 2026-06-10

A regra documentada ("não consultar texto a texto") é violada nos dois fluxos
mais pesados:

- `translate_catalog_entries` (`mode_settings_service.py:281`): um
  `get_by_text` (= uma conexão SQLite) por entrada do catálogo.
- `RpgMakerPatchService.export_patch` (`rpg_maker_patch_service.py:130`):
  idem, para o catálogo inteiro.

**Armadilha ao corrigir**: o catálogo tem entradas duplicadas (mesmo texto em
origens diferentes). Hoje a 2ª ocorrência pega o cache salvo pela 1ª na mesma
execução, porque cada `get_by_text` é fresco. Um prefetch ingênuo com
`get_many_by_text` retraduzia a 2ª ocorrência. O prefetch precisa atualizar o
mapa local após cada `save_translation` (ou deduplicar por texto normalizado
antes do loop).

### 2.8 Traduções concorrentes via bridge (BAIXO/observar)

`ThreadingHTTPServer` cria uma thread por POST; avanço rápido de diálogo pode
empilhar chamadas simultâneas ao Ollama (a resposta HTTP só sai após a
tradução inteira). O `request_id` já impede overlay desatualizado; o custo é
só carga no Ollama. Opções futuras: responder 202 e processar async, ou
serializar com lock. Não corrigir junto com outras mudanças — comportamento do
plugin precisa ser testado manualmente.

### 2.9 Código morto e drift (BAIXO)

- `domain/errors.py`: **nenhuma** das 5 exceções é usada em lugar algum.
  `RpgMakerProjectDetectionError` (infra) herda de `ValueError`, não de
  `DomainError`. Decidir: adotar de verdade ou remover.
- Tabela `glossary` no `SCHEMA_SQL` sem repositório, Protocol ou uso.
- Heurísticas irmãs em 3 lugares: `_PROMPT_ECHO_MARKERS` (vision extractor),
  `_NON_GAME_TEXT_MARKERS` (pipeline), `_PROMPT_LEAK_MARKERS` (quality).
- `_DESCRIPTION_TYPES` duplicado (translator + prompt_builder); blocos
  "Preserve exatamente..." repetidos em 3 prompts; "portugues brasileiro"
  hardcoded ignorando `target_language`; limite 95 chars hardcoded.
- `RpgMakerRuntimeService._cache_scope` usa `getattr` defensivo em vez de
  contar com o tipo `ModeSettingsService` que já recebe.
- `application/` importa `config.defaults` (patch service) — desvio leve da
  regra "Application depende só de Domain"; aceitável, mas registrar.

---

## 3. Mapa de interdependências relevantes

```txt
translation_quality (application → mover para domain)
  ├── ollama_translator (infra)          ← violação atual
  ├── mode_settings_service (lote/contagem/limpeza)
  ├── rpg_maker_patch_service (export)
  ├── rpg_maker_runtime_service (cache hit)
  └── [FALTA] translation_pipeline_service (item 2.2)

get_rpg_maker_cache_scope (mode_settings)
  ├── runtime process_text (a cada fala — item 2.3)
  ├── translate_catalog_entries / count / clear
  └── export_rpg_maker_patch

cache de tradução (scope = "" universal | root do projeto MV/MZ)
  ├── pipeline universal (sem validação — item 2.2)
  ├── runtime MV/MZ (valida)
  ├── lote (valida; N+1 — item 2.7)
  └── patch export (valida; N+1 — item 2.7)
```

---

## 4. Ordem de execução recomendada

Cada passo termina com `ruff check` + suíte completa verde antes do próximo.

1. **Mover `translation_quality` para `domain/`** (mecânico, zero mudança de
   comportamento). Atualizar os 5 imports + testes. Estender
   `tests/unit/test_architecture_rules.py` com a regra "infra não importa
   application" — que passa a valer.
2. **Validar cache no pipeline universal** (item 2.2): hits de texto e imagem
   passam por `looks_like_invalid_translation` (sem `text_type`); hit inválido
   vira miss. Testes novos no `test_translation_pipeline_service.py`.
3. **OllamaClient: classificação de erros** (item 2.5) — isolado, manter as
   exceções como subclasses de `OllamaError` para não quebrar handlers.
4. **OllamaTranslator: retry + marcador residual** (itens 2.4 e 2.6).
5. **Cache do scope no runtime + degradação do detect** (item 2.3): scope
   memoizado invalidado em `set_rpg_maker_project_path`; `detect` falhando →
   diagnóstico "projeto MV/MZ inacessível" em vez de exceção por fala.
6. **N+1 do lote e do patch** (item 2.7), respeitando a armadilha de
   duplicatas documentada acima.
7. **Limpezas** (item 2.9): erros de domínio, glossary, deduplicação de
   heurísticas/prompts — cada uma pequena e independente.

Itens deliberadamente adiados: 2.8 (precisa de teste manual com jogo real) e
instalador de plugin / UX da bridge (checklist MV/MZ, sem dependência destes).
