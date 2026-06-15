# Relatório V04 — Coordenadas e consistência de tradução

## Resumo

Este checkpoint corrige o desalinhamento restante de calibração e o problema de consistência de tradução mais visível encontrado em teste manual com a janela do RPG Maker.

## Entregas

- Corrigida a saída do seletor de região para converter coordenadas locais de arraste em coordenadas físicas de captura, considerando origem da tela e escala DPI.
- Mantidos `X`, `Y`, `Largura` e `Altura` visíveis porque eles representam exatamente a região MSS usada pelo preview e pela captura em runtime.
- Atualizados prompts de tradução para separar contexto recente do texto atual.
- Adicionada validação defensiva no tradutor Ollama para rejeitar respostas que parecem incluir linhas de contexto anterior.
- Adicionada cobertura unitária para conversão de coordenadas do seletor, fronteiras de prompt e rejeição de vazamento de contexto.

## Validação

- Testes automatizados: `.venv\Scripts\python.exe -m pytest` passou com 74 testes.
- Validação manual: preview do texto selecionado correspondeu à região de diálogo do jogo.
- Validação manual: tradução parou de mostrar diálogo anterior acumulado após mudanças no prompt e no guard do tradutor.

## Pendências e riscos

- Qualidade de OCR e tradução ainda depende do comportamento do modelo local no Ollama.
- A região de captura atual usa coordenadas da tela, não fica presa a uma janela de jogo em movimento.
- Build Windows empacotado e logging de produção continuam pendentes.
