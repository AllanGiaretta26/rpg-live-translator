# Documentação

Este diretório reúne contexto de produto, planos, relatórios e checklists. A documentação ativa fica pequena e navegável; relatórios antigos ficam como histórico.

## Leitura recomendada

| Se você quer... | Leia |
|---|---|
| Instalar, rodar ou configurar o app | [`../README.md`](../README.md) |
| Entender camadas, dependências e falhas | [`../ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Instalar o plugin MV/MZ, diagnosticar ou gerar patch | [`rpg-maker-mvmz.md`](rpg-maker-mvmz.md) |
| Entender o produto e o plano inicial | [`BRIEFING.md`](BRIEFING.md) |
| Ver próximos passos MV/MZ | [`next-steps/mvmz-checklist.md`](next-steps/mvmz-checklist.md) |
| Consultar histórico de versões | [`../CHANGELOG.md`](../CHANGELOG.md) |
| Consultar checkpoints históricos | [`relatorios/`](relatorios/) |
| Consultar auditorias | [`auditorias/`](auditorias/) |

## Documentos ativos

- [`../README.md`](../README.md): guia do usuário, requisitos, instalação, configuração, visão geral dos modos, troubleshooting e links principais.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md): fonte atual para arquitetura, regras de dependência e estratégia de testes.
- [`rpg-maker-mvmz.md`](rpg-maker-mvmz.md): guia completo do modo RPG Maker MV/MZ — instalação do plugin, recuperação após atualização, diagnóstico e patch de tradução.
- [`BRIEFING.md`](BRIEFING.md): briefing de produto e planejamento inicial. Use como contexto, não como contrato técnico quando divergir do código.
- [`next-steps/mvmz-checklist.md`](next-steps/mvmz-checklist.md): backlog/checklist operacional para evolução do modo MV/MZ.

## Histórico

- [`relatorios/`](relatorios/): checkpoints históricos do projeto, padronizados em português brasileiro e nomeados como `relatorio-vNN-*`.
- [`auditorias/`](auditorias/): auditorias técnicas e de documentação, separadas dos relatórios de checkpoint.
- [`superpowers/`](superpowers/): planos e specs gerados durante fluxos assistidos por agentes.

Quando houver divergência, a ordem de autoridade é:

1. código atual e testes;
2. [`../ARCHITECTURE.md`](../ARCHITECTURE.md), para regras técnicas;
3. [`../README.md`](../README.md), para uso do app;
4. documentos históricos em `docs/relatorios/` e `docs/auditorias/`.

## Padrão para novas páginas

- Use um único H1 no início do arquivo.
- Escreva em português brasileiro, com acentos e termos consistentes (`tradução`, `diagnóstico`, `catálogo`, `Próximas sessões`).
- Use títulos em sentence case, não Title Case.
- Inclua uma seção curta de status quando o documento for plano, checklist ou relatório.
- Prefira links relativos para documentos do repositório.
- Ao citar botões, abas ou status da UI, copie o texto exibido no app. Fora de código ou rótulos, use português brasileiro com acentos.
- Não duplique DDL, prompts ou detalhes longos de implementação. Aponte para o arquivo de código que é a fonte da verdade.
- Em relatórios, separe claramente: escopo, achados, ações aplicadas, verificação e pendências.

## Manutenção

Antes de fechar uma mudança de documentação:

1. confira se o `README.md` continua sendo guia de uso, não despejo de arquitetura;
2. confira se `ARCHITECTURE.md` descreve o código atual, não intenção futura;
3. mantenha rótulos da UI como aparecem no app, mesmo quando ainda estiverem sem acento;
4. não misture checkpoints com auditorias; use `docs/relatorios/` para entregas de versão e `docs/auditorias/` para achados/recomendações;
5. rode uma checagem local de links relativos e H1 nos documentos ativos antes de declarar a auditoria concluída.

## Auditorias recentes

- [`auditorias/auditoria-documentacao-2026-06-15.md`](auditorias/auditoria-documentacao-2026-06-15.md): auditoria da documentação, padronização aplicada e pendências.
