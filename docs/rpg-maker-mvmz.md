# Modo RPG Maker MV/MZ

Guia completo do modo `RPG Maker MV/MZ`: instalação do plugin runtime,
recuperação após atualizações, diagnóstico em tempo real e geração/aplicação
do patch de tradução. Para visão geral do app, instalação e configuração, veja
[`../README.md`](../README.md).

## Visão geral

O app não modifica arquivos do jogo durante importação, tradução em lote ou
runtime. O suporte MV/MZ tem três partes:

- importação read-only dos JSONs em `www/data/` ou `data/`;
- plugin runtime opcional para enviar falas atuais ao app sem OCR;
- geração/aplicação explícita de patch traduzido, com backup antes de
  sobrescrever JSONs do jogo.

Arquivos importados:

- `Map*.json` e `CommonEvents.json`;
- `Items.json`, `Skills.json`, `Weapons.json`, `Armors.json`, `States.json`,
  `Classes.json`, `Enemies.json`, `Actors.json`, `System.json`, `Troops.json` e
  `Scenario.json`, quando presentes.

Textos extraídos: mensagens, escolhas, texto rolante, nomes e descrições de
itens, skills, armas, armaduras, estados, classes, inimigos, atores, termos de
sistema/menu, eventos de batalha e cenas custom.

Traduções geradas ficam no cache `translations`, isoladas pelo caminho do
projeto ativo.

## Instalar `LiveTranslatorBridge.js`

O plugin runtime é opcional, mas é o caminho recomendado no modo MV/MZ: ele
envia a fala renderizada pelo jogo direto para o app, sem OCR. O arquivo fica
em:

```text
src/live_translator/infrastructure/rpgmaker/plugin/LiveTranslatorBridge.js
```

### Instalação pelo editor RPG Maker

1. Feche o jogo antes de alterar arquivos.
2. Copie `LiveTranslatorBridge.js` para a pasta de plugins do jogo
   (`js/plugins/` ou `www/js/plugins/`).
3. Mantenha o nome do arquivo exatamente como `LiveTranslatorBridge.js`.
4. Abra o projeto no RPG Maker.
5. Acesse `Tools` > `Plugin Manager`.
6. Crie uma nova entrada, escolha `LiveTranslatorBridge` e deixe `Status` como
   `ON`.
7. Confirme o parâmetro `Endpoint`: o padrão deve ser
   `http://127.0.0.1:8765/rpgmaker/text`.
8. Salve o projeto.
9. Rode o app, escolha `RPG Maker MV/MZ`, importe o catálogo e inicie o jogo.

### Instalação manual

Útil para jogo distribuído ou Steam sem acesso ao Plugin Manager:

1. Feche o jogo e faça backup de `js/plugins.js` ou `www/js/plugins.js`.
2. Copie `LiveTranslatorBridge.js` para `js/plugins/` ou `www/js/plugins/`,
   conforme a estrutura do jogo.
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

Se você alterou `LIVE_TRANSLATOR_RPG_MAKER_BRIDGE_PORT`, ajuste também o
parâmetro `Endpoint` do plugin para usar a mesma porta.

## Recuperar plugin após atualização ou verificação da Steam

Atualizações do jogo ou a opção `Verify integrity of game files` da Steam
podem sobrescrever `plugins.js`. Quando o modo MV/MZ parar de receber falas
depois de uma atualização:

1. Feche o jogo e o app.
2. Confira se `LiveTranslatorBridge.js` ainda existe em `js/plugins/` ou
   `www/js/plugins/`.
3. Se `plugins.js` foi recriado, restaure o backup feito antes da instalação
   manual ou adicione de novo a entrada `LiveTranslatorBridge` pelo Plugin
   Manager.
4. Confirme se o `Endpoint` continua usando a mesma porta do `.env`, por
   padrão `http://127.0.0.1:8765/rpgmaker/text`.
5. Abra o app em modo `RPG Maker MV/MZ`, inicie o jogo e avance uma fala.
   `Fonte MV/MZ` deve deixar de mostrar `aguardando`.
6. Reimporte o catálogo somente se a atualização também alterou arquivos em
   `data/` ou `www/data/`.

