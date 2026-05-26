# Relatorio V2

## Resumo

A segunda etapa consolidou o MVP em uma estrutura de pacote correta e melhorou o fluxo de calibracao. O projeto agora usa `src/live_translator/`, possui uma janela guiada para configurar area de texto e overlay, e separa melhor captura, preview, execucao e diagnostico.

## Entregas

- Codigo reorganizado para `src/live_translator/` com imports `live_translator.*`.
- Janela de configuracao reestruturada em abas: area do texto, overlay e execucao.
- Campo `Titulo da janela` ocultado no fluxo principal, pois ainda nao controla a captura.
- Preview de captura integrado na UI, salvo em `captures/preview.png`.
- Seletor visual de area com instrucao na tela, fundo translucido e retangulo destacado.
- Preview automatico apos selecionar a area do texto.
- Modelo `OverlayPlacement` para posicao, tamanho, opacidade e fonte do overlay.
- `OverlaySettingsService` para salvar/restaurar overlay via `SettingsRepository`.
- Overlay ajustavel por mouse: arrastar move, canto inferior direito redimensiona.
- Status basico do loop de captura e diagnostico basico do pipeline na UI.
- Documentacao atualizada no `README.md` e `CHANGELOG.md`.

## Validacao

Ambiente validado com:

```powershell
.venv\Scripts\python.exe -m pytest
```

Resultado atual:

```txt
52 passed
```

Tambem foram verificadas as fronteiras arquiteturais:

- UI nao acessa SQLite, Ollama, MSS ou infraestrutura diretamente.
- Application orquestra preview, settings e pipeline.
- Domain contem modelos e contratos sem dependencias de UI ou infraestrutura.
- Bootstrap continua sendo o ponto de montagem das implementacoes concretas.

## Decisoes Arquiteturais

- A area de captura permanece em coordenadas absolutas da tela.
- O overlay agora tem configuracao propria, separada da area de captura.
- `Titulo da janela` fica oculto ate existir captura relativa a janela.
- Persistencia de overlay usa a tabela generica `settings`, sem nova tabela.
- A calibracao prioriza mouse e usa campos numericos apenas para ajuste fino.

## Pendencias E Riscos

- A calibracao guiada precisa ser validada em jogo real.
- O overlay ainda nao tem modo click-through configuravel.
- O OCR via modelo vision ainda pode hallucinar quando nao ha texto claro.
- Ainda nao ha logs estruturados para diagnosticar chamadas Ollama em uso real.
- Captura relativa a janela ainda nao foi implementada.
- Nao existe build empacotado para Windows.

## Proximos Passos Recomendados

1. Testar o fluxo completo em um jogo real e registrar problemas de UX.
2. Adicionar modo click-through configuravel para o overlay.
3. Melhorar logs e tela de diagnostico do pipeline/Ollama.
4. Avaliar captura relativa a janela usando `win32_window_detector`.
5. Preparar empacotamento Windows quando o fluxo manual estiver estavel.
