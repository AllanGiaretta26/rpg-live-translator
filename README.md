# RPG Live Translator

Aplicativo desktop em Python para traduzir, em tempo real, textos exibidos em jogos RPG Maker. O MVP captura uma região da tela, usa Ollama para extrair/traduzir texto, guarda resultados em cache SQLite e mostra a tradução em um overlay PySide6.

## Estado Atual

O projeto possui um MVP funcional de traducao em tempo real por captura de tela.
O fluxo principal ja cobre calibracao, captura, OCR/vision, traducao, cache,
overlay, pausa/retomada e diagnostico basico de tempo.

- arquitetura em camadas dentro de `src/live_translator/`;
- cache SQLite por texto e por imagem;
- captura de tela com MSS;
- integração com Ollama usando `gemma4:e4b`;
- overlay PySide6 com posição ajustável e janela de calibração guiada;
- seletor fullscreen de area de texto com preview de captura e ajuste para DPI;
- contexto recente desligado por padrao para evitar vazamento de falas anteriores;
- painel de status com tempo total, OCR, traducao e caminho do ultimo frame;
- modo RPG Maker MV/MZ com importacao de catalogo, traducao sob demanda e
  bridge runtime local;
- controles MV/MZ para limpar cache contaminado, reprocessar fala atual e
  consultar erros do ultimo lote;
- scripts de desenvolvimento para criar perfil e testar captura.

O modo universal continua sendo o caminho mais compativel. O modo RPG Maker
MV/MZ reduz dependencia de OCR em jogos suportados ao ler os arquivos JSON do
jogo e receber falas do runtime por plugin.

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

1. `Modo`: escolha `Universal` ou `RPG Maker MV/MZ`. No modo MV/MZ, selecione
   a pasta do jogo e clique em `Importar catalogo`.
2. `Catalogo`: confira textos importados, use `Traduzir selecionado` para
   testar uma entrada ou `Traduzir catalogo` para preencher o cache em lote.
   O lote permite escolher `100`, `500` ou `Todos` e filtrar por tipo, com os
   tipos agrupados em categorias (mensagens e eventos, database e batalha) para
   facilitar a selecao, alem de pausar, retomar e cancelar. Por padrao, `speaker` fica desativado
   para evitar traduzir nomes proprios. A aba tambem mostra quantas entradas ja
   possuem traducao cacheada, permite limpar traducoes contaminadas do projeto
   atual e consultar os erros do ultimo lote.
3. `Area do texto`: clique em `Selecionar area do texto`, arraste sobre a
   caixa de texto do jogo e confira o recorte em `Ver preview da area`. O
   preview deve mostrar somente a area enviada ao OCR.
4. `Overlay`: clique em `Ajustar overlay`, arraste a tradução de teste para
   mover e arraste bordas ou cantos para redimensionar. Mantenha o overlay
   fora da area capturada para evitar que o OCR leia a traducao em vez do jogo.
5. `Executar`: pause, retome e acompanhe o estado da captura e do pipeline.
   A linha `Tempo` mostra o ultimo frame processado, por exemplo:
   `total 3.40s | ocr 1.42s | traducao 1.36s | cache miss`.
   No modo MV/MZ, esta aba tambem mostra a ultima fonte recebida pela bridge e
   a ultima traducao aceita pelo runtime. Use `Reprocessar fala atual` para
   apagar o cache da fala runtime atual e forcar uma nova traducao.

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

A janela separa a area capturada do overlay de traducao. Os numeros `X`, `Y`,
`Largura` e `Altura` sao mantidos para ajuste fino; o fluxo principal e por
mouse.

Se a traducao parecer repetir falas antigas, verifique primeiro se o preview
contem apenas a caixa de texto atual e se o overlay nao esta dentro da area
capturada.

## Modo RPG Maker MV/MZ

O app nao modifica arquivos do jogo. O suporte MV/MZ tem duas partes:

- importacao read-only dos JSONs em `www/data/` ou `data`;
- plugin runtime opcional para enviar falas atuais ao app sem OCR.

Importacao atual:

- detecta pasta MV/MZ valida;
- le `MapXXX.json` e `CommonEvents.json`;
- le `Items.json`, `Skills.json`, `Weapons.json`, `Armors.json`, `States.json`,
  `Classes.json`, `Enemies.json`, `Actors.json`, `System.json`, `Troops.json`
  e `Scenario.json` quando existirem;
- extrai comandos de mensagem, escolhas, texto rolante, nomes de itens,
  descricoes de itens, nomes de skills, descricoes de skills, mensagens de
  skills, armas, armaduras, estados, classes, inimigos, nomes de atores, termos
  de sistema/menu, eventos de batalha e cenas custom em formato de lista de
  comandos;
