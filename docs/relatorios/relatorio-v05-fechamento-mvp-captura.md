# Relatório V05 — Fechamento do MVP de captura

## Resumo

Este checkpoint fecha o escopo atual do MVP para o fluxo externo por captura de tela. Testes manuais mostraram que desativar prompts com contexto recente resolveu a contaminação visível por contexto e melhorou a latência percebida. O app agora expõe diagnósticos básicos de tempo no painel de status para comparar OCR, tradução e tempo total por frame durante gameplay real.

## Entregas

- Contexto recente de tradução desativado por padrão para evitar vazamento de diálogo anterior na saída atual.
- Prompts de tradução encurtados quando nenhum contexto é enviado ao modelo.
- Diagnóstico de tempo no pipeline: tempo total do frame, tempo de OCR, tempo de tradução e caminho percorrido pelo frame.
- Resumo de tempo exibido no painel `Executar`.
- Documentação atualizada para marcar o MVP baseado em captura como funcionalmente completo.
- Suporte por leitura de arquivos RPG Maker MV/MZ documentado como próxima grande evolução.

## Achados manuais

- A poluição por contexto parece resolvida após desativar o contexto.
- A latência melhorou o suficiente para o fluxo atual de MVP.
- OCR e tradução ficaram em torno de 1,50s ou menos cada durante os testes.
- O tempo fim a fim observado em casos de cache miss ficou por volta de 3,40s.
- A linha de status atual é útil; granularidade maior provavelmente deixaria o painel ruidoso se não ficasse atrás de um modo debug.

## Validação

```powershell
.venv\Scripts\python.exe -m pytest
```

Resultado registrado:

```txt
75 passed
```

Validação de estilo tentada com:

```powershell
.venv\Scripts\python.exe -m ruff check .
```

Resultado registrado:

```txt
No module named ruff
```

## Status do MVP

Os critérios do MVP em `docs/BRIEFING.md` foram atendidos para o fluxo por captura de tela:

- região de texto selecionável;
- captura da região;
- OCR/vision e tradução local via Ollama;
- overlay traduzido;
- cache por imagem e texto;
- controles de pausa/retomada;
- status básico do pipeline e diagnóstico de tempo.

## Próxima fase: suporte RPG Maker MV/MZ

A próxima grande fase deve adicionar suporte read-only a RPG Maker MV/MZ:

- detectar pastas `www/data` ou `data`;
- parsear `MapXXX.json` e `CommonEvents.json`;
- extrair diálogos, escolhas e texto rolante;
- preservar origem do texto para depuração e rastreabilidade de cache;
- pré-cachear traduções conhecidas;
- usar OCR/vision como fallback e pareamento em runtime, não como única fonte da verdade.

Isso deve melhorar latência, consistência e qualidade de tradução sem modificar arquivos do jogo.

## Pendências e riscos

- O app ainda não está empacotado como executável Windows.
- Captura ainda usa coordenadas absolutas da tela, não uma janela de jogo móvel.
- OCR/vision continua necessário para imagens, textos gerados por plugins e strings desconhecidas em runtime.
- Logging de produção e diagnósticos exportáveis continuam pendentes.
