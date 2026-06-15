# Relatório V06 — Modo RPG Maker MV/MZ inicial

## Resumo

Este checkpoint adiciona o primeiro fluxo prático de RPG Maker MV/MZ sobre o MVP baseado em captura. O app passa a importar catálogos de texto MV/MZ, pré-cachear traduções em lote, receber texto em runtime por plugin de jogo e diagnosticar se uma saída ruim no overlay veio do plugin, do cache ou do modelo.

## Entregas

- Modos explícitos `Universal` e `RPG Maker MV/MZ`.
- Detecção read-only de projetos MV/MZ em `www/data` e `data`.
- Parser JSON para `MapXXX.json` e `CommonEvents.json`.
- Tabela SQLite `rpg_maker_text_catalog` para texto-fonte extraído e origem.
- UI de catálogo com tradução de entrada individual e tradução em lote.
- Controles de lote para `100`, `500` ou todas as entradas, com progresso, cancelamento, contagem de cache hits e erros.
- Bridge HTTP runtime e plugin `LiveTranslatorBridge.js`.
- Diagnósticos MV/MZ runtime no painel `Executar`.
- Detecção de vazamento de prompt e retry com prompt de tradução mais curto.
- Validação de cache no runtime MV/MZ para ignorar e sobrescrever traduções contaminadas em cache.

## Achados manuais

- O caminho runtime MV/MZ é muito mais rápido que o caminho Universal/OCR quando há cache hit.
- O diagnóstico `Fonte MV/MZ` confirmou que algumas saídas ruins no overlay não vinham do OCR: a captura estava desativada e o runtime usava texto em cache.
- Algumas entradas iniciais de lote/cache continham instruções de prompt em `translated_text`. O runtime agora trata essas entradas como inválidas.
- O aviso de sobreposição overlay/captura pode ser enganoso no modo MV/MZ porque a captura fica desativada.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

Resultados registrados:

```txt
96 passed
All checks passed!
```

## Pendências e riscos

- Tradução em lote ainda registra apenas contagem de erros; detalhes por entrada ainda não são persistidos.
- Compatibilidade do plugin pode variar com sistemas customizados de mensagem.
- O plugin MV/MZ ainda exige instalação manual em jogos Steam/distribuídos.
- Ferramentas de limpeza de cache ainda não foram implementadas.
- O aviso de sobreposição overlay/captura deve ser ocultado ou reescrito no modo MV/MZ.