Quando o jogo chama mensagens ou escolhas, o plugin envia o texto para o app.
O app busca no cache, traduz quando necessário e atualiza o overlay sem passar
por captura/OCR.

## Diagnóstico MV/MZ

No modo `RPG Maker MV/MZ`, a aba `Executar` mostra:

- `Fonte MV/MZ`: último texto recebido pela bridge;
- `Traducao MV/MZ`: última tradução aceita pelo runtime;
- `Pipeline`: caminho usado, como `runtime cache texto`, `runtime cache
  inválido` ou `runtime traduzido`;
- `Tempo`: tempo do runtime MV/MZ.

Use esses campos para identificar a origem do problema:

- se `Fonte MV/MZ` já vier errada, o problema está no plugin ou no fluxo do
  jogo;
- se `Fonte MV/MZ` vier limpa e `Traducao MV/MZ` vier contaminada, o problema
  está no modelo ou no cache;
- se `Pipeline` mostrar `runtime cache texto`, a tradução veio do cache
  `translations`;
- se `Pipeline` mostrar `runtime cache inválido`, o cache antigo foi ignorado
  e o app está tentando gerar uma nova tradução;
- se `Pipeline` mostrar `projeto MV/MZ inacessível`, o caminho salvo do
  projeto ficou inválido. Selecione a pasta do jogo novamente na aba `Modo`.

Controles úteis quando aparecer uma tradução ruim:

- `Limpar cache contaminado`: varre o catálogo MV/MZ ativo e remove do cache
  apenas traduções que parecem conter contexto ou instruções de prompt;
- `Reprocessar fala atual`: remove o cache da última `Fonte MV/MZ` recebida e
  traduz novamente;
- `Ver erros do ultimo lote`: abre a lista de falhas salvas do lote mais
  recente, com origem e mensagem de erro;
- `Cache: X/Y entradas ja traduzidas`: mostra quantos textos do catálogo atual
  já possuem tradução válida no cache. Traduções contaminadas não entram na
  contagem.

No lote MV/MZ, cache existente só conta como hit quando a tradução parece
válida. O lote também envia falas anteriores do mesmo evento como contexto
para o modelo, melhorando pronomes, tom e sentido das traduções. O padrão são
4 falas; ajuste com `LIVE_TRANSLATOR_RPG_MAKER_BATCH_CONTEXT_LINES` no `.env`.

Textos que contêm apenas pontuação ou controle, como `...`, são mantidos como
estão e não são enviados ao modelo. Se um cache antigo expandiu esse tipo de
texto para uma fala inventada, `Limpar cache contaminado` remove a entrada e o
próximo lote salva o passthrough correto.

## Patch de tradução MV/MZ

A área `Patch de traducao` gera arquivos JSON traduzidos para resolver partes
que o overlay não substitui bem, como escolhas dentro da UI do jogo. O fluxo
usa apenas o catálogo MV/MZ já importado e as traduções existentes no cache;
ele não chama Ollama durante a geração.

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

O patcher substitui textos pela origem exata do catálogo e valida arquivo,
evento, página, comando e parâmetro antes de alterar. Mensagens longas são
quebradas em linhas menores para reduzir o risco de saírem da caixa de texto
do jogo. Códigos RPG Maker como `\N[1]`, `\V[2]`, `\C[3]` e `\I[64]`, e
placeholders como `%1`, `%2` e `%3`, precisam ser preservados na tradução. Se
a tradução em cache perder esses códigos, ela é tratada como inválida.

Textos sem cache, com tradução contaminada ou com texto original que não bate
mais com o JSON do jogo são pulados e aparecem no relatório:

```text
live-translator-patch-report.json
live-translator-patch-report.md
```

`Aplicar patch` copia os JSON gerados para `data/` ou `www/data/` do projeto
ativo. Antes de sobrescrever, o app cria backup automático em:

```text
backups/patches/<nome-do-jogo>-<timestamp>/data/
```

`Restaurar ultimo backup` restaura o backup mais recente criado pelo app para
o projeto ativo. O app não apaga patches nem backups automaticamente. Depois
de atualizar o app, reimporte o catálogo antes de gerar um novo patch para
incluir arquivos recém-suportados.
