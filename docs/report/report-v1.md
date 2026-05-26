# Relatorio V1

## Resumo

A primeira versao funcional do RPG Live Translator estabelece a base arquitetural e um MVP tecnico para traducao em tempo real por captura de tela. O app ja consegue iniciar com PySide6, carregar configuracoes, capturar uma regiao, enviar imagem ao pipeline, usar Ollama, cachear resultados em SQLite e exibir traducoes em overlay.

## Entregas

- Camada `src/live_translator/domain` com modelos imutaveis: `TextRegion`, `ExtractedText`, `TranslationResult` e `GameProfile`.
- Contratos em `src/live_translator/domain/interfaces.py` para captura, OCR, traducao, caches, overlay, perfis e settings.
- `TranslationPipelineService` com cache por imagem, cache por texto, controle de contexto e filtro contra eco de prompt.
- `CaptureLoopService` com pausa, retomada, intervalo de captura, protecao contra frames paralelos e tratamento local de erros.
- Persistencia SQLite para `translations`, `image_cache`, `glossary`, `game_profiles` e `settings`.
- Integracao Ollama com timeout, tratamento de erro de conexao, `format=json` e validacao de JSON.
- Utilitarios de imagem com hash perceptual, detector de mudanca e preprocessamento.
- Captura MSS e detector Win32.
- Overlay PySide6 com atualizacao por sinais Qt e posicao ajustavel por mouse.
- Janela de calibracao guiada para selecionar area do texto, testar preview, ajustar overlay, pausar, retomar e fechar.
- Scripts `live_translator.scripts.create_profile` e `live_translator.scripts.capture_region` para validacao manual.

## Validacao

Ambiente validado com:

```powershell
.venv\Scripts\python.exe -m pytest
```

Resultado atual:

```txt
52 passed
```

Tambem foram validados:

- importacao de dependencias desktop (`PySide6`, `mss`, `win32gui`);
- disponibilidade do Ollama em `http://127.0.0.1:11434`;
- existencia do modelo `gemma4:e4b`;
- chamada real minima ao Ollama retornando JSON;
- captura real de regiao para PNG.

## Decisoes Arquiteturais

- O projeto permanece como monolito modular desktop.
- `src/live_translator/app/bootstrap.py` e o unico ponto de composicao concreta.
- UI conversa com servicos da Application, nao com SQLite, Ollama ou MSS diretamente.
- Infrastructure implementa contratos do Domain.
- O overlay nao exibe status inicial quando o Ollama esta disponivel, para evitar que o app capture o proprio overlay e gere loop visual.

## Pendencias E Riscos

- O OCR via vision model pode hallucinar em imagens sem texto; filtros iniciais foram adicionados, mas ainda podem precisar de ajuste.
- Ainda nao existe historico visual, diagnostico completo ou logs estruturados.
- O overlay pode precisar de modos adicionais: lateral, legenda fixa ou click-through.
- O suporte especifico a arquivos RPG Maker ainda nao foi iniciado.

## Proximos Passos Recomendados

1. Validar a calibracao guiada em jogo real.
2. Melhorar logs e diagnostico do Ollama.
3. Adicionar modo click-through configuravel para o overlay.
4. Avaliar captura relativa a janela quando o campo de titulo voltar a ser necessario.
5. Criar build Windows empacotado quando o fluxo manual estiver estavel.
