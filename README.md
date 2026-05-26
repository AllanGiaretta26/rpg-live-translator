# RPG Live Translator

Aplicativo desktop em Python para traduzir, em tempo real, textos exibidos em jogos RPG Maker. O MVP captura uma região da tela, usa Ollama para extrair/traduzir texto, guarda resultados em cache SQLite e mostra a tradução em um overlay PySide6.

## Estado Atual

O projeto já possui um MVP técnico com:

- arquitetura em camadas dentro de `src/live_translator/`;
- cache SQLite por texto e por imagem;
- captura de tela com MSS;
- integração com Ollama usando `gemma4:e4b`;
- overlay PySide6 e janela de configurações com preview de captura;
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

## Configurar Região De Captura

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

A janela de configuração permite editar a região, testar a captura com preview,
selecionar a região visualmente, salvar o perfil, pausar, retomar e fechar o
app. Ela também mostra o estado do loop de captura: `Rodando`, `Capturando`,
`Pausado` ou `Erro`.
O diagnóstico do pipeline indica o último resultado: `sem texto`,
`cache imagem`, `cache texto`, `traduzindo` ou `traduzido`.
O botão `Testar captura` salva a imagem em `captures\preview.png` e mostra o
preview na própria janela.
O botão `Selecionar regiao` abre uma camada transparente; arraste o retângulo
da área de texto do jogo e depois use `Testar captura` para conferir.

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
