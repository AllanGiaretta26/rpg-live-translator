# Relatório V10 — UX dos modos Universal e MV/MZ

## Resumo

Este checkpoint melhora a UX da janela principal separando o fluxo Universal, baseado em captura, do fluxo RPG Maker MV/MZ, baseado em catálogo/runtime. O app passa a deixar o modo ativo mais claro e desativa controles que não se aplicam ao modo atual.

## Entregas

- Abas principais renomeadas para separar `Universal` de `RPG Maker MV/MZ`.
- Controles agrupados em seções para modo ativo, projeto, captura/OCR Universal, manutenção de catálogo MV/MZ, tradução em lote, overlay compartilhado e ações de runtime.
- Estado centralizado de controles por modo na janela principal.
- Controles de captura Universal desativados enquanto o modo RPG Maker MV/MZ está ativo.
- Controles de catálogo, lote, cache e erros MV/MZ desativados enquanto o modo Universal está ativo.
- Seleção/importação de projeto RPG Maker mantida disponível quando o usuário seleciona RPG Maker MV/MZ no dropdown, mesmo antes de salvar o modo.
- Controles de overlay mantidos disponíveis nos dois fluxos.

## Notas de comportamento

- No modo Universal, o app mantém controles de captura/OCR ativos e marca controles MV/MZ como indisponíveis.
- No modo RPG Maker MV/MZ, o app pausa captura como antes e torna catálogo/runtime o fluxo ativo.
- `Reprocessar fala atual` só fica ativo quando o modo RPG Maker MV/MZ está ativo e o serviço runtime existe.
- Controles de lote seguem o mesmo estado: iniciar só fica disponível em MV/MZ quando nenhum lote está rodando; pausar/retomar/cancelar só ficam disponíveis durante lote ativo.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

Resultados registrados:

```txt
120 passed
All checks passed!
```

## Pendências e riscos

- Os testes de estado cobrem regras de comportamento sem instanciar Qt. Uma camada futura de testes com widgets Qt pegaria regressões visuais de forma mais direta.
- A janela principal ainda usa layout desktop com abas. Um redesenho maior poderia melhorar densidade visual, mas este checkpoint manteve a mudança focada.
