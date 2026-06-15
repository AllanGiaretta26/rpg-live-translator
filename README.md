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
- [Licença](#licença)

## Sobre o projeto

O RPG Live Translator captura texto de jogos e exibe a tradução em um overlay transparente. O app não modifica arquivos do jogo durante captura, OCR, importação de catálogo ou tradução em runtime; alterações em JSONs só acontecem nas ações explícitas de aplicar/restaurar patch MV/MZ.

Ele funciona em dois modos:

| Modo | Como funciona | Quando usar |
|---|---|---|
| Universal | Captura uma região da tela, usa Ollama com visão computacional para extrair o texto e traduzir. | Qualquer jogo ou janela. |
| RPG Maker MV/MZ | Lê o catálogo JSON do jogo e recebe falas em tempo real por um plugin local. | Jogos MV/MZ com acesso à pasta `data/` ou `www/data/`. |

Resultados ficam em cache SQLite. Textos e imagens já processados não precisam ser traduzidos de novo. Traduções antigas do cache que parecem contaminadas por contexto, instruções de prompt ou códigos RPG Maker perdidos são ignoradas e recriadas automaticamente.

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

- importação read-only dos JSONs em `www/data/` ou `data/`;
- plugin runtime opcional para enviar falas atuais ao app sem OCR.
- geração/aplicação explícita de patch traduzido, com backup antes de sobrescrever JSONs do jogo.

Arquivos importados:

- `Map*.json` e `CommonEvents.json`;
- `Items.json`, `Skills.json`, `Weapons.json`, `Armors.json`, `States.json`, `Classes.json`, `Enemies.json`, `Actors.json`, `System.json`, `Troops.json` e `Scenario.json`, quando presentes.

Textos extraídos: mensagens, escolhas, texto rolante, nomes e descrições de itens, skills, armas, armaduras, estados, classes, inimigos, atores, termos de sistema/menu, eventos de batalha e cenas custom.

Traduções geradas ficam no cache `translations`, isoladas pelo caminho do projeto ativo.

### Instalar `LiveTranslatorBridge.js`

O plugin runtime é opcional, mas é o caminho recomendado no modo MV/MZ: ele envia a fala renderizada pelo jogo direto para o app, sem OCR. O arquivo fica em:

```text
src/live_translator/infrastructure/rpgmaker/plugin/LiveTranslatorBridge.js
```

Instalação pelo editor RPG Maker:

1. Feche o jogo antes de alterar arquivos.
2. Copie `LiveTranslatorBridge.js` para a pasta de plugins do jogo (`js/plugins/` ou `www/js/plugins/`).
3. Mantenha o nome do arquivo exatamente como `LiveTranslatorBridge.js`.
4. Abra o projeto no RPG Maker.
5. Acesse `Tools` > `Plugin Manager`.
6. Crie uma nova entrada, escolha `LiveTranslatorBridge` e deixe `Status` como `ON`.
7. Confirme o parâmetro `Endpoint`: o padrão deve ser `http://127.0.0.1:8765/rpgmaker/text`.
8. Salve o projeto.
9. Rode o app, escolha `RPG Maker MV/MZ`, importe o catálogo e inicie o jogo.

Instalação manual, útil para jogo distribuído ou Steam sem acesso ao Plugin Manager:

1. Feche o jogo e faça backup de `js/plugins.js` ou `www/js/plugins.js`.
2. Copie `LiveTranslatorBridge.js` para `js/plugins/` ou `www/js/plugins/`, conforme a estrutura do jogo.
3. Abra `plugins.js` em um editor de texto.
4. Dentro da lista `var $plugins = [...]`, adicione:

```js
{
  name: "LiveTranslatorBridge",
  status: true,
  description: "Sends RPG Maker MV/MZ dialogue text to RPG Live Translator.",
  parameters: {
    Endpoint: "http://127.0.0.1:8765/rpgmaker/text"
  }
}
```

5. Mantenha as vírgulas da lista válidas se já existirem outras entradas.
6. Salve `plugins.js`, rode o app em modo `RPG Maker MV/MZ` e abra o jogo.

Se você alterou `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT`, ajuste também o parâmetro `Endpoint` do plugin para usar a mesma porta.

### Recuperar plugin após atualização ou verificação da Steam

Atualizações do jogo ou a opção `Verify integrity of game files` da Steam podem sobrescrever `plugins.js`. Quando o modo MV/MZ parar de receber falas depois de uma atualização:

1. Feche o jogo e o app.
2. Confira se `LiveTranslatorBridge.js` ainda existe em `js/plugins/` ou `www/js/plugins/`.
3. Se `plugins.js` foi recriado, restaure o backup feito antes da instalação manual ou adicione de novo a entrada `LiveTranslatorBridge` pelo Plugin Manager.
4. Confirme se o `Endpoint` continua usando a mesma porta do `.env`, por padrão `http://127.0.0.1:8765/rpgmaker/text`.
5. Abra o app em modo `RPG Maker MV/MZ`, inicie o jogo e avance uma fala. `Fonte MV/MZ` deve deixar de mostrar `aguardando`.
6. Reimporte o catálogo somente se a atualização também alterou arquivos em `data/` ou `www/data/`.

Quando o jogo chama mensagens ou escolhas, o plugin envia o texto para o app. O app busca no cache, traduz quando necessário e atualiza o overlay sem passar por captura/OCR.

### Diagnóstico MV/MZ

No modo `RPG Maker MV/MZ`, a aba `Executar` mostra:

- `Fonte MV/MZ`: último texto recebido pela bridge;
- `Traducao MV/MZ`: última tradução aceita pelo runtime;
- `Pipeline`: caminho usado, como `runtime cache texto`, `runtime cache inválido` ou `runtime traduzido`;
- `Tempo`: tempo do runtime MV/MZ.

Use esses campos para identificar a origem do problema:

- se `Fonte MV/MZ` já vier errada, o problema está no plugin ou no fluxo do jogo;
- se `Fonte MV/MZ` vier limpa e `Traducao MV/MZ` vier contaminada, o problema está no modelo ou no cache;
- se `Pipeline` mostrar `runtime cache texto`, a tradução veio do cache `translations`;
- se `Pipeline` mostrar `runtime cache inválido`, o cache antigo foi ignorado e o app está tentando gerar uma nova tradução;
- se `Pipeline` mostrar `projeto MV/MZ inacessível`, o caminho salvo do projeto ficou inválido. Selecione a pasta do jogo novamente na aba `Modo`.

Controles úteis quando aparecer uma tradução ruim:

- `Limpar cache contaminado`: varre o catálogo MV/MZ ativo e remove do cache apenas traduções que parecem conter contexto ou instruções de prompt;
- `Reprocessar fala atual`: remove o cache da última `Fonte MV/MZ` recebida e traduz novamente;
- `Ver erros do ultimo lote`: abre a lista de falhas salvas do lote mais recente, com origem e mensagem de erro;
- `Cache: X/Y entradas ja traduzidas`: mostra quantos textos do catálogo atual já possuem tradução válida no cache. Traduções contaminadas não entram na contagem.

No lote MV/MZ, cache existente só conta como hit quando a tradução parece válida. O lote também envia falas anteriores do mesmo evento como contexto para o modelo, melhorando pronomes, tom e sentido das traduções. O padrão são 4 falas; ajuste com `LIVE_TRANSLATOR_RPG_MAKER_BATCH_CONTEXT_LINES` no `.env`.

Textos que contêm apenas pontuação ou controle, como `...`, são mantidos como estão e não são enviados ao modelo. Se um cache antigo expandiu esse tipo de texto para uma fala inventada, `Limpar cache contaminado` remove a entrada e o próximo lote salva o passthrough correto.

### Patch de tradução MV/MZ

A área `Patch de traducao` gera arquivos JSON traduzidos para resolver partes que o overlay não substitui bem, como escolhas dentro da UI do jogo. O fluxo usa apenas o catálogo MV/MZ já importado e as traduções existentes no cache; ele não chama Ollama durante a geração.

Escopo atual do patch:

| Arquivo | Conteúdo traduzido |
|---|---|
| `Map*.json`, `CommonEvents.json` | Mensagens, escolhas, texto rolante, speakers opcionais |
| `Items.json`, `Skills.json` | Nomes, descrições, mensagens |
| `Weapons.json`, `Armors.json` | Nomes e descrições |
| `States.json`, `Classes.json` | Nomes e mensagens |
| `Enemies.json`, `Actors.json` | Nomes |
| `System.json` | Termos de sistema/menu, como `Item` e `Skill` |
| `Troops.json` | Mensagens, escolhas, texto rolante e speakers de batalha |
| `Scenario.json` | Mensagens, escolhas, texto rolante e nomes `Tachie showName` |

`Gerar patch` cria uma pasta separada em:

```text
exports/patches/<nome-do-jogo>-ptBR-<timestamp>/data/
```

O patcher substitui textos pela origem exata do catálogo e valida arquivo, evento, página, comando e parâmetro antes de alterar. Mensagens longas são quebradas em linhas menores para reduzir o risco de saírem da caixa de texto do jogo. Códigos RPG Maker como `\N[1]`, `\V[2]`, `\C[3]` e `\I[64]`, e placeholders como `%1`, `%2` e `%3`, precisam ser preservados na tradução. Se a tradução em cache perder esses códigos, ela é tratada como inválida.

Textos sem cache, com tradução contaminada ou com texto original que não bate mais com o JSON do jogo são pulados e aparecem no relatório:

```text
live-translator-patch-report.json
live-translator-patch-report.md
```

`Aplicar patch` copia os JSON gerados para `data/` ou `www/data/` do projeto ativo. Antes de sobrescrever, o app cria backup automático em:

```text
backups/patches/<nome-do-jogo>-<timestamp>/data/
```

`Restaurar ultimo backup` restaura o backup mais recente criado pelo app para o projeto ativo. O app não apaga patches nem backups automaticamente. Depois de atualizar o app, reimporte o catálogo antes de gerar um novo patch para incluir arquivos recém-suportados.

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
| `Fonte MV/MZ` continua `aguardando` | Confirme modo `RPG Maker MV/MZ`, endpoint `http://127.0.0.1:8765/rpgmaker/text`, plugin ativo e porta igual ao `.env`. Se parou após atualização da Steam, recrie a entrada em `plugins.js`. |
| Tradução ruim reaparece | Use `Limpar cache contaminado` ou `Reprocessar fala atual`. |
| Patch pulou entradas | Leia `live-translator-patch-report.md`; o texto do JSON pode ter mudado desde a importação ou a tradução em cache pode estar inválida. |

## Limitações conhecidas

- Não existe build empacotado para Windows; o app roda pelo ambiente Python local.
- A captura usa coordenadas absolutas da tela. Se o jogo ou monitor mudar de posição, a área precisa ser recalibrada.
- O modo universal depende de OCR/visão. O modo MV/MZ reduz essa dependência, mas textos gerados por plugins customizados podem exigir fallback.
- Plugins customizados ainda podem armazenar textos fora dos JSONs padrão e de `Scenario.json`.
- Logs persistentes gerais do runtime ainda não foram implementados; o diagnóstico principal fica no painel `Status`.
- O modo click-through do overlay ainda não é configurável pela UI.

## Licença

Este projeto usa a licença MIT. Consulte [`LICENSE`](LICENSE) para os termos completos.

---
Desenvolvido por [Allan Giaretta](https://github.com/AllanGiaretta26)
