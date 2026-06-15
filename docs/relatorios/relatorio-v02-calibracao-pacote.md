# Relatório V02 — Calibração e pacote

## Resumo

A segunda etapa consolidou o MVP em uma estrutura de pacote correta e melhorou o fluxo de calibração. O projeto agora usa `src/live_translator/`, possui uma janela guiada para configurar área de texto e overlay, e separa melhor captura, preview, execução e diagnóstico.

## Entregas

- Código reorganizado para `src/live_translator/` com imports `live_translator.*`.
- Janela de configuração reestruturada em abas: área do texto, overlay e execução.
- Campo `Titulo da janela` ocultado no fluxo principal, pois ainda não controla a captura.
- Preview de captura integrado na UI, salvo em `captures/preview.png`.
- Seletor visual de área com instrução na tela, fundo translúcido e retângulo destacado.
- Preview automático após selecionar a área do texto.
- Modelo `OverlayPlacement` para posição, tamanho, opacidade e fonte do overlay.
- `OverlaySettingsService` para salvar/restaurar overlay via `SettingsRepository`.
- Overlay ajustável por mouse: arrastar move, canto inferior direito redimensiona.
- Status básico do loop de captura e diagnóstico básico do pipeline na UI.
- Documentação atualizada no `README.md` e `CHANGELOG.md`.

## Validação

Ambiente validado com:

```powershell
.venv\Scripts\python.exe -m pytest
```

Resultado registrado:

```txt
52 passed
```

Também foram verificadas as fronteiras arquiteturais:

- UI não acessa SQLite, Ollama, MSS ou infraestrutura diretamente.
- Application orquestra preview, settings e pipeline.
- Domain contém modelos e contratos sem dependências de UI ou infraestrutura.
- Bootstrap continua sendo o ponto de montagem das implementações concretas.

## Decisões arquiteturais

- A área de captura permanece em coordenadas absolutas da tela.
- O overlay agora tem configuração própria, separada da área de captura.
- `Titulo da janela` fica oculto até existir captura relativa à janela.
- Persistência de overlay usa a tabela genérica `settings`, sem nova tabela.
- A calibração prioriza mouse e usa campos numéricos apenas para ajuste fino.

## Pendências e riscos

- A calibração guiada precisa ser validada em jogo real.
- O overlay ainda não tem modo click-through configurável.
- OCR via modelo vision ainda pode alucinar quando não há texto claro.
- Ainda não há logs estruturados para diagnosticar chamadas Ollama em uso real.
- Captura relativa à janela ainda não foi implementada.
- Não existe build empacotado para Windows.

## Próximos passos recomendados

1. Testar o fluxo completo em um jogo real e registrar problemas de UX.
2. Adicionar modo click-through configurável para o overlay.
3. Melhorar logs e tela de diagnóstico do pipeline/Ollama.
4. Avaliar captura relativa à janela usando `win32_window_detector`.
5. Preparar empacotamento Windows quando o fluxo manual estiver estável.
