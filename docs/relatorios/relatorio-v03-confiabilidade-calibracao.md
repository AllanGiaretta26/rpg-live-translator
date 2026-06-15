# Relatório V03 — Confiabilidade da calibração

## Resumo

Este checkpoint melhora a confiabilidade da calibração. O overlay passa a ser tratado apenas como saída traduzida, a região de texto-fonte fica mais fácil de selecionar e o app avisa quando a posição do overlay pode contaminar o OCR.

## Entregas

- Adicionada detecção de sobreposição entre a região de texto e a posição do overlay.
- Adicionado aviso no app quando o overlay intersecta a área capturada.
- Melhorado o redimensionamento do overlay pelas bordas e cantos.
- Corrigida a escolha da tela no seletor de região usando o monitor sob o cursor.
- Reforçados prompts de tradução e validação de resultado vazio.
- Adicionados diagnósticos mais claros para falha de tradução.

## Validação

- Testes automatizados: `.venv\Scripts\python.exe -m pytest` passou com 68 testes.
- Varredura de imports de arquitetura: nenhum import sensível encontrado em `domain` ou `application`.
- Validações manuais ainda necessárias: seleção de região, preview de captura, redimensionamento do overlay, aviso de sobreposição e tradução de diálogos multilinha contra jogo real.

## Pendências e riscos

- Completude da tradução ainda depende da qualidade do OCR e do comportamento do modelo.
- Captura relativa à janela continua sendo melhoria futura.
- Validação manual da GUI ainda é obrigatória no monitor/jogo alvo.
- Empacotamento e logging de produção continuam pendentes.
