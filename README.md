# RPG Live Translator

![Python](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?logo=windows&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-UI-41CD52?logo=qt&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-LLM-black)
![SQLite](https://img.shields.io/badge/cache-SQLite-003B57?logo=sqlite&logoColor=white)
![Licença](https://img.shields.io/badge/licença-MIT-green)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

> Aplicativo desktop Windows para traduzir em tempo real textos de jogos RPG Maker para o português brasileiro.

## Sobre o Projeto

O **RPG Live Translator** captura texto de jogos e exibe a tradução em um overlay transparente, sem modificar os arquivos do jogo. Funciona em dois modos:

- **Universal**: captura uma região da tela, usa Ollama com visão computacional (OCR) para extrair e traduzir o texto. Compatível com qualquer jogo.
- **RPG Maker MV/MZ**: lê o catálogo JSON do jogo e recebe falas em tempo real via plugin local, eliminando a dependência de OCR nos jogos suportados.

Resultados são armazenados em cache SQLite — textos e imagens já processados não precisam ser retraduzidos. Em ambos os modos, traduções antigas do cache que parecem contaminadas (contexto, instruções de prompt, códigos RPG Maker perdidos) são ignoradas e retraduzidas automaticamente.

## Requisitos

- Windows 10/11
- Python 3.13 ou superior
- [Ollama](https://ollama.com) rodando em `http://127.0.0.1:11434`
- Modelo `gemma4:e4b` instalado no Ollama (`ollama pull gemma4:e4b`)

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev,desktop]
```

Valide a instalação:

```powershell
.venv\Scripts\python.exe -m pytest
```

## Rodar o App

```powershell
.venv\Scripts\pythonw.exe -m live_translator.app.main
```

A janela principal abre em modo de calibração. O fluxo básico de configuração está descrito abaixo.

## Configurar pelo App

Abra o app e use as abas da janela de calibração:

1. **Modo**: escolha `Universal` ou `RPG Maker MV/MZ`. No modo MV/MZ, selecione a pasta do jogo e clique em `Importar catálogo`.
2. **Catálogo**: confira os textos importados, use `Traduzir selecionado` para testar uma entrada ou `Traduzir catálogo` para preencher o cache em lote. O lote permite escolher `100`, `500` ou `Todos` e filtrar por tipo, com os tipos agrupados em categorias (mensagens e eventos, database e batalha), além de pausar, retomar e cancelar. Por padrão, `speaker` fica desativado para evitar traduzir nomes próprios. A aba também mostra quantas entradas já possuem tradução em cache, permite limpar traduções contaminadas do projeto atual e consultar os erros do último lote.
3. **Área do texto**: clique em `Selecionar área do texto`, arraste sobre a caixa de texto do jogo e confira o recorte em `Ver preview da área`. O preview deve mostrar somente a área enviada ao OCR.
4. **Overlay**: clique em `Ajustar overlay`, arraste a tradução de teste para mover e arraste bordas ou cantos para redimensionar. Mantenha o overlay fora da área capturada para evitar que o OCR leia a tradução em vez do jogo.
5. **Executar**: pause, retome e acompanhe o estado da captura e do pipeline. A linha `Tempo` mostra o último frame processado, por exemplo: `total 3.40s | ocr 1.42s | traducao 1.36s | cache miss`. No modo MV/MZ, esta aba também mostra a última fonte recebida pela bridge e a última tradução aceita pelo runtime. Use `Reprocessar fala atual` para apagar o cache da fala runtime atual e forçar uma nova tradução.

Clique em `Salvar área` e `Salvar overlay` para manter os ajustes após reiniciar.

## Configurar Região por Script

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

O app não modifica arquivos do jogo. O suporte MV/MZ tem duas partes:

- importação read-only dos JSONs em `www/data/` ou `data/`;
- plugin runtime opcional para enviar falas atuais ao app sem OCR.

Arquivos importados:

- `Map*.json` e `CommonEvents.json`
- `Items.json`, `Skills.json`, `Weapons.json`, `Armors.json`, `States.json`, `Classes.json`, `Enemies.json`, `Actors.json`, `System.json`, `Troops.json` e `Scenario.json` (quando presentes)

Textos extraídos: comandos de mensagem, escolhas, texto rolante, nomes e descrições de itens, skills, armas, armaduras, estados, classes, inimigos, atores, termos de sistema/menu, eventos de batalha e cenas custom.

Traduções geradas ficam no cache `translations`, isoladas pelo caminho do projeto ativo.

### Instalar `LiveTranslatorBridge.js`

O plugin runtime é opcional, mas é o caminho recomendado no modo MV/MZ: ele envia a fala renderizada pelo jogo direto para o app, sem OCR. O arquivo fica em:

```
src/live_translator/infrastructure/rpgmaker/plugin/LiveTranslatorBridge.js
```

**Instalação pelo editor RPG Maker:**

1. Feche o jogo antes de alterar arquivos.
2. Copie `LiveTranslatorBridge.js` para a pasta de plugins do jogo (`js/plugins/` ou `www/js/plugins/`).
3. Mantenha o nome do arquivo exatamente como `LiveTranslatorBridge.js`.
4. Abra o projeto no RPG Maker.
5. Acesse `Tools` > `Plugin Manager`.
6. Crie uma nova entrada, escolha `LiveTranslatorBridge` e deixe `Status` como `ON`.
7. Confirme o parâmetro `Endpoint`: o padrão deve ser `http://127.0.0.1:8765/rpgmaker/text`.
8. Salve o projeto.
9. Rode o app, escolha `RPG Maker MV/MZ`, importe o catálogo e inicie o jogo.

**Instalação manual (jogo distribuído ou Steam sem acesso ao Plugin Manager):**

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

Quando o jogo chama mensagens ou escolhas, o plugin envia o texto para o app. O app busca no cache, traduz quando necessário e atualiza o overlay sem passar por captura/OCR.

Para validar a instalação, abra a aba `Executar` no app. Ao avançar uma fala no jogo, `Fonte MV/MZ` deve mostrar o texto recebido pela bridge. Se continuar `aguardando`, confirme se o app está aberto em modo `RPG Maker MV/MZ`, se o endpoint do plugin está correto e se o plugin está ativo em `plugins.js`.

### Diagnóstico MV/MZ

No modo `RPG Maker MV/MZ`, a aba `Executar` mostra:

- `Fonte MV/MZ`: último texto recebido pela bridge;
- `Tradução MV/MZ`: última tradução aceita pelo runtime;
- `Pipeline`: caminho usado, como `runtime cache texto`, `runtime cache inválido` ou `runtime traduzido`;
- `Tempo`: tempo do runtime MV/MZ.

Use esses campos para identificar a origem do problema:

- se `Fonte MV/MZ` já vier errada, o problema está no plugin ou no fluxo do jogo;
- se `Fonte MV/MZ` vier limpa e `Tradução MV/MZ` vier contaminada, o problema está no modelo ou no cache;
- se `Pipeline` mostrar `runtime cache texto`, a tradução veio do cache `translations`;
- se `Pipeline` mostrar `runtime cache inválido`, o cache antigo foi ignorado e o app está tentando gerar uma nova tradução;
- se `Pipeline` mostrar `projeto MV/MZ inacessível`, o caminho salvo do projeto ficou inválido (jogo movido, renomeado ou atualizado pela Steam) — selecione a pasta do jogo novamente na aba `Modo`.

O runtime MV/MZ valida traduções vindas do cache. Entradas antigas que parecem conter contexto ou instruções de prompt são ignoradas e sobrescritas por uma nova tradução quando a fala aparecer novamente.

**Controles úteis quando aparecer uma tradução ruim:**

- `Limpar cache contaminado`: varre o catálogo MV/MZ ativo e remove do cache apenas traduções que parecem conter contexto ou instruções de prompt;
- `Reprocessar fala atual`: remove o cache da última `Fonte MV/MZ` recebida e traduz novamente;
- `Ver erros do último lote`: abre a lista de falhas salvas do lote mais recente, com origem e mensagem de erro;
- `Cache: X/Y entradas já traduzidas`: mostra quantos textos do catálogo atual já possuem tradução válida no cache. Traduções contaminadas não entram na contagem.

No lote MV/MZ, cache existente só conta como hit quando a tradução parece válida. Se a entrada em cache parecer conter contexto ou instrução de prompt, o lote tenta traduzir novamente e sobrescrever. O status final mostra processados, traduzidos, cache hits, erros, tempo total e média por tradução real.

Textos que contêm apenas pontuação ou controle, como `...`, são mantidos como estão e não são enviados ao modelo. Se um cache antigo expandiu esse tipo de texto para uma fala inventada, `Limpar cache contaminado` remove a entrada e o próximo lote salva o passthrough correto.

### Patch de Tradução MV/MZ

A área `Patch de tradução` gera arquivos JSON traduzidos para resolver partes que o overlay não substitui bem, como escolhas dentro da UI do jogo. O fluxo usa apenas o catálogo MV/MZ já importado e as traduções existentes no cache — não chama Ollama durante a geração.

**Escopo atual do patch:**

| Arquivo | Conteúdo traduzido |
|---|---|
| `Map*.json`, `CommonEvents.json` | Mensagens, escolhas, texto rolante, speakers (opcional) |
| `Items.json`, `Skills.json` | Nomes, descrições, mensagens |
| `Weapons.json`, `Armors.json` | Nomes e descrições |
| `States.json`, `Classes.json` | Nomes e mensagens |
| `Enemies.json`, `Actors.json` | Nomes |
| `System.json` | Termos de sistema/menu (ex.: `Item`, `Skill`) |
| `Troops.json` | Mensagens, escolhas, texto rolante e speakers de batalha |
| `Scenario.json` | Mensagens, escolhas, texto rolante e nomes `Tachie showName` |

`Gerar patch` cria uma pasta separada em:

```
exports/patches/<nome-do-jogo>-ptBR-<timestamp>/data/
```

O patcher substitui textos pela origem exata do catálogo e valida arquivo, evento, página, comando e parâmetro antes de alterar. Mensagens longas são quebradas em linhas menores para reduzir o risco de saírem da caixa de texto do jogo. Códigos RPG Maker como `\N[1]`, `\V[2]`, `\C[3]` e `\I[64]`, e placeholders como `%1`, `%2` e `%3`, precisam ser preservados na tradução — se a tradução em cache perder esses códigos, ela é tratada como inválida. Textos sem cache, com tradução contaminada ou com texto original que não bate mais com o JSON do jogo são pulados e aparecem no relatório:

```
live-translator-patch-report.json
live-translator-patch-report.md
```

`Aplicar patch` copia os JSON gerados para `data/` ou `www/data/` do projeto ativo. Antes de sobrescrever, o app cria backup automático em:

```
backups/patches/<nome-do-jogo>-<timestamp>/data/
```

`Restaurar último backup` restaura o backup mais recente criado pelo app para o projeto ativo. O app não apaga patches nem backups automaticamente. Depois de atualizar o app, reimporte o catálogo antes de gerar um novo patch para incluir arquivos recém-suportados.

## Arquitetura

Monólito em camadas sob `src/live_translator/`. A regra central é: **UI e infraestrutura dependem do domínio; o domínio não depende de nada externo.**

| Camada | Responsabilidade |
|---|---|
| `domain/` | Modelos imutáveis, contratos (Protocols) e heurísticas de qualidade de tradução. Sem dependências externas. |
| `application/` | Orquestração: pipeline de tradução, loop de captura, serviços MV/MZ. |
| `infrastructure/` | Adaptadores concretos: SQLite, MSS, Ollama, utilitários de imagem, bridge HTTP. |
| `ui/` | Janela principal, overlay e seletor de região (PySide6). |
| `app/bootstrap.py` | Composition root — único lugar onde implementações concretas são conectadas aos Protocols. |

A UI nunca acessa SQLite, Ollama ou captura diretamente; tudo passa pelos serviços de aplicação.

## Testes

```powershell
.venv\Scripts\python.exe -m pytest
```

A suíte cobre cache SQLite, pipeline de tradução, loop de captura, utilitários de imagem, client Ollama, scripts de perfil/captura e bootstrap. Os testes rodam sem dependências de desktop, Ollama ou display.

## Limitações Conhecidas

- Não existe build empacotado para Windows; o app roda pelo ambiente Python local.
- A captura usa coordenadas absolutas da tela. Se o jogo ou monitor mudar de posição, a área precisa ser recalibrada.
- O modo universal depende de OCR/visão. O modo MV/MZ reduz essa dependência, mas textos gerados por plugins customizados podem exigir fallback.
- Plugins customizados ainda podem armazenar textos fora dos JSONs padrão e de `Scenario.json`.
- Logs persistentes gerais do runtime ainda não foram implementados; o diagnóstico principal fica no painel `Status`.
- O modo click-through do overlay ainda não é configurável pela UI.

## Licença

Este projeto usa a licença MIT. Consulte `LICENSE` para os termos completos.

---
Desenvolvido por [Allan Giaretta](https://github.com/AllanGiaretta26)
