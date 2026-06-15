# Relatório V07 — Cache e diagnósticos MV/MZ

## Resumo

Este checkpoint estabiliza o fluxo RPG Maker MV/MZ após os primeiros testes runtime com diálogo real. O foco foi recuperação de cache e diagnóstico: o app agora oferece ferramentas para identificar entradas ruins do lote, limpar cache contaminado do catálogo atual e forçar nova tradução da fala runtime atual.

## Entregas

- Aviso de sobreposição overlay/captura ocultado quando o modo `RPG Maker MV/MZ` está ativo.
- Contagem de cache do catálogo: `Cache: X/Y entradas ja traduzidas`.
- Limpeza manual de traduções contaminadas no catálogo MV/MZ ativo.
- Ação runtime para reprocessar a fala MV/MZ atual apagando o cache e traduzindo novamente.
- Persistência SQLite dos erros do último lote em `rpg_maker_batch_errors`.
- Ação de UI para inspecionar erros do lote mais recente, incluindo ID, origem, texto-fonte e mensagem de erro.
- Checklists atualizados com os itens de cache e diagnóstico implementados.

## Notas de comportamento

- A limpeza de cache é limitada ao catálogo do projeto MV/MZ ativo. Ela não varre traduções de outros jogos.
- O app mantém apenas a lista de erros do último lote. Iniciar um novo lote limpa erros anteriores.
- A validação automática de cache em runtime continua ativa: traduções contaminadas são ignoradas quando a mesma fala aparece de novo.
- `Reprocessar fala atual` é a saída manual quando o usuário quer forçar uma nova tradução imediatamente.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

Resultados registrados:

```txt
103 passed
All checks passed!
```

## Pendências e riscos

- Compatibilidade do plugin pode variar com sistemas customizados de mensagem MV/MZ.
- O plugin MV/MZ ainda exige instalação manual em jogos Steam/distribuídos.
- Erros do último lote podem ser vistos no app, mas ainda não exportados para arquivo.
- Diagnósticos runtime aparecem na UI, mas não são armazenados como log completo de sessão.
- Ainda falta trabalho futuro para exportação de patch traduzido ou substituição in-game sem overlay.
