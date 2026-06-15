# RPG Live Translator

![Python](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?logo=windows&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-UI-41CD52?logo=qt&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-LLM-black)
![SQLite](https://img.shields.io/badge/cache-SQLite-003B57?logo=sqlite&logoColor=white)
![Licença](https://img.shields.io/badge/licença-MIT-green)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

> Aplicativo desktop Windows para traduzir em tempo real textos de jogos RPG Maker para o português brasileiro.

## Conteúdo

- [Sobre o projeto](#sobre-o-projeto)
- [Demonstração](#demonstração)
- [Status do projeto](#status-do-projeto)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Rodar o app](#rodar-o-app)
- [Configurar pelo app](#configurar-pelo-app)
- [Configuração avançada](#configuração-avançada)
- [Configurar região por script](#configurar-região-por-script)
- [Modo RPG Maker MV/MZ](#modo-rpg-maker-mvmz)
- [Arquitetura](#arquitetura)
- [Testes](#testes)
- [Mapa da documentação](#mapa-da-documentação)
- [Solução de problemas rápida](#solução-de-problemas-rápida)
- [Limitações conhecidas](#limitações-conhecidas)
- [Como contribuir](#como-contribuir)
- [Licença](#licença)

## Sobre o projeto

O RPG Live Translator captura texto de jogos e exibe a tradução em um overlay transparente. O app não modifica arquivos do jogo durante captura, OCR, importação de catálogo ou tradução em runtime; alterações em JSONs só acontecem nas ações explícitas de aplicar/restaurar patch MV/MZ.

Ele funciona em dois modos:

| Modo | Como funciona | Quando usar |
|---|---|---|
| Universal | Captura uma região da tela, usa Ollama com visão computacional para extrair o texto e traduzir. | Qualquer jogo ou janela. |
| RPG Maker MV/MZ | Lê o catálogo JSON do jogo e recebe falas em tempo real por um plugin local. | Jogos MV/MZ com acesso à pasta `data/` ou `www/data/`. |

Resultados ficam em cache SQLite. Textos e imagens já processados não precisam ser traduzidos de novo. Traduções antigas do cache que parecem contaminadas por contexto, instruções de prompt ou códigos RPG Maker perdidos são ignoradas e recriadas automaticamente.

## Demonstração

> Capturas de tela e um GIF do overlay traduzindo falas em tempo real serão
> adicionados aqui em uma próxima atualização.

<!-- ![Overlay traduzindo uma fala em tempo real](./assets/overlay-demo.png) -->

## Status do projeto

Em desenvolvimento ativo, na versão `0.6.0` (veja [`CHANGELOG.md`](CHANGELOG.md)). Os dois modos (`Universal` e `RPG Maker MV/MZ`) funcionam ponta a ponta e são cobertos por 259 testes automatizados. Os próximos passos planejados ficam em [`docs/next-steps/mvmz-checklist.md`](docs/next-steps/mvmz-checklist.md).

## Requisitos

- Windows 10/11.
- Python 3.13 ou superior.
- [Ollama](https://ollama.com) em `http://127.0.0.1:11434`.
- Modelo `gemma4:e4b` instalado no Ollama:

```powershell
ollama pull gemma4:e4b
```

## Instalação

Crie o ambiente local e instale o app com as dependências de desenvolvimento e desktop:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev,desktop]
```

Valide a instalação:

```powershell
.venv\Scripts\python.exe -m pytest
```

A suíte de testes não exige desktop, display ou servidor Ollama ativo.

## Rodar o app

```powershell
.venv\Scripts\pythonw.exe -m live_translator.app.main
```

A janela principal abre em modo de calibração. Se o Ollama estiver fora do ar, o app mostra um aviso no overlay e continua aberto para permitir ajustes de região, modo e cache.

## Configurar pelo app

Abra o app e use as abas da janela de calibração:

1. **Modo**: escolha `Universal` ou `RPG Maker MV/MZ`. No modo MV/MZ, selecione a pasta do jogo e clique em `Importar catalogo`.
2. **Catálogo**: confira os textos importados, use `Traduzir selecionado` para testar uma entrada ou `Traduzir catalogo` para preencher o cache em lote. O lote permite escolher `100`, `500` ou `Todos`, filtrar por tipo e pausar, retomar ou cancelar. Por padrão, `speaker` fica desativado para evitar traduzir nomes próprios. Tradução individual e retradução por ID não usam contexto de falas anteriores; contexto é aplicado apenas ao lote MV/MZ.
3. **Área do texto**: clique em `Selecionar area do texto`, arraste sobre a caixa de texto do jogo e confira o recorte em `Ver preview da area`. O preview deve mostrar somente a área enviada ao OCR.
4. **Overlay**: clique em `Ajustar overlay`, arraste a tradução de teste para mover e arraste bordas ou cantos para redimensionar. Mantenha o overlay fora da área capturada para evitar que o OCR leia a tradução em vez do jogo.
5. **Executar**: pause, retome e acompanhe o estado da captura e do pipeline. A linha `Tempo` mostra o último frame processado, por exemplo: `total 3.40s | ocr 1.42s | traducao 1.36s | cache miss`. No modo MV/MZ, esta aba também mostra a última fala recebida pela bridge e a última tradução aceita pelo runtime.

Clique em `Salvar area` e `Salvar overlay` para manter os ajustes após reiniciar.

## Configuração avançada

O app lê variáveis de ambiente com prefixo `LIVE_TRANSLATOR_` e também um arquivo `.env` na raiz do projeto. A tabela abaixo cobre as opções que alteram o fluxo principal. Ajustes feitos pela UI, como modo ativo, projeto MV/MZ, posição, tamanho, fonte e opacidade do overlay, ficam no SQLite e não precisam entrar no `.env`.

| Variável | Padrão | Uso |
|---|---:|---|
| `LIVE_TRANSLATOR_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | URL do Ollama. |
| `LIVE_TRANSLATOR_OLLAMA_MODEL` | `gemma4:e4b` | Modelo usado para OCR/visão e tradução. |
| `LIVE_TRANSLATOR_OLLAMA_TIMEOUT_SECONDS` | `10.0` | Timeout das chamadas ao modelo. |
| `LIVE_TRANSLATOR_CAPTURE_INTERVAL_MS` | `500` | Intervalo entre capturas no modo universal. |
| `LIVE_TRANSLATOR_SOURCE_LANGUAGE` | `auto` | Idioma de origem enviado ao tradutor. |
| `LIVE_TRANSLATOR_TARGET_LANGUAGE` | `pt-BR` | Idioma de destino. |
| `LIVE_TRANSLATOR_DATABASE_PATH` | `data/app.sqlite3` | Caminho do banco SQLite local. |
| `LIVE_TRANSLATOR_CAPTURE_PREVIEW_PATH` | `captures/preview.png` | Saída do preview de captura. |
| `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_ENABLED` | `true` | Liga ou desliga o servidor local MV/MZ. |
| `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_HOST` | `127.0.0.1` | Host do servidor local MV/MZ. |
| `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT` | `8765` | Porta do endpoint `/rpgmaker/text`. |
| `LIVE_TRANSLATOR_PATCH_MESSAGE_LINE_LIMIT` | `58` | Largura de linha para mensagens no patch MV/MZ. |
| `LIVE_TRANSLATOR_PATCH_MESSAGE_FACE_LINE_LIMIT` | `44` | Largura de linha quando há face no diálogo. |
| `LIVE_TRANSLATOR_PATCH_DESCRIPTION_LINE_LIMIT` | `52` | Largura de linha para descrições. |
| `LIVE_TRANSLATOR_RPG_MAKER_BATCH_CONTEXT_LINES` | `4` | Falas anteriores usadas como contexto no lote MV/MZ; use `0` para desativar. |

Exemplo de `.env`:

```dotenv
LIVE_TRANSLATOR_OLLAMA_MODEL=gemma4:e4b
LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT=8765
LIVE_TRANSLATOR_RPG_MAKER_BATCH_CONTEXT_LINES=4
```

## Configurar região por script

Crie ou atualize o perfil ativo:

```powershell
.venv\Scripts\python.exe -m live_translator.scripts.create_profile --name "Meu Jogo" --window-title "Manual Region" --x 256 --y 950 --width 2048 --height 360
```

Teste a captura:

```powershell
.venv\Scripts\python.exe -m live_translator.scripts.capture_region --output captures\latest.png
```

Abra `captures\latest.png` e ajuste `x`, `y`, `width` e `height` até a imagem conter a caixa de diálogo do jogo.

## Modo RPG Maker MV/MZ

O app não modifica arquivos do jogo durante importação, tradução em lote ou runtime. O suporte MV/MZ tem três partes:

- **Importação** read-only do catálogo JSON em `data/` ou `www/data/` (mapas, eventos comuns, database e termos de sistema).
- **Plugin runtime** opcional (`LiveTranslatorBridge.js`) que envia a fala atual ao app sem OCR.
- **Patch de tradução**: geração/aplicação explícita de JSONs traduzidos, com backup automático antes de sobrescrever arquivos do jogo.

### Início rápido

1. Na aba `Modo`, escolha `RPG Maker MV/MZ`, selecione a pasta do jogo e clique em `Importar catalogo`.
2. Copie `src/live_translator/infrastructure/rpgmaker/plugin/LiveTranslatorBridge.js` para `js/plugins/` (ou `www/js/plugins/`) do jogo.
3. No RPG Maker, abra `Tools` > `Plugin Manager`, adicione `LiveTranslatorBridge` com `Status: ON` e confirme o `Endpoint` (`http://127.0.0.1:8765/rpgmaker/text`).
4. Rode o jogo. Na aba `Executar`, `Fonte MV/MZ` deve deixar de mostrar `aguardando`.

Para instalação manual (Steam, sem Plugin Manager), recuperação do plugin após uma atualização, diagnóstico em tempo real e o fluxo completo de patch de tradução, veja o guia [`docs/rpg-maker-mvmz.md`](docs/rpg-maker-mvmz.md).

## Arquitetura

Monólito em camadas sob `src/live_translator/`. A regra central é: a UI e a infraestrutura dependem do domínio; o domínio não depende de nada externo.

| Camada | Responsabilidade |
|---|---|
| `domain/` | Modelos imutáveis, contratos (`Protocol`) e heurísticas de qualidade de tradução. Sem dependências externas. |
| `application/` | Orquestração: pipeline de tradução, loop de captura, serviços MV/MZ. |
| `infrastructure/` | Adaptadores concretos: SQLite, MSS, Ollama, utilitários de imagem, bridge HTTP. |
| `ui/` | Janela principal, overlay e seletor de região em PySide6. |
| `app/bootstrap.py` | Composition root: único lugar onde implementações concretas são conectadas aos contratos. |

A UI nunca acessa SQLite, Ollama ou captura diretamente. Tudo passa pelos serviços de aplicação. Para detalhes de dependência, falhas e testes, leia [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Testes

```powershell
.venv\Scripts\python.exe -m pytest
```

A suíte cobre cache SQLite, pipeline de tradução, loop de captura, utilitários de imagem, client Ollama, scripts de perfil/captura e bootstrap. Os testes rodam sem dependências de desktop, Ollama ou display.

## Mapa da documentação

| Documento | Uso |
|---|---|
| [`README.md`](README.md) | Guia de instalação e uso. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Arquitetura atual e regras de dependência. |
| [`docs/rpg-maker-mvmz.md`](docs/rpg-maker-mvmz.md) | Guia completo do modo RPG Maker MV/MZ: plugin, diagnóstico e patch. |
| [`docs/README.md`](docs/README.md) | Índice e padrão da documentação do repositório. |
| [`docs/BRIEFING.md`](docs/BRIEFING.md) | Contexto de produto e planejamento inicial. |
| [`docs/next-steps/mvmz-checklist.md`](docs/next-steps/mvmz-checklist.md) | Checklist de próximos passos MV/MZ. |
| [`docs/relatorios/`](docs/relatorios/) | Checkpoints históricos do projeto. |
| [`docs/auditorias/`](docs/auditorias/) | Auditorias técnicas e de documentação. |
| [`CHANGELOG.md`](CHANGELOG.md) | Histórico de versões e mudanças relevantes. |

## Solução de problemas rápida

| Sintoma | O que conferir |
|---|---|
| App abre, mas não traduz | Confirme se o Ollama está rodando e se `ollama pull gemma4:e4b` foi executado. |
| Overlay mostra a própria tradução | Mova o overlay para fora da área capturada e salve a posição. |
| Preview captura a região errada | Refaça `Selecionar area do texto` ou ajuste o perfil pelo script `create_profile`. |
| `Fonte MV/MZ` continua `aguardando` | Confirme modo `RPG Maker MV/MZ`, plugin ativo e porta igual ao `.env`. Para instalação manual e recuperação após atualização da Steam, veja [`docs/rpg-maker-mvmz.md`](docs/rpg-maker-mvmz.md). |
| Tradução ruim reaparece | No modo MV/MZ, use `Limpar cache contaminado` ou `Reprocessar fala atual` (detalhes em [`docs/rpg-maker-mvmz.md`](docs/rpg-maker-mvmz.md)); o app também recria traduções contaminadas automaticamente. |
| Patch pulou entradas | Leia `live-translator-patch-report.md` e a seção de patch em [`docs/rpg-maker-mvmz.md`](docs/rpg-maker-mvmz.md); o texto do JSON pode ter mudado desde a importação ou a tradução em cache pode estar inválida. |

## Limitações conhecidas

- Não existe build empacotado para Windows; o app roda pelo ambiente Python local.
- A captura usa coordenadas absolutas da tela. Se o jogo ou monitor mudar de posição, a área precisa ser recalibrada.
- O modo universal depende de OCR/visão. O modo MV/MZ reduz essa dependência, mas textos gerados por plugins customizados podem exigir fallback.
- Plugins customizados ainda podem armazenar textos fora dos JSONs padrão e de `Scenario.json`.
- Logs persistentes gerais do runtime ainda não foram implementados; o diagnóstico principal fica no painel `Status`.
- O modo click-through do overlay ainda não é configurável pela UI.

## Como contribuir

1. Faça um fork do repositório e crie uma branch a partir de `main`.
2. Siga os passos de [Instalação](#instalação) para preparar o ambiente.
3. Rode `.venv\Scripts\python.exe -m pytest` e `ruff check .` antes de abrir o PR.
4. Abra um Pull Request descrevendo o que mudou e por quê.

## Licença

Este projeto usa a licença MIT. Consulte [`LICENSE`](LICENSE) para os termos completos.

---
Desenvolvido por [Allan Giaretta](https://github.com/AllanGiaretta26)
