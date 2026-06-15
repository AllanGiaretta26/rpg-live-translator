# Relatório V09 — Manutenção do catálogo MV/MZ

## Resumo

Este checkpoint melhora a manutenção do catálogo RPG Maker MV/MZ após lotes longos de tradução. A tabela do catálogo passa a carregar em páginas, o usuário pode localizar uma entrada por ID do banco e os caminhos de retradução manual forçam nova chamada ao modelo em vez de reutilizar cache antigo.

## Entregas

- Paginação do catálogo com 500 entradas por página.
- Paginação movida para consultas SQLite com `LIMIT`/`OFFSET`, evitando carregar o catálogo inteiro para exibir as primeiras linhas.
- Controles `Anterior 500` e `Proximos 500` na aba do catálogo.
- Busca por ID na aba do catálogo para inspecionar diretamente uma entrada persistida.
- Retradução forçada por ID de catálogo: remove tradução antiga em cache, chama Ollama novamente, salva o novo resultado e atualiza o overlay.
- `Reprocessar fala atual` passa a usar retradução runtime forçada: apaga cache antigo, ignora lookup de cache, chama Ollama novamente, salva e substitui texto no overlay.

## Notas de comportamento

- `Atualizar catalogo` volta para a primeira página do catálogo.
- Busca por ID mostra apenas a entrada correspondente e desativa navegação por páginas até atualizar o catálogo.
- `Limpar cache contaminado` continua removendo apenas traduções que falham nas heurísticas de contaminação. Não limpa o cache inteiro do jogo e não retraduz imediatamente.
- Lote com limite `100` ou `500` processa apenas essa quantidade de entradas compatíveis a partir do início do catálogo filtrado. Cache hits são pulados, entradas sem cache são traduzidas e entradas contaminadas são retraduzidas.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check <changed-files>
```

Resultados registrados:

```txt
116 passed
All checks passed!
8 files already formatted
```

## Pendências e riscos

- Contagem de cache do catálogo ainda varre as entradas ativas e pode ficar lenta em projetos muito grandes.
- Limites de lote ainda começam do início do catálogo filtrado; não miram apenas entradas que falharam recentemente.
- Erros do último lote podem ser vistos no app, mas ainda não existe retry em massa de todos os IDs com falha.
- Ainda falta trabalho futuro para exportação de patch traduzido ou substituição in-game sem overlay.
