# Changelog

Todas as mudancas relevantes deste projeto serao registradas aqui.

## Unreleased

### Added

- Tema visual escuro coeso na janela principal, com grupos em cartoes
  arredondados, campos e tabela destacados e botoes de acao principal em
  destaque (`Salvar`, `Importar`, `Traduzir`, `Gerar patch`).
- Relatorio V12 com fechamento do suporte inicial a database MV/MZ no catalogo
  e no patch.
- Catalogacao e patch MV/MZ para `Weapons.json`, `Armors.json`, `States.json`,
  `Classes.json`, `Enemies.json` e eventos de batalha em `Troops.json`.
- Catalogacao e patch MV/MZ para cenas custom em `Scenario.json`, incluindo
  mensagens, escolhas, texto rolante e nomes `Tachie showName`.
- Catalogacao MV/MZ de `Items.json` e `Skills.json`, incluindo nomes e
  descricoes, alem de mensagens `message1` e `message2` de skills.
- Catalogacao MV/MZ de `Actors.json` para nomes de personagens.
- Catalogacao de termos de `System.json`, incluindo comandos de menu como
  `Item` e `Skill`.
- Tipos de catalogo `item_name`, `item_description`, `skill_name` e
  `skill_description`.
- Tipos de catalogo `weapon_name`, `weapon_description`, `armor_name`,
  `armor_description`, `state_name`, `state_message`, `class_name`,
  `enemy_name`, `skill_message`, `troop_message`, `troop_choice`,
  `troop_scrolling_text` e `troop_speaker`.
- Tipos de catalogo `actor_name` e `system_term`.
- Exportacao de patch para nomes e descricoes em `Items.json` e `Skills.json`.
- Exportacao de patch para nomes e descricoes de armas e armaduras, nomes e
  mensagens de estados, classes, inimigos, mensagens de skills e eventos de
  batalha.
- Exportacao de patch para nomes em `Actors.json` e termos em `System.json`.
- Escopo de cache de traducao por projeto RPG Maker MV/MZ, mantendo cache global
  para o modo Universal/OCR.
- Migracao SQLite idempotente para armazenar origem de database no catalogo
  existente e escopo na tabela `translations`.
- Relatorio V11 com fechamento do exportador/aplicador de patch JSON MV/MZ.
- Area `Patch de traducao` no modo RPG Maker MV/MZ para gerar patch, aplicar
  patch e restaurar o ultimo backup.
- Exportacao de patch traduzido para `Map*.json` e `CommonEvents.json`, usando
  traducoes ja cacheadas.
- Backup automatico dos JSON originais antes de aplicar um patch MV/MZ.
- Relatorio V10 com fechamento da separacao visual entre modo Universal e
  RPG Maker MV/MZ.
- Helper testavel para decidir quais controles da janela principal ficam ativos
  em cada modo.
- Relatorio V9 com fechamento de paginacao do catalogo, busca por ID e
  retraducao forcada.
- Navegacao do catalogo MV/MZ em paginas de 500 entradas.
- Busca de entrada do catalogo MV/MZ por ID persistido no banco.
- Acao `Retraduzir ID` para apagar cache antigo, chamar Ollama novamente e
  salvar a nova traducao.
- Relatorio V8 com fechamento dos controles avancados de traducao em lote MV/MZ.
- Filtro de traducao em lote MV/MZ por `message`, `choice`, `speaker` e
  `scrolling_text`.
- Controles para pausar e retomar o lote MV/MZ sem perder progresso na sessao
  atual.
- Status final do lote MV/MZ com tempo total e media por traducao real.
- Relatorio V7 com fechamento dos controles de cache, erros de lote e
  diagnostico MV/MZ.
- Botao `Limpar cache contaminado` para remover traducoes invalidas do cache do
  catalogo MV/MZ ativo.
- Botao `Reprocessar fala atual` para apagar o cache da ultima fala MV/MZ e
  forcar nova traducao.
