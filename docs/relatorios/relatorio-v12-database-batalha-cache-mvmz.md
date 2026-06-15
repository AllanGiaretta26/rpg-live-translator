# Relatório V12 — Database, batalha e cache MV/MZ

## Resumo

Este checkpoint completa a expansão de database, eventos de batalha e cache escopado por projeto no RPG Maker MV/MZ. O catálogo passa a importar arquivos padrão de database, termos de sistema, eventos de tropas e cenas `Scenario.json`; a tradução em lote consegue cachear esses textos por padrão; e o patch exporta JSONs de database traduzidos junto dos JSONs de eventos.

## Entregas

- Tipos de catálogo para nomes/descrições de itens, skills, armas, armaduras, estados, classes, inimigos e atores.
- Tipos de catálogo para mensagens de skill, termos de sistema e eventos de batalha (`troop_message`, `troop_choice`, `troop_scrolling_text`, `troop_speaker`).
- Parser para `Items.json`, `Skills.json`, `Weapons.json`, `Armors.json`, `States.json`, `Classes.json`, `Enemies.json`, `Actors.json`, `System.json`, `Troops.json` e `Scenario.json`.
- Metadados de origem de database com migração SQLite para catálogos existentes.
- Cache de tradução escopado por projeto RPG Maker MV/MZ, mantendo cache global para modo Universal/OCR.
- Defaults e filtros de UI para textos de database, atores, sistema e tropas.
- Substituição de patch para campos `name`, `description` e termos de sistema aninhados.
- Substituição de patch para comandos de eventos de batalha em `Troops.json`.
- Substituição de patch para listas de comandos custom em `Scenario.json`, incluindo comandos de speaker `Tachie showName`.
- Validação de tradução para códigos RPG Maker como `\N[1]` e placeholders de batalha como `%1`.
- Prompts por tipo de texto: diálogo, nomes, descrições, termos de sistema e mensagens de batalha/status.
- Quebra de linhas longas em mensagens/textos rolantes do patch.
- README e checklist MV/MZ atualizados para o escopo expandido de patch.

## Notas de comportamento

- Geração de patch ainda usa apenas traduções existentes no cache.
- Substituição em database valida arquivo, ID do objeto e campo antes de escrever.
- Substituição de termos de sistema valida o caminho aninhado antes de escrever.
- Substituição de eventos de tropa usa o mesmo fluxo de comandos de mapas, escopado por ID da tropa e página.
- Substituição de `Scenario.json` usa o mesmo fluxo de comandos de mapas, escopado pela chave da cena.
- Tradução cacheada que perde código de escape RPG Maker é inválida e será pulada/retraduzida conforme o fluxo.
- Tradução cacheada que perde `%1`, `%2` ou `%3` é inválida.
- `speaker` permanece desativado por padrão no lote.
- `speaker` comum continua opcional no patch; `troop_speaker` entra como tipo de texto de batalha.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check <changed-files>
```

Resultados registrados:

```txt
154 passed
All checks passed!
20 files already formatted
```

## Pendências e riscos

- Plugins RPG Maker customizados podem armazenar texto fora dos arquivos padrão e listas de comandos de `Scenario.json`.
- Testes manuais em múltiplos jogos MV e MZ ainda são necessários antes de tratar o patcher como amplamente seguro.
