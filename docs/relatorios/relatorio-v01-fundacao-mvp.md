# Relatório V01 — Fundação do MVP

## Resumo

A primeira versão funcional do RPG Live Translator estabelece a base arquitetural e um MVP técnico para tradução em tempo real por captura de tela. O app já inicia com PySide6, carrega configurações, captura uma região, envia imagem ao pipeline, usa Ollama, cacheia resultados em SQLite e exibe traduções em overlay.

## Entregas

- Camada `src/live_translator/domain` com modelos imutáveis: `TextRegion`, `ExtractedText`, `TranslationResult` e `GameProfile`.
- Contratos em `src/live_translator/domain/interfaces.py` para captura, OCR, tradução, caches, overlay, perfis e settings.
- `TranslationPipelineService` com cache por imagem, cache por texto, controle de contexto e filtro contra eco de prompt.
- `CaptureLoopService` com pausa, retomada, intervalo de captura, proteção contra frames paralelos e tratamento local de erros.
- Persistência SQLite para `translations`, `image_cache`, `glossary`, `game_profiles` e `settings`.
- Integração Ollama com timeout, tratamento de erro de conexão, `format=json` e validação de JSON.
- Utilitários de imagem com hash perceptual, detector de mudança e pré-processamento.
- Captura MSS e detector Win32.
- Overlay PySide6 com atualização por sinais Qt e posição ajustável por mouse.
- Janela de calibração guiada para selecionar área do texto, testar preview, ajustar overlay, pausar, retomar e fechar.
- Scripts `live_translator.scripts.create_profile` e `live_translator.scripts.capture_region` para validação manual.

## Validação

Ambiente validado com:

```powershell
.venv\Scripts\python.exe -m pytest
```

Resultado registrado:

```txt
52 passed
```

Também foram validados:

- importação de dependências desktop (`PySide6`, `mss`, `win32gui`);
- disponibilidade do Ollama em `http://127.0.0.1:11434`;
- existência do modelo `gemma4:e4b`;
- chamada real mínima ao Ollama retornando JSON;
- captura real de região para PNG.

## Decisões arquiteturais

- O projeto permanece como monólito modular desktop.
- `src/live_translator/app/bootstrap.py` é o único ponto de composição concreta.
- UI conversa com serviços da Application, não com SQLite, Ollama ou MSS diretamente.
- Infrastructure implementa contratos do Domain.
- O overlay não exibe status inicial quando o Ollama está disponível, para evitar que o app capture o próprio overlay e gere loop visual.

## Pendências e riscos

- OCR via vision model pode alucinar em imagens sem texto; filtros iniciais foram adicionados, mas ainda podem precisar de ajuste.
- Ainda não existe histórico visual, diagnóstico completo ou logs estruturados.
- O overlay pode precisar de modos adicionais: lateral, legenda fixa ou click-through.
- O suporte específico a arquivos RPG Maker ainda não foi iniciado.

## Próximos passos recomendados

1. Validar a calibração guiada em jogo real.
2. Melhorar logs e diagnóstico do Ollama.
3. Adicionar modo click-through configurável para o overlay.
4. Avaliar captura relativa à janela quando o campo de título voltar a ser necessário.
5. Criar build Windows empacotado quando o fluxo manual estiver estável.