- salva textos em `rpg_maker_text_catalog`, com origem rastreavel;
- salva traducoes geradas no cache `translations`, isoladas pelo caminho do
  projeto MV/MZ ativo;
- permite pre-cache em lote com limite, filtros por tipo, progresso, cache hits,
  pausa, retomada e cancelamento;
- persiste erros do ultimo lote em `rpg_maker_batch_errors`, com ID da entrada,
  origem, texto fonte e mensagem do erro.

### Instalar `LiveTranslatorBridge.js`

O plugin runtime e opcional, mas e o caminho recomendado no modo MV/MZ: ele
envia a fala renderizada pelo jogo direto para o app, sem OCR. O arquivo do
plugin fica no repositorio em:

```txt
src/live_translator/infrastructure/rpgmaker/plugin/LiveTranslatorBridge.js
```

Instalacao pelo editor RPG Maker:

1. Feche o jogo antes de alterar arquivos.
2. Copie `LiveTranslatorBridge.js` para a pasta de plugins do jogo:
   - projetos MV/MZ normalmente usam `js/plugins/`;
   - jogos empacotados podem usar `www/js/plugins/`.
3. Mantenha o nome do arquivo exatamente como `LiveTranslatorBridge.js`.
4. Abra o projeto no RPG Maker.
5. Acesse `Tools` > `Plugin Manager`.
6. Crie uma nova entrada, escolha `LiveTranslatorBridge` e deixe `Status` como
   `ON`.
7. Confira o parametro `Endpoint`. O padrao deve ser
   `http://127.0.0.1:8765/rpgmaker/text`.
8. Salve o projeto.
9. Rode o app com `.venv\Scripts\pythonw.exe -m live_translator.app.main`,
   escolha `RPG Maker MV/MZ`, importe o catalogo e inicie o jogo.

Instalacao manual em jogo distribuido ou Steam sem acesso ao Plugin Manager:

1. Feche o jogo e faça backup de `js/plugins.js` ou `www/js/plugins.js`.
2. Copie `LiveTranslatorBridge.js` para `js/plugins/` ou `www/js/plugins/`,
   conforme a estrutura do jogo.
3. Abra `plugins.js` em um editor de texto.
4. Dentro da lista `var $plugins = [...]`, adicione uma entrada como esta:

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

5. Se ja existir uma entrada antes ou depois dela, mantenha as virgulas da lista
   validas.
6. Salve `plugins.js`, rode o app em modo `RPG Maker MV/MZ` e abra o jogo.

Se voce alterou `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT`, ajuste tambem o
parametro `Endpoint` do plugin para usar a mesma porta.

Quando o jogo chama mensagens ou escolhas, o plugin envia o texto para o app. O
app busca no cache, traduz quando necessario e atualiza o overlay sem passar por
captura/OCR.

Para validar a instalacao, abra a aba `Executar` no app. Ao avancar uma fala no
jogo, `Fonte MV/MZ` deve mostrar o texto recebido pela bridge. Se continuar
`aguardando`, confira se o app esta aberto em modo `RPG Maker MV/MZ`, se o
endpoint do plugin esta correto e se o plugin esta ativo em `plugins.js`.

### Diagnostico MV/MZ

No modo `RPG Maker MV/MZ`, a aba `Executar` mostra:

- `Fonte MV/MZ`: ultimo texto recebido pela bridge;
- `Traducao MV/MZ`: ultima traducao aceita pelo runtime;
- `Pipeline`: caminho usado, como `runtime cache texto`, `runtime cache invalido`
  ou `runtime traduzido`;
- `Tempo`: tempo do runtime MV/MZ.

Use esses campos para separar a causa de problemas:

- se `Fonte MV/MZ` ja vier errada, o problema esta no plugin ou no fluxo do jogo;
- se `Fonte MV/MZ` vier limpa e `Traducao MV/MZ` vier contaminada, o problema
  esta no modelo ou no cache;
- se `Pipeline` mostrar `runtime cache texto`, a traducao veio do cache
  `translations`;
- se `Pipeline` mostrar `runtime cache invalido`, o cache antigo foi ignorado e
  o app esta tentando gerar uma nova traducao.

O runtime MV/MZ valida traducoes vindas do cache. Entradas antigas que parecem
conter contexto ou instrucoes de prompt sao ignoradas e sobrescritas por uma
nova traducao quando a fala aparecer novamente.

