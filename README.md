# RPG Live Translator

Aplicativo desktop em Python para traduzir, em tempo real, textos exibidos em jogos RPG Maker. O MVP captura uma região da tela, usa Ollama para extrair/traduzir texto, guarda resultados em cache SQLite e mostra a tradução em um overlay PySide6.

## Estado Atual

O projeto já possui um MVP técnico com:

- arquitetura em camadas dentro de `src/live_translator/`;
- cache SQLite por texto e por imagem;
- captura de tela com MSS;
- integração com Ollama usando `gemma4:e4b`;
- overlay PySide6 com posição ajustável e janela de calibração guiada;
- seletor fullscreen de area de texto com preview de captura e ajuste para DPI;
- prompt de traducao separado por contexto/texto atual para reduzir vazamento de falas anteriores;
- scripts de desenvolvimento para criar perfil e testar captura.

## Requisitos

- Windows 10/11
- Python 3.13 ou superior
- Ollama rodando em `http://127.0.0.1:11434`
- Modelo `gemma4:e4b` instalado no Ollama

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev,desktop]
```

Valide a instalação:

```powershell
.venv\Scripts\python.exe -m pytest
```

## Configurar Pelo App

Abra o app e use as abas da janela de calibração:

1. `Area do texto`: clique em `Selecionar area do texto`, arraste sobre a
   caixa de texto do jogo e confira o recorte em `Ver preview da area`. O
   preview deve mostrar somente a area enviada ao OCR.
2. `Overlay`: clique em `Ajustar overlay`, arraste a tradução de teste para
   mover e arraste bordas ou cantos para redimensionar. Mantenha o overlay
   fora da area capturada para evitar que o OCR leia a traducao em vez do jogo.
3. `Executar`: pause, retome e acompanhe o estado da captura e do pipeline.

Clique em `Salvar area` e `Salvar overlay` para manter os ajustes após reiniciar.

## Configurar Região Por Script

Crie ou atualize o perfil ativo:

```powershell
.venv\Scripts\python.exe -m live_translator.scripts.create_profile --name "Meu Jogo" --window-title "Manual Region" --x 256 --y 950 --width 2048 --height 360
```

Teste a captura:

```powershell
.venv\Scripts\python.exe -m live_translator.scripts.capture_region --output captures\latest.png
```

Abra `captures\latest.png` e ajuste `x`, `y`, `width` e `height` até a imagem conter a caixa de diálogo do jogo.

## Rodar O App

Sem terminal:

```powershell
.venv\Scripts\pythonw.exe -m live_translator.app.main
```

Com terminal para depuração:

```powershell
.venv\Scripts\python.exe -m live_translator.app.main
```

A janela separa a area capturada do overlay de traducao. Os numeros `X`, `Y`,
`Largura` e `Altura` sao mantidos para ajuste fino; o fluxo principal e por
mouse.

Se a traducao parecer repetir falas antigas, verifique primeiro se o preview
contem apenas a caixa de texto atual e se o overlay nao esta dentro da area
capturada.

## Arquitetura

- `src/live_translator/domain/`: modelos imutáveis, contratos e erros.
- `src/live_translator/application/`: orquestração do pipeline, loop de captura e configurações de perfil.
- `src/live_translator/infrastructure/`: SQLite, captura MSS, utilitários de imagem e Ollama.
- `src/live_translator/ui/`: overlay e janela de configuração PySide6.
- `src/live_translator/app/`: bootstrap, composition root e entrada principal.

Regra central: UI não acessa SQLite, Ollama ou captura diretamente; o bootstrap conecta implementações concretas.

## Testes

```powershell
.venv\Scripts\python.exe -m pytest
```

A suíte cobre cache SQLite, pipeline de tradução, loop de captura, utilitários de imagem, client Ollama, scripts de perfil/captura e bootstrap.

## Licença

Este projeto usa a licença MIT. Consulte `LICENSE` para os termos completos.

---
Desenvolvido por [Allan Giaretta](https://github.com/AllanGiaretta26)
