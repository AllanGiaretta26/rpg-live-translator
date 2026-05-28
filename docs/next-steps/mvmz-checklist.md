# Proximas Sessoes: Checklist MV/MZ

## Estabilizacao do modo MV/MZ

- [ ] Ocultar ou reescrever o aviso de overlay sobre area capturada quando o modo ativo for `RPG Maker MV/MZ`.
- [x] Confirmar em teste manual que `Fonte MV/MZ` sempre corresponde ao texto visivel no jogo.
- [x] Confirmar em teste manual que `Traducao MV/MZ` nao reaproveita cache contaminado.
- [ ] ~~Validar falas com uma linha, multiplas linhas,~~ escolhas e texto rolante.
- [x] Testar avanco rapido de dialogos para confirmar que traducoes antigas nao sobrescrevem falas novas.

## Cache e diagnostico

- [ ] Adicionar limpeza manual de traducoes contaminadas no cache.
- [ ] Adicionar acao para reprocessar a fala atual quando o cache for invalido.
- [ ] Persistir erros de traducao em lote com `entry_id`, origem, texto fonte e mensagem do erro.
- [ ] Adicionar botao ou aba para consultar os erros do ultimo lote.
- [ ] Mostrar contagem de entradas do catalogo com traducao ja cacheada.

## Traducao em lote

- [ ] Adicionar filtro de lote por tipo de texto: `message`, `choice`, `speaker`, `scrolling_text`.
- [ ] Definir se `speaker` deve entrar no lote por padrao ou ficar desativado.
- [ ] Adicionar pausa/resumo do lote sem perder progresso.
- [ ] Evitar retraduzir entradas cujo cache foi validado como bom.
- [ ] Melhorar status final do lote com tempo total e media por traducao.

## Plugin MV/MZ

- [ ] Testar compatibilidade do `LiveTranslatorBridge.js` em jogos MV e MZ diferentes.
- [x] Verificar comportamento com jogos Steam sem acesso ao Plugin Manager.
- [ ] Criar instalador/registrador de plugin para copiar o arquivo e atualizar `plugins.js` com backup.
- [ ] Adicionar desinstalador/restaurador do plugin usando o backup.
- [ ] Documentar recuperacao caso update da Steam sobrescreva `plugins.js`.

## UX do modo RPG Maker

- [ ] Separar melhor na UI o modo Universal do modo MV/MZ.
- [ ] Desativar controles de captura quando o modo MV/MZ estiver ativo.
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
