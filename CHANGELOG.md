# Changelog

Todas as mudanças relevantes deste projeto serão registradas aqui.

## Unreleased

### Added

- Índice de documentação em `docs/README.md`, separando documentos ativos, histórico e padrão para novas páginas.
- Auditoria de documentação em `docs/auditorias/auditoria-documentacao-2026-06-15.md`.
- Relatórios históricos movidos de `docs/report/report-v*.md` para `docs/relatorios/relatorio-vNN-*.md`, com títulos e conteúdo padronizados em português brasileiro.
- Auditorias movidas para `docs/auditorias/`, separando achados técnicos de checkpoints de versão.

### Changed

- `README.md` reorganizado com sumário, tabela de variáveis `LIVE_TRANSLATOR_*`, mapa da documentação e troubleshooting rápido.
- `ARCHITECTURE.md`, `docs/BRIEFING.md`, `AGENTS.md`, `CLAUDE.md` e o checklist MV/MZ padronizados para apontar aos documentos atuais e usar português consistente.
- `README.md` agora documenta a recuperação do plugin MV/MZ quando uma atualização ou verificação da Steam sobrescreve `plugins.js`.
- Documentação do modo MV/MZ ajustada para separar fluxos read-only de ações explícitas de patch com backup, e para citar `data/` e `www/data/` de forma consistente.

## [0.6.0] - 2026-06-12

### Added

- Contexto de dialogo na traducao em lote MV/MZ: ate `batch_context_lines`
  falas anteriores do mesmo bloco evento/pagina sao enviadas como contexto
  (default 4, env `LIVE_TRANSLATOR_RPG_MAKER_BATCH_CONTEXT_LINES`, 0 desativa).
  O contexto e montado sobre o catalogo completo (lotes filtrados, ex. so
  choices, ainda recebem as messages vizinhas), nunca cruza eventos/paginas e
  so falas corridas o alimentam. Traducao individual por ID segue sem contexto.
