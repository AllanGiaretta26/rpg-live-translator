# Relatório V13 — Qualidade de lote e patch MV/MZ

## Resumo

Este checkpoint estabiliza a tradução em lote e exportação de patch RPG Maker MV/MZ após os primeiros testes grandes de patch em Demons Roots. As principais correções impedem que texto só de pontuação vire diálogo inventado, preservam prefixos visuais RPG Maker em linhas quebradas e rejeitam traduções que adicionam marcadores visuais inesperados como `€`.

## Entregas

- Passthrough para texto RPG Maker que contém apenas pontuação ou tokens de controle, como `...`.
- Tradução em lote salva entradas passthrough direto no cache, sem chamar o modelo.
- Tradução individual e retradução forçada usam o mesmo comportamento passthrough.
- Detecção de tradução inválida quando origem só de pontuação vira diálogo completo.
- Detecção de marcador visual inicial inesperado, como `€`, `¥` e `￥`.
- Prompts atualizados para instruir o modelo a não adicionar símbolos visuais/moeda que não existem na origem.
- Quebra de linha do patch copia prefixos visuais simples, como `\#`, para cada continuação.
- Reflow de linha curta desativado para grupos com prefixos visuais, preservando intenção de formatação original.
- Testes de regressão para passthrough de pontuação, limpeza de cache contaminado, marcadores visuais adicionados e linhas quebradas com prefixo visual.

## Notas de comportamento

- Cache para origem `...` que expande para uma frase agora é considerado contaminado.
- `Limpar cache contaminado` remove a entrada ruim no escopo do projeto RPG Maker ativo.
- O próximo lote salva `...` como `...`, sem traduzir.
- Geração de patch ainda não chama Ollama. Usa cache existente, pula entradas ausentes/inválidas e escreve pulos no relatório.
- Se o jogo já tem patch antigo aplicado, restaure o backup antes de aplicar patch gerado após essas correções. Caso contrário, a validação de fonte pode encontrar divergência contra JSON já modificado.

## Achados locais

O cache local de Demons Roots tinha entrada contaminada:

```txt
source_text: ...
translated_text: Eu não sei quem você é, Mas ele já me pediu para falar com você.
catalog refs: 544
```

Com a nova validação, a entrada passa a ser inválida e pode ser limpa pela ação existente de limpeza de cache.

A última linha quebrada observada no prólogo veio de `Map111.json`. A tradução preservava `\#` só na primeira linha gerada, então a continuação perdia alinhamento visual. O wrapper do patch agora carrega `\#` para toda linha gerada.

## Próximo teste manual recomendado

1. Restaurar o backup mais recente se um patch antigo estiver aplicado.
2. Rodar `Limpar cache contaminado`.
3. Rodar lote novamente para entradas ausentes/inválidas.
4. Gerar novo patch.
5. Aplicar o novo patch.
6. Conferir:
   - diálogo repetido `...` não aparece mais;
   - prólogo em `Map111` não perde alinhamento em linhas quebradas;
   - descrições de skills de batalha continuam traduzidas e cabem em duas linhas.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check <changed-files>
```

Resultados registrados:

```txt
185 passed
All checks passed!
7 files already formatted
```

## Pendências e riscos

- Algumas traduções cacheadas podem continuar linguisticamente ruins mesmo passando na validação estrutural.
- Plugins customizados podem usar códigos de escape visuais com comportamento diferente por tipo de janela.
- Texto longo centralizado/cinemático ainda exige inspeção manual in-game, porque métricas reais de fonte dependem do jogo/tema.
