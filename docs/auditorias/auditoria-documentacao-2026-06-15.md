# Auditoria de documentação — 2026-06-15

## Escopo

Auditoria feita nos arquivos Markdown do repositório, com foco nos documentos ativos para usuário, arquitetura, contexto de produto e próximos passos.

Arquivos revisados:

- `README.md`
- `ARCHITECTURE.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CHANGELOG.md`
- `docs/BRIEFING.md`
- `docs/next-steps/mvmz-checklist.md`
- inventário de `docs/report/` (agora `docs/relatorios/` e `docs/auditorias/`) e `docs/superpowers/`

Também foram conferidos links relativos, quantidade de H1 nos documentos ativos e aderência da tabela de variáveis do `README.md` aos campos de `AppSettings`.

## Achados

| Achado | Impacto | Ação aplicada |
|---|---|---|
| Referências a `BRIEFING.md` sem o caminho real `docs/BRIEFING.md`. | Leitores e agentes podiam procurar um arquivo inexistente na raiz. | Atualizados `AGENTS.md`, `CLAUDE.md`, `README.md` e o topo do briefing. |
| `ARCHITECTURE.md` tinha dois H1. | Navegação e renderização de índice ficavam inconsistentes. | Consolidado em um único H1 e adicionados links para documentos relacionados. |
| Não havia índice da documentação. | Documentos ativos e históricos ficavam misturados. | Criado `docs/README.md` com mapa, ordem de autoridade e padrão para novas páginas. |
| `README.md` explicava o uso, mas não listava variáveis de ambiente nem troubleshooting em um ponto único. | Configuração avançada exigia ler código ou lembrar nomes de settings. | Reorganizado com sumário, tabela `LIVE_TRANSLATOR_*`, mapa de docs e solução de problemas rápida. |
| Checklist MV/MZ tinha títulos e termos sem acento ou com capitalização inconsistente. | O documento parecia menos cuidado que o restante da documentação em pt-BR. | Padronizados título, seções principais e termos recorrentes. |
| `docs/BRIEFING.md` não deixava claro que é contexto/plano inicial. | Poderia ser lido como fonte técnica atual mesmo quando divergir do código. | Adicionado aviso de status apontando para `ARCHITECTURE.md` e `README.md`. |
| Recuperação do plugin após atualização ou verificação da Steam não estava descrita. | Usuários podiam ficar sem bridge MV/MZ se `plugins.js` fosse sobrescrito. | Adicionada seção de recuperação no `README.md` e checklist MV/MZ atualizado. |
| Tabela de configuração avançada podia ser lida como lista exaustiva de todos os campos de settings. | Campos persistidos pela UI, como overlay, poderiam confundir quem usa `.env`. | Texto ajustado para deixar claro que a tabela cobre o fluxo principal e que ajustes de overlay ficam no SQLite. |
| Sumário do `README.md` não apontava para todas as seções de segundo nível. | Navegação incompleta em renderizadores de Markdown sem índice automático. | Adicionados links para configuração por script, limitações conhecidas e licença. |
| `README.md` dizia que o app não modifica arquivos do jogo, mas também documentava aplicação de patch. | A promessa era ampla demais e contradizia o fluxo de patch MV/MZ. | Reescrito para separar fluxos read-only de ações explícitas de apply/restore com backup. |
| `ARCHITECTURE.md` citava apenas `data/` como pasta MV/MZ. | Inconsistência com detector/importação e com o README, que aceitam `www/data/`. | Atualizado para `data/` ou `www/data/`. |
| `docs/BRIEFING.md` preservava planejamento antigo sem resumir o estado atual. | Leitor podia confundir nomes planejados com implementação real. | Adicionada seção `Estado atual` e aviso de que nomes antigos são histórico, não contrato. |
| Relatórios históricos usavam estilos diferentes (`Report`, `Relatorio`, versões antigas). | Histórico ficava desorganizado no Git e misturava checkpoint com auditoria. | Relatórios movidos para `docs/relatorios/relatorio-vNN-*.md`, auditorias movidas para `docs/auditorias/` e conteúdo padronizado em pt-BR. |

## Padrão adotado

- Um único H1 por documento.
- Títulos em sentence case.
- Português brasileiro com acentos nos documentos ativos.
- Links relativos entre documentos do repositório.
- README como guia de uso; `ARCHITECTURE.md` como fonte técnica; `docs/README.md` como índice e padrão de manutenção.
- Relatórios históricos preservados em conteúdo, mas padronizados em português brasileiro e renomeados com prefixo ordenável `relatorio-vNN-*`.
- Rótulos da UI citados como aparecem no app; prose fora de código em português brasileiro com acentos.

## Pendências recomendadas

- Manter `docs/relatorios/` para checkpoints e `docs/auditorias/` para auditorias; não recriar `docs/report/`.
- Adicionar um checker simples de Markdown ao CI se o projeto passar a aceitar contribuições externas.
- Decidir se `overlay_opacity` e `overlay_font_size` devem ser conectados ao bootstrap como defaults vindos do `.env` ou removidos de `AppSettings`; hoje o overlay é ajustado e persistido pela UI.
- Criar screenshots curtos do fluxo de calibração e do modo MV/MZ quando houver uma build estável.

## Verificação

- Auditoria local de Markdown: arquivos `.md` do repositório conferidos; links relativos quebrados apenas dentro de `.venv/`, fora da documentação do projeto.
- Documentos ativos conferidos com um H1 real por arquivo, ignorando linhas `#` dentro de blocos de código.
- `git diff --check`: passou; o Git só emitiu avisos esperados de normalização LF/CRLF no Windows.
- `.venv\Scripts\python.exe -m pytest`: 259 testes passaram.