- Persistencia dos erros do ultimo lote em `rpg_maker_batch_errors`, com
  `entry_id`, origem, texto fonte e mensagem do erro.
- Botao `Ver erros do ultimo lote` para consultar falhas de traducao em lote.
- Contagem de entradas do catalogo MV/MZ que ja possuem traducao cacheada.
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

- Patch MV/MZ agora reequilibra quebras de fala vindas do cache e quebra
  descricoes de itens, skills, armas e armaduras para caberem na janela de
  ajuda/batalha.
- Traducoes em lote de descricoes MV/MZ agora aceitam ate duas linhas curtas e
  usam prompt compacto de UI, evitando conflito com instrucao de nao resumir.
- Patch MV/MZ agora evita deixar inicio de frase ou conectivo curto pendurado no
  fim de linhas de dialogo.
- Lote MV/MZ agora repara prefixos visuais simples como `\{` quando o modelo
  traduz a fala mas perde o codigo, e usa tentativa compacta extra para
  descricoes longas.
- Aviso de overlay sobre area capturada agora fica oculto no modo RPG Maker
  MV/MZ, onde a captura/OCR esta desativada.
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

- Janela principal reformulada visualmente: campos com largura natural alinhados
  a esquerda, conteudo fixado ao topo e preview/tabela ocupando o espaco livre,
  eliminando os campos esticados e os grandes vazios verticais.
- Filtros de tipo do lote MV/MZ agora ficam agrupados por categoria (mensagens e
  eventos, database e batalha) em grade, sem cortar os nomes, e a aba
  `RPG Maker MV/MZ` passou a usar area rolavel.
- Lote MV/MZ agora inclui itens e skills por padrao, mantendo `speaker`
  desativado por padrao.
- Lote MV/MZ agora inclui database expandido, nomes de atores, termos do sistema
  e eventos de batalha por padrao.
- Patch MV/MZ agora valida tambem ID e campo de database antes de substituir
  campos como `name`, `description`, `message1` e `message2`.
- Patch MV/MZ agora quebra mensagens longas em linhas menores ao gerar
  `Map*.json` e `CommonEvents.json`.
- Tradutor/cache agora tratam como invalida a traducao que remove codigos RPG
  Maker como `\N[1]`, `\V[2]`, `\C[3]`, `\I[64]` ou placeholders como `%1` e
  `%2`.
- Prompts de traducao agora mudam conforme tipo de texto: dialogo, nome,
  descricao, termo de sistema ou mensagem de batalha.
- Patch MV/MZ pula entradas sem cache, traducoes contaminadas e origens que nao
  batem mais com o JSON original, registrando tudo no relatorio do patch.
- Janela principal reorganizada em fluxos mais claros: `Universal`,
  `RPG Maker MV/MZ`, `Overlay` e `Executar`.
- Controles de captura/OCR agora ficam desativados no modo RPG Maker MV/MZ.
- Controles de catalogo, lote, cache e erros MV/MZ agora ficam desativados
  enquanto o modo Universal esta ativo.
- Consulta do catalogo MV/MZ agora usa paginacao SQLite com `LIMIT`/`OFFSET`,
  evitando carregar o catalogo inteiro para exibir a tabela.
- Botao `Reprocessar fala atual` agora usa retraducao forcada explicita:
  remove cache antigo, ignora cache existente, chama Ollama e salva a nova
  traducao.
- Lote MV/MZ agora deixa `speaker` desativado por padrao para evitar traduzir
  nomes proprios.
- Lote MV/MZ agora valida cache existente antes de contar como cache hit; cache
  contaminado e retraduzido e sobrescrito.
- Lotes MV/MZ agora limpam os erros anteriores ao iniciar e mantem os erros do
  ultimo lote para diagnostico.
- README documenta os novos controles de cache contaminado, reprocessamento e
  consulta de erros do modo MV/MZ.
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
