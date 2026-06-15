# Relatório V11 — Patch JSON MV/MZ inicial

## Resumo

Este checkpoint adiciona o primeiro fluxo de patch JSON para RPG Maker MV/MZ. O fluxo atual de overlay/runtime permanece inalterado, enquanto traduções de catálogo já cacheadas passam a poder ser exportadas para JSON traduzido, aplicadas ao jogo com backup e restauradas a partir do backup mais recente.

## Entregas

- Serviço de patch para `Map*.json` e `CommonEvents.json`.
- Suporte a mensagens, escolhas, texto rolante e speakers opcionais.
- Substituição por origem exata usando metadados do catálogo, não busca global por texto.
- Relatórios de patch em JSON e Markdown.
- Backup automático antes de aplicar arquivos de patch ao projeto ativo.
- Restauração do backup mais recente criado para o projeto ativo.
- Controles de UI na aba RPG Maker MV/MZ para gerar, aplicar e restaurar patches.

## Notas de comportamento

- Geração de patch usa apenas traduções que já existem no cache.
- Entradas sem cache, traduções inválidas e divergências de fonte são puladas e reportadas.
- Entradas `speaker` são puladas salvo quando `Incluir speakers` está marcado.
- Patches gerados ficam em `exports/patches/`.
- Backups ficam em `backups/patches/`.
- Arquivos de database como `Skills.json` e `Items.json` ainda não estavam cobertos neste checkpoint.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check <changed-files>
```

Resultados registrados:

```txt
124 passed
All checks passed!
6 files already formatted
```

## Pendências e riscos

- Aplicar patch sobrescreve JSONs do jogo por design, então integridade do backup é essencial.
- O primeiro escopo de patch não traduz conteúdo de database como skills, itens, armas, armaduras ou estados.
- Jogos com eventos/plugins customizados podem ter texto fora dos comandos catalogados.