- Metrica de descartes do `translation_quality` no status do lote:
  `invalid_translation_reason` nomeia a regra que rejeitou e o resultado do
  lote expoe `rejected_by_rule` (exibido na UI como "cache descartado por
  regra: ...").
- Corpus de regressao de qualidade de traducao
  (`tests/data/translation_regression_corpus.json`): pares fonte/traducao no
  formato real do jogo validam mudancas de prompt e heuristicas sem rodar o
  jogo — pares bons nao podem virar falso positivo e pares ruins precisam cair
  na regra esperada.

### Changed

- Prompt principal de traducao reestruturado: diretrizes de estilo
  (naturalidade, tom da cena, siglas HP/MP/TP/EXP preservadas) e texto a
  traduzir movido para o fim do prompt; frases distintivas das diretrizes
  entraram nos marcadores de vazamento de prompt.
- Prompt de visao agora e OCR-only: transcreve o texto da imagem sem traduzir
  (a traducao ja era feita em chamada separada), melhorando a fidelidade da
  transcricao no modo universal.
- `OllamaClient.generate()` envia `options.temperature = 0` (traducoes
  deterministicas) e `keep_alive` (default 15m) para manter o modelo carregado
  entre frames; `is_available()` usa timeout dedicado de 2s em vez do timeout
  cheio de requisicao.

## [0.5.0] - 2026-06-10

### Added

- `ARCHITECTURE.md` reescrita do zero, fiel ao codigo real: regras de
  dependencia verificaveis, mapa de tratamento de falhas e prioridades de
  teste (`app/bootstrap.py` como fonte da verdade).
- Guard-rails de arquitetura automatizados em
  `tests/unit/test_architecture_rules.py`: pureza do Domain, proibicao de
  infraestrutura importar Application/UI e imports desktop (`PySide6`/`mss`)
  apenas lazy fora de `ui/` e `infrastructure/capture/`.
- Teste de bootstrap headless (`tests/unit/app/test_bootstrap_headless.py`)
  garantindo os fallbacks `ConsoleOverlay`/`ConsoleUiApp` sem GUI instalada.
- Auditoria completa do projeto em `docs/auditorias/auditoria-projeto-2026-06-10.md`, com
  mapa de interdependencias e ordem de execucao das correcoes.
- Novo erro `OllamaModelNotFoundError` distinguindo "modelo nao instalado"
  (HTTP 404, com instrucao de `ollama pull`) de "Ollama fora do ar".

### Changed

- `translation_quality` movido de `application/` para `domain/`, eliminando a
  violacao de camada em que a infraestrutura importava Application.
- Lote de traducao do catalogo e export de patch MV/MZ agora usam uma unica
  consulta em lote (`get_many_by_text`) em vez de uma consulta SQLite por
  entrada, preservando o reaproveitamento de textos duplicados do catalogo.
- Scope de cache MV/MZ agora e memoizado por caminho de projeto: o bridge nao
  refaz deteccao de projeto no disco a cada fala; o cache e invalidado ao
  trocar o caminho do projeto e falhas de deteccao nao sao memoizadas.
- Prompts de traducao deduplicados (blocos "Preserve exatamente..."
  compartilhados); o prompt de retry passou a listar os codigos RPG Maker
  completos; o idioma destino respeita `target_language` em vez de
  "portugues brasileiro" fixo; o limite de caracteres da descricao compacta e
  derivado dos limites de validacao do dominio.
- Heuristica de texto nao-jogo unificada em
  `domain/translation_quality.looks_like_non_game_text`, usada pelo pipeline
  universal e pelo extrator de visao (que agora tambem descarta texto do
  proprio overlay).

### Fixed

- Modo universal agora valida hits de cache (imagem e texto) com
  `looks_like_invalid_translation`: traducao contaminada antiga vira cache
  miss e e retraduzida, em vez de aparecer no overlay para sempre e se
  propagar para o cache de imagem.
- `OllamaTranslator` agora aciona o prompt de retry tambem quando o modelo
  devolve JSON invalido (antes abortava o loop) e rejeita traducoes com
  marcadores de mascara `__LT_RPG_TOKEN` residuais ou mutilados.
- `OllamaClient` classifica `HTTPError` antes de `URLError` (um 404 nao vira
  mais "Ollama is unavailable") e timeout embrulhado em
  `URLError(reason=TimeoutError)` vira `OllamaTimeoutError`.
- Runtime MV/MZ degrada com diagnostico "projeto MV/MZ inacessivel" quando o
  caminho do projeto fica invalido (jogo movido/atualizado), em vez de
  responder HTTP 500 a cada fala do plugin.

### Removed

- `domain/errors.py` (exceções sem nenhum uso) e a tabela `glossary` sem uso
  do schema SQLite (bancos existentes nao sao alterados).

## [0.4.0] - 2026-06-07

### Added

- Relatório V14 com a auditoria de otimizacao e tratamento de bugs (persistencia
  SQLite, contagem de cache, validacao de traducao e bridge runtime).
- Relatório V15 com as correcoes de quebra de linha, overflow e codigos de escape
  na geracao de patch MV/MZ.
- Limites de largura do patch MV/MZ configuraveis por settings/ambiente
  (`LIVE_TRANSLATOR_PATCH_MESSAGE_LINE_LIMIT`,
  `LIVE_TRANSLATOR_PATCH_MESSAGE_FACE_LINE_LIMIT`,
  `LIVE_TRANSLATOR_PATCH_DESCRIPTION_LINE_LIMIT`), ja que a caixa de texto varia
  por jogo/tema.

### Changed

- `SQLiteConnectionManager` agora inicializa schema e migracoes apenas uma vez por
  instancia, em vez de re-executar todo o `SCHEMA_SQL` e a introspeccao de
  migracao a cada conexao aberta, reduzindo o custo de cada acesso ao banco.
- Contagem e limpeza de cache do catalogo MV/MZ agora usam uma unica consulta em
  lote (`get_many_by_text`) no lugar de uma consulta por entrada, acelerando
  catalogos grandes.
- Importacao do catalogo MV/MZ (`replace_project_entries`) agora grava as entradas
  com `executemany` em vez de um `INSERT` por entrada.
- O patch MV/MZ agora quebra mensagens preenchendo a largura (reflui a fala), sem
  pular linha apos virgula/ponto, mantendo falas longas divididas em varias linhas
  para nao sair da tela.

### Fixed

- A contagem `Cache: X/Y entradas ja traduzidas` deixou de incluir traducoes
  contaminadas; agora conta apenas traducoes validas, alinhando o numero ao que o
  lote e a limpeza de cache consideram hit real.
- A validacao de traducao deixou de rejeitar por engano traducoes validas que
  quebram uma linha de origem em varias linhas, ao detectar marcadores visuais
  inesperados (`€`, `¥`, `￥`) apenas em linhas com origem correspondente.
- A bridge runtime MV/MZ agora limita o tamanho do corpo das requisicoes (responde
  `413` quando excede o limite e `400` para `Content-Length` invalido) e separa
  erro de cliente (`400`) de erro interno de processamento (`500`).
- Patch MV/MZ nao duplica mais codigos de fonte (`\{`/`\}`) nas linhas quebradas,
  que faziam a fonte crescer e a fala sair da caixa; apenas o marcador `\#` e
  repetido por linha.
- Patch MV/MZ agora mede a largura da linha de forma ciente de codigos de escape:
  codigos de largura zero (`\C[n]`, `\I[n]`, `\{`, espera) nao contam e codigos
  dinamicos (`\N`, `\P`, `\V`) usam estimativa conservadora, evitando overflow.

## [0.3.0] - 2026-06-03

### Added

- Tema visual escuro coeso na janela principal, com grupos em cartoes
  arredondados, campos e tabela destacados e botoes de acao principal em
  destaque (`Salvar`, `Importar`, `Traduzir`, `Gerar patch`).
- Relatório V12 com fechamento do suporte inicial a database MV/MZ no catalogo
  e no patch.
- Relatório V13 com fechamento das correcoes de qualidade para lote/cache e
  quebra visual do patch MV/MZ.
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
- Relatório V11 com fechamento do exportador/aplicador de patch JSON MV/MZ.
- Area `Patch de traducao` no modo RPG Maker MV/MZ para gerar patch, aplicar
  patch e restaurar o ultimo backup.
- Exportacao de patch traduzido para `Map*.json` e `CommonEvents.json`, usando
  traducoes ja cacheadas.
- Backup automatico dos JSON originais antes de aplicar um patch MV/MZ.
- Relatório V10 com fechamento da separacao visual entre modo Universal e
  RPG Maker MV/MZ.
- Helper testavel para decidir quais controles da janela principal ficam ativos
  em cada modo.
- Relatório V9 com fechamento de paginacao do catalogo, busca por ID e
  retraducao forcada.
- Navegacao do catalogo MV/MZ em paginas de 500 entradas.
- Busca de entrada do catalogo MV/MZ por ID persistido no banco.
- Acao `Retraduzir ID` para apagar cache antigo, chamar Ollama novamente e
  salvar a nova traducao.
- Relatório V8 com fechamento dos controles avancados de traducao em lote MV/MZ.
- Filtro de traducao em lote MV/MZ por `message`, `choice`, `speaker` e
  `scrolling_text`.
- Controles para pausar e retomar o lote MV/MZ sem perder progresso na sessao
  atual.
- Status final do lote MV/MZ com tempo total e media por traducao real.
- Relatório V7 com fechamento dos controles de cache, erros de lote e
  diagnostico MV/MZ.
- Botao `Limpar cache contaminado` para remover traducoes invalidas do cache do
  catalogo MV/MZ ativo.
- Botao `Reprocessar fala atual` para apagar o cache da ultima fala MV/MZ e
  forcar nova traducao.
- Persistencia dos erros do ultimo lote em `rpg_maker_batch_errors`, com
  `entry_id`, origem, texto fonte e mensagem do erro.
- Botao `Ver erros do ultimo lote` para consultar falhas de traducao em lote.
- Contagem de entradas do catalogo MV/MZ que ja possuem traducao cacheada.
- Relatório V6 com fechamento parcial da evolucao MV/MZ, diagnosticos e riscos
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
- Reparo de prefixos visuais do lote MV/MZ agora funciona por linha e o prompt
  compacto de descricoes passou a limitar tamanho total.
- Lote MV/MZ agora mascara codigos RPG Maker e placeholders antes de chamar o
  modelo, restaurando os valores originais depois da traducao.
- Lote MV/MZ agora trata textos so de pontuacao/controle, como `...`, como
  passthrough e rejeita caches que expandem esse texto para falas inventadas.
- Patch MV/MZ agora preserva prefixos visuais simples como `\#` em cada linha
  criada pela quebra automatica.
- Validacao MV/MZ agora rejeita traducoes que adicionam marcadores visuais
  inesperados como `€`, `¥` ou `￥` no inicio da fala.
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
- Relatório V5 sobre fechamento do MVP e proxima evolucao RPG Maker MV/MZ.
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
