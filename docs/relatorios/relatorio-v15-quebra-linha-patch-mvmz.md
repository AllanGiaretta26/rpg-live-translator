# Relatório V15 — Quebra de linha no patch MV/MZ

## Resumo

Este checkpoint corrige três problemas in-game no patch de tradução RPG Maker MV/MZ: linhas de diálogo quebrando em locais ruins (após vírgula ou ponto), texto renderizando maior que a caixa de mensagem ou saindo da tela, e códigos de escape especiais vazando entre linhas. O wrapper de mensagens foi reescrito para preencher cada linha até a largura da caixa usando medição ciente de códigos de escape, e os limites de largura passaram a ser configuráveis por jogo.

## Causas raiz

- **Códigos de fonte duplicados.** O wrapper anterior recolocava prefixo visual inicial em toda linha quebrada, e o conjunto de prefixos incluía `\{`/`\}` (tamanho de fonte, cumulativo dentro da mensagem). Um `\{Hello ...` virava `\{line1`/`\{line2`/`\{line3`, aumentando a fonte linha a linha.
- **Largura medida em caracteres crus.** A quebra contava códigos como `\C[3]`, `\N[1]`, `\V[2]`, `\I[64]`, `\{` como caracteres visíveis. Códigos de largura zero quebravam cedo demais, e códigos dinâmicos (`\N`, `\V`, `\P`) eram subestimados.
- **Reflow ciente de sentença.** Um polimento empurrava texto depois de `.`, `!` ou `?` para a próxima linha; o caminho sem colapso preservava quebras geradas pelo modelo, inclusive após vírgulas.

## Entregas

- `_visible_width` mede largura renderizada, ignorando códigos de largura zero (`\C`, `\I`, `\{`, `\}`, waits) e estimando códigos dinâmicos (`\N`, `\P`, `\V`) de forma conservadora.
- `_fill_wrap` / `_greedy_wrap_words` colapsam quebras do modelo e preenchem cada linha até a largura visível. Traduções longas de linha única sempre quebram em múltiplas linhas.
- Prefixo repetido por linha restrito a `\#`. Códigos com estado como `\{`/`\}` ficam inline e aparecem uma vez.
- Reflow por final de frase/palavra pendurada removido, eliminando quebras forçadas após vírgula ou ponto.
- Wrapper ciente de escape aplicado a mensagens, texto rolante e descrições de database.
- Limites de largura configuráveis: `patch_message_line_limit`, `patch_message_face_line_limit` e `patch_description_line_limit` em `AppSettings`, com prefixo env `LIVE_TRANSLATOR_`, passados por `ModeSettingsService` até `RpgMakerPatchService`.
- Testes de regressão para `\{` não duplicado, `\#` ainda repetido, `_visible_width`, color codes não quebrando linha cedo, linhas longas quebrando em múltiplas linhas, limite configurável e novo output fill-to-width.

## Notas de comportamento

- Caixas de mensagem são refluídas: quebras do modelo são descartadas e o texto é preenchido novamente. Traduções curtas multilinha podem virar menos linhas quando couberem; traduções longas sempre quebram para caber.
- O problema de linha única saindo da tela não retorna: `_fill_wrap` sempre quebra no limite configurado.
- Texto rolante preserva quebras intencionais; cada linha é quebrada independentemente com medição ciente de escape.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check src/live_translator tests
```

Resultados registrados:

```txt
203 passed
All checks passed!
```

## Próximo teste manual recomendado

1. Restaurar o backup mais recente se patch antigo estiver aplicado.
2. Gerar novo patch e aplicar.
3. No jogo, conferir:
   - diálogo longo quebra em múltiplas linhas e fica dentro da caixa;
   - não há quebra logo após vírgula ou ponto;
   - fonte não cresce linha a linha (`\{` não é duplicado);
   - não sobram códigos de escape duplicados ou visíveis no diálogo.
4. Se a caixa de um jogo específico for mais estreita/larga, ajustar `LIVE_TRANSLATOR_PATCH_MESSAGE_LINE_LIMIT` e limites de face/descrição, depois gerar o patch novamente.

## Pendências e riscos

- Estimativa de largura para `\N`/`\P`/`\V` é heurística; o tamanho real em runtime é desconhecido, então a estimativa é conservadora.
- Texto realmente aumentado por `\{...\}` ocupa mais pixels por caractere; a correção evita duplicar o código, mas não modela precisamente o glifo maior.
- A largura ideal ainda depende da fonte/tema do jogo, por isso os limites são configuráveis.
