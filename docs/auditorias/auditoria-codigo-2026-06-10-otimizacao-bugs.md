# Auditoria de código — 2026-06-10 — Otimização e bugs

## Resumo

Esta auditoria focou otimização e tratamento de bugs, não novas features. A rodada removeu trabalho repetido de schema por conexão no SQLite, trocou consultas de cache por entrada por consulta em lote, corrigiu a contagem de cache do catálogo para não contar traduções contaminadas, corrigiu falso positivo na validação de marcador visual inesperado e endureceu o handler HTTP da bridge runtime RPG Maker. Itens levantados em relatórios anteriores foram rechecados contra o código real; vários já estavam resolvidos ou eram falsos alarmes, registrados abaixo para não serem reinvestigados.

## Escopo da auditoria

- Infrastructure: tradução/Ollama, persistência/SQLite, captura, imagem, bridge/parser RPG Maker.
- Application e Domain: loop de captura, pipeline de tradução, heurísticas de qualidade, patch service, runtime service e mode settings.
- Cruzamento de `CHANGELOG.md` e relatórios V01–V13 contra o código atual para confirmar se correções reportadas estavam realmente resolvidas.

## Ações aplicadas

### Performance

- `SQLiteConnectionManager` passa a inicializar schema e migrações uma vez por instância, protegido por lock e flag, em vez de rodar `SCHEMA_SQL` completo e introspecção de migração a cada `open()`.
- `PRAGMA foreign_keys = ON` permanece por conexão e `timeout` fica explícito.
- Adicionado `TranslationCache.get_many_by_text`, lookup em lote com chunking para respeitar limite de parâmetros do SQLite.
- `count_cached_catalog_entries` e `clear_contaminated_catalog_cache` passam a usar lookup em lote, evitando um `get_by_text` e uma conexão por entrada.
- `replace_project_entries` passa a inserir linhas do catálogo com `executemany`.

### Correção

- `count_cached_catalog_entries` valida cada hit com `looks_like_invalid_translation` e conta apenas traduções válidas. O número `Cache: X/Y` agora bate com lote e patch.
- `adds_unexpected_leading_visual_marker` compara apenas linhas traduzidas que têm linha-fonte correspondente. Tradução válida que quebra uma linha de origem em várias linhas não é mais rejeitada por uma linha extra sem contraparte.

### Robustez

- Handler `do_POST` da bridge runtime RPG Maker passa a limitar corpo da requisição (`413` acima do limite, `400` para `Content-Length` inválido) e separa erro de cliente (`400`) de erro interno (`500`, com stack trace em log).

### Testes

- Testes de regressão adicionados para: inicialização única de schema, lookup de cache em lote com isolamento de escopo e chunk grande, contagem de cache consciente de contaminação, importação de catálogo grande, falso positivo de marcador visual e respostas `413`/`400`/`500` da bridge.

## Notas de comportamento

- `get_many_by_text` retorna mapeamento pela string original solicitada e omite textos sem tradução em cache.
- O pipeline de tradução continua sem alimentar falas anteriores no tradutor. O `context` vazio é intencional, herdado da decisão anti-vazamento, e foi mantido como guarda de regressão.

## Achados descartados ou já resolvidos

- Regex de escape RPG Maker já casa `\C[1]`; `C` é letra e entra em `\[A-Za-z]+`.
- Checagem de índice de `_replace_parameter` no patch service está correta.
- `sqlite3.connect` já aplicava busy timeout padrão de 5s; timeout explícito foi melhoria de clareza.
- Runtime MV/MZ não apaga cache inválido explicitamente, mas `save_translation` posterior sobrescreve a entrada, então o fluxo se autocorrige.
- Versionamento por `_latest_request_id` com lock está correto.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check <changed-files>
```

Resultados registrados:

```txt
197 passed
All checks passed!
12 files already formatted
```

## Pendências e riscos

- O repositório não estava totalmente limpo para `ruff format` antes desta rodada; drift em arquivos não tocados foi deixado de propósito para manter diff focado.
- Lookup de cache em lote carrega linhas encontradas em memória. Em catálogos enormes, isso troca muitas consultas pequenas por poucos result sets maiores; é o trade-off pretendido, mas aumenta pico de memória por chamada.
- Limite de corpo da bridge (1 MiB) fica fixo no código, não configurável pela UI.
