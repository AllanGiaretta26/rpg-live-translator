# Changelog

Todas as mudancas relevantes deste projeto serao registradas aqui.

## Unreleased

### Added

- Relatorio V6 com fechamento parcial da evolucao MV/MZ, diagnosticos e riscos
  restantes.
- Traducao em lote do catalogo MV/MZ com limite de 100, 500 ou todos os textos.
- Progresso, contagem de cache hits, contagem de erros e cancelamento para o
  pre-cache do catalogo.
- Modo RPG Maker MV/MZ com importacao de catalogo por `MapXXX.json` e `CommonEvents.json`.
- Aba `Catalogo` para listar textos importados e traduzir a entrada selecionada sob demanda.
- Catalogo SQLite `rpg_maker_text_catalog` separado do cache de traducoes.
- Bridge runtime HTTP local para receber falas de plugin MV/MZ sem passar por captura/OCR.
- Plugin `LiveTranslatorBridge.js` para enviar mensagens e escolhas do jogo ao app.

### Fixed

- Bridge MV/MZ agora captura o texto realmente renderizado pela janela de
  mensagem, evitando ler a fila interna do RPG Maker quando ela contem falas
  alem da fala visivel.
- Runtime MV/MZ agora impede que uma traducao antiga finalize depois e
  sobrescreva a fala mais recente no overlay.
- Tradutor Ollama agora rejeita respostas que vazam instrucoes do prompt e tenta
  uma segunda chamada com prompt mais curto antes de falhar.
- Runtime MV/MZ agora ignora traducoes antigas do cache quando elas parecem
  conter contexto ou instrucoes de prompt, forçando nova traducao.

### Changed

- Painel `Status` agora mostra a ultima fonte recebida pela bridge MV/MZ e a
  ultima traducao aceita pelo runtime, para separar problemas de plugin, cache e
  modelo.
- README documenta o diagnostico MV/MZ e como interpretar `Fonte MV/MZ`,
  `Traducao MV/MZ`, cache valido e cache invalido.

## [0.2.0] - 2026-05-27

### Added

- Aviso na UI quando o overlay cruza a area capturada pelo OCR.
- Helpers testaveis para sobreposicao de retangulos, geometria de overlay e selecao de monitor.
- Testes unitarios para redimensionamento do overlay, selecao de tela e validacao do tradutor Ollama.
- Relatorio V5 sobre fechamento do MVP e proxima evolucao RPG Maker MV/MZ.
- `ruff` no extra de desenvolvimento para alinhar o ambiente ao comando documentado.

### Changed

- Overlay agora pode ser redimensionado pelas bordas e cantos, nao apenas pelo canto inferior direito.
- Seletor de area agora escolhe o monitor pelo cursor e usa geometria explicita da tela.
- Prompt de traducao reforca traducao completa, sem resumo ou omissao de frases.
- Prompt de traducao agora separa contexto recente do texto atual para reduzir vazamento de falas anteriores.
- Pipeline de traducao agora desliga o contexto recente por padrao para evitar contaminacao do output.
- Prompt de traducao omite o bloco de contexto quando nao ha contexto enviado, reduzindo a chamada ao modelo.
- Painel de status agora mostra tempo total, OCR, traducao e caminho do ultimo frame processado.
- Diagnostico do pipeline diferencia falha de traducao de erro generico.
- Documentacao atualizada para marcar o MVP de captura como funcionalmente concluido e detalhar o suporte futuro a RPG Maker MV/MZ.
- README documenta Known Issues reais antes da evolucao MV/MZ.
- Versao do pacote atualizada para `0.2.0` como checkpoint MVP.

### Fixed

- Preview da area selecionada agora usa coordenadas fisicas derivadas da selecao local e escala DPI.
- Tradutor Ollama rejeita respostas que parecem incluir linhas do contexto em vez de apenas o texto atual.

## [0.1.0] - 2026-05-26

### Added

- Base arquitetural em camadas: Domain, Application, Infrastructure, UI e App.
- Modelos e contratos de dominio para captura, traducao, caches, overlay, perfis e settings.
- Pipeline de traducao com cache por imagem, cache por texto e contexto das ultimas falas.
- Loop de captura com pausa, retomada, intervalo configuravel e protecao contra processamento paralelo.
- Persistencia SQLite para traducoes, cache de imagem, glossario, perfis e configuracoes.
- Integracao Ollama com timeout, tratamento de conexao e resposta JSON.
- Captura de tela com MSS e detector de janela Win32.
- Utilitarios de imagem com hash perceptual, detector de mudanca e preprocessamento.
- Overlay PySide6 e janela minima de configuracao.
- Preview de captura na janela de configuracao, salvo em `captures/preview.png`.
- Status operacional basico do loop de captura na janela de configuracao.
- Diagnostico basico do pipeline: sem mudanca, sem texto, cache e traducao.
- Seletor visual de regiao por arraste em overlay transparente.
- Janela de calibracao guiada com abas para area do texto, overlay e execucao.
- Overlay ajustavel por mouse, com posicao e tamanho salvos em `settings`.
- Scripts para criar perfil ativo e testar captura de regiao.
- README inicial, relatorio V1 e guia de contribuicao `AGENTS.md`.
- Suite de testes automatizados com `pytest`.

### Changed

- O codigo da aplicacao foi movido para o layout `src/live_translator/`.
- Comandos de execucao e scripts agora usam o namespace `live_translator.*`.
- O client Ollama passou a enviar `format=json` para reduzir respostas fora do contrato.
- O overlay passou a atualizar via sinais Qt para evitar chamadas fora da thread principal.
- O overlay deixou de recentralizar a cada traducao quando existe posicionamento salvo.
- O pipeline passou a ignorar textos que parecem eco de prompt ou instrucoes internas.

### Known Issues

- O modelo vision pode falhar ou hallucinar quando a imagem nao contem texto claro.
- Ainda nao existe build empacotado para Windows.