Controles uteis quando aparecer uma traducao ruim:

- `Limpar cache contaminado`: varre o catalogo MV/MZ ativo e remove do cache
  apenas traducoes que parecem conter contexto ou instrucoes de prompt;
- `Reprocessar fala atual`: remove o cache da ultima `Fonte MV/MZ` recebida e
  traduz novamente;
- `Ver erros do ultimo lote`: abre a lista de falhas salvas do lote mais
  recente, com origem e mensagem de erro;
- `Cache: X/Y entradas ja traduzidas`: mostra quantos textos do catalogo atual
  ja possuem traducao no cache.

No lote MV/MZ, cache existente so conta como hit quando a traducao parece
valida. Se a entrada cacheada parecer conter contexto ou instrucao de prompt, o
lote tenta traduzir novamente e sobrescrever o cache. O status final mostra
processados, traduzidos, cache hits, erros, tempo total e media por traducao
real.

### Patch de traducao MV/MZ

A area `Patch de traducao` gera arquivos JSON traduzidos para resolver partes
que o overlay nao substitui bem, como escolhas dentro da UI do jogo. O fluxo
atual usa apenas o catalogo MV/MZ ja importado e traducoes existentes no cache;
ele nao chama Ollama durante a geracao do patch.

Escopo atual do patch:

- `Map*.json`;
- `CommonEvents.json`;
- `Items.json`;
- `Skills.json`;
- `Weapons.json`;
- `Armors.json`;
- `States.json`;
- `Classes.json`;
- `Enemies.json`;
- `Actors.json`;
- `System.json`;
- `Troops.json`;
- `Scenario.json`;
- mensagens;
- escolhas;
- texto rolante;
- nomes e descricoes de itens;
- nomes e descricoes de skills;
- mensagens de skills;
- nomes e descricoes de armas;
- nomes e descricoes de armaduras;
- nomes e mensagens de estados;
- nomes de classes;
- nomes de inimigos;
- nomes de atores;
- termos de sistema/menu, como comandos `Item` e `Skill`;
- mensagens, escolhas, texto rolante e speakers de batalha;
- mensagens, escolhas, texto rolante e nomes `Tachie showName` em
  `Scenario.json`;
- `speaker`, somente se `Incluir speakers` estiver marcado.

`Gerar patch` cria uma pasta separada em:

```txt
exports/patches/<nome-do-jogo>-ptBR-<timestamp>/data/
```

O patcher substitui textos pela origem exata do catalogo. Em eventos, ele
valida arquivo, evento, pagina, comando e parametro antes de alterar. Em
database, ele valida arquivo, ID do objeto e campo (`name` ou `description`).
Em `System.json`, ele valida o caminho do termo antes de substituir. Mensagens
longas sao quebradas em linhas menores para reduzir o risco de sair da caixa de
texto do jogo. Codigos RPG Maker como `\N[1]`, `\V[2]`, `\C[3]` e `\I[64]`, e
placeholders como `%1`, `%2` e `%3`, precisam ser preservados na traducao; se a
traducao cacheada perder esses codigos, ela e tratada como invalida. Se o texto
original nao bater mais com o JSON do jogo, a entrada e pulada.
Textos sem cache ou com traducao contaminada tambem sao pulados e aparecem no
relatorio:

```txt
live-translator-patch-report.json
live-translator-patch-report.md
```

`Aplicar patch` copia os JSON gerados para `data/` ou `www/data/` do projeto
ativo. Antes de sobrescrever, o app cria backup automatico em:

```txt
backups/patches/<nome-do-jogo>-<timestamp>/data/
```

`Restaurar ultimo backup` restaura o backup mais recente criado pelo app para o
projeto ativo. O app nao apaga patches nem backups automaticamente. Depois de
atualizar o app, reimporte o catalogo antes de gerar um novo patch para incluir
arquivos recem-suportados como `Scenario.json`.

## Known Issues

- Ainda nao existe build empacotado para Windows; o app roda pelo ambiente
  Python local.
- A captura usa coordenadas absolutas da tela. Se o jogo ou monitor mudar de
  posicao, a area precisa ser recalibrada.
- O modo universal ainda depende de OCR/vision. O modo MV/MZ reduz essa
  dependencia, mas textos gerados por plugins custom podem exigir fallback.
- Plugins customizados ainda podem armazenar textos fora dos JSONs padrao e de
  `Scenario.json`.
- Logs persistentes gerais do runtime ainda nao foram implementados; o
  diagnostico principal fica no painel `Status`.
- O modo click-through do overlay ainda nao e configuravel pela UI.

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
