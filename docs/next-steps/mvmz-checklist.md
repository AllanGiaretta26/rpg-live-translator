# Proximas Sessoes: Checklist MV/MZ

## Estabilizacao do modo MV/MZ

- [x] Ocultar ou reescrever o aviso de overlay sobre area capturada quando o modo ativo for `RPG Maker MV/MZ`.
- [x] Confirmar em teste manual que `Fonte MV/MZ` sempre corresponde ao texto visivel no jogo.
- [x] Confirmar em teste manual que `Traducao MV/MZ` nao reaproveita cache contaminado.
- [x] ~~Validar falas com uma linha, multiplas linhas, escolhas e~~ texto rolante.
- [x] Testar avanco rapido de dialogos para confirmar que traducoes antigas nao sobrescrevem falas novas.

## Cache e diagnosticoS

- [x] Adicionar limpeza manual de traducoes contaminadas no cache.
- [x] Adicionar acao para reprocessar a fala atual quando o cache for invalido.
- [x] Persistir erros de traducao em lote com `entry_id`, origem, texto fonte e mensagem do erro.
- [x] Adicionar botao ou aba para consultar os erros do ultimo lote.
- [x] Mostrar contagem de entradas do catalogo com traducao ja cacheada.
- [x] Adicionar busca de entrada do catalogo por ID.
- [x] Adicionar retraducao forcada por ID do catalogo.
- [x] Garantir que `Reprocessar fala atual` substitui cache antigo com nova traducao.

## Traducao em lote

- [x] Adicionar filtro de lote por tipo de texto: `message`, `choice`, `speaker`, `scrolling_text`.
- [x] Definir se `speaker` deve entrar no lote por padrao ou ficar desativado.
- [x] Adicionar pausa/resumo do lote sem perder progresso.
- [x] Evitar retraduzir entradas cujo cache foi validado como bom.
- [x] Melhorar status final do lote com tempo total e media por traducao.
- [x] Paginar visualizacao do catalogo em blocos de 500 entradas.

## Plugin MV/MZ

- [ ] Testar compatibilidade do `LiveTranslatorBridge.js` em jogos MV e MZ diferentes.
- [x] Verificar comportamento com jogos Steam sem acesso ao Plugin Manager.
- [ ] Criar instalador/registrador de plugin para copiar o arquivo e atualizar `plugins.js` com backup.
- [ ] Adicionar desinstalador/restaurador do plugin usando o backup.
- [ ] Documentar recuperacao caso update da Steam sobrescreva `plugins.js`.

## UX do modo RPG Maker

- [x] Separar melhor na UI o modo Universal do modo MV/MZ.
- [x] Desativar controles de captura quando o modo MV/MZ estiver ativo.
- [x] Deixar a interface mais elegante e intuitiva.
- [ ] Destacar endpoint da bridge e estado do servidor local.
- [ ] Adicionar botao para copiar o endpoint da bridge.
- [ ] Adicionar status de plugin conectado/ultima requisicao recebida.

## Futuro sem overlay

- [ ] Planejar substituicao runtime de texto dentro da janela do jogo usando cache.
- [ ] Definir fallback quando a traducao ainda nao estiver pronta.
- [ ] Avaliar exportacao de patch traduzido para pasta separada, sem sobrescrever o jogo original.
- [ ] Documentar riscos de patch em jogos com plugins customizados.

## Validacao antes de merge

- [x] Rodar `.venv\Scripts\python.exe -m ruff check .`.
- [x] Rodar `.venv\Scripts\python.exe -m pytest`.
- [x] Testar manualmente o modo Universal para garantir que OCR/captura nao regrediu.
- [x] Testar manualmente o modo MV/MZ com plugin atualizado.
- [x] Atualizar README, CHANGELOG e relatorio da fase antes do commit final.
