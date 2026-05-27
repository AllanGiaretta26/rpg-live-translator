# BRIEFING.md — RPG Live Translator

## 1. Visão geral

**Nome provisório:** RPG Live Translator

O projeto consiste em um software desktop em Python para traduzir jogos feitos em RPG Maker em tempo real, exibindo a tradução em português brasileiro por meio de um overlay sobre o jogo.

A primeira versão deve funcionar sem modificar os arquivos do jogo. A evolução natural do projeto é suportar extração direta de textos de jogos RPG Maker MV/MZ/VX/VX Ace para melhorar velocidade, precisão e consistência.

---

## 2. Objetivo do projeto

Criar uma aplicação desktop capaz de:

1. capturar uma região da tela onde aparece o texto do jogo;
2. extrair o texto usando OCR/vision;
3. traduzir o texto para PT-BR usando modelo local;
4. exibir a tradução em overlay;
5. cachear traduções para reduzir latência;
6. evoluir para suporte específico a arquivos RPG Maker.

---

## 3. Problema que resolve

Jogos de RPG Maker frequentemente não possuem tradução oficial. Traduzir manualmente os arquivos pode exigir conhecimento técnico, quebrar scripts ou demandar muito tempo.

O projeto cria uma camada externa de tradução em tempo real:

```txt
Jogo rodando → Captura de texto → Tradução → Overlay em PT-BR
```

O MVP evita alterar arquivos do jogo e foca em entregar valor rapidamente.

---

## 4. Público-alvo

### Primário

Jogadores que querem jogar RPGs não traduzidos.

### Secundário

Tradutores, modders e criadores de patches que querem extrair, validar ou acelerar traduções de jogos RPG Maker.

---

## 5. Plataforma alvo

### Inicial

**Windows 10/11**

Motivos:

- maior compatibilidade com jogos RPG Maker;
- melhor suporte a captura de janela;
- mais opções para overlay;
- integração mais madura com `pywin32`;
- maior probabilidade de uso real pelo público-alvo.

### Futuro

Linux pode ser suportado posteriormente, mas não deve guiar as decisões do MVP.

---

## 6. Estratégia técnica

A melhor estratégia é híbrida:

```txt
1. Captura direta de texto quando possível
2. OCR/vision quando necessário
3. Cache agressivo
4. Tradução contextual
5. Overlay configurável
```

Para acelerar o desenvolvimento inicial, o MVP deve seguir este fluxo:

```txt
Captura de região da tela
→ OCR/vision com gemma4:e4b
→ tradução
→ overlay
```

Depois, o projeto pode evoluir para:

```txt
OCR dedicado → correção por LLM → tradução por LLM → overlay
```

E, em uma fase mais avançada:

```txt
Leitura dos arquivos RPG Maker → pré-cache de traduções → OCR apenas como fallback
```

---

## 7. Stack recomendada

### Linguagem

```txt
Python 3.13
```

Motivo: boa compatibilidade com bibliotecas desktop, captura de tela, OpenCV, PySide6 e empacotamento.

---

### Gerenciador de projeto

```txt
uv
```

Motivo: simplifica criação de ambiente, instalação de dependências e execução do projeto.

Comandos iniciais sugeridos:

```bash
uv init rpg-live-translator
uv add pyside6 mss pillow opencv-python pydantic pydantic-settings requests platformdirs pywin32 pygetwindow imagehash
```

---

### Interface desktop

```txt
PySide6
```

**Problema que resolve:** criação de UI desktop, overlay transparente, janelas de configuração e tray icon.

**Quando usar:** aplicação desktop real com interface, atalhos, overlay e configurações.

**Quando evitar:** scripts pequenos ou protótipos puramente CLI.

---

### Captura de tela

```txt
mss
```

**Problema que resolve:** captura rápida de regiões da tela.

**Quando usar:** captura contínua ou quase contínua de uma área do jogo.

**Quando evitar:** quando for necessário capturar textura interna via APIs gráficas mais avançadas.

---

### Integração Windows

```txt
pywin32
pygetwindow
keyboard
```

Uso:

- detectar janela ativa;
- obter posição e tamanho da janela do jogo;
- criar atalhos globais;
- manter overlay acima do jogo.

---

### Processamento de imagem

```txt
Pillow
OpenCV
imagehash
```

Uso:

- recortar região da tela;
- pré-processar imagem;
- aumentar contraste;
- detectar mudança visual;
- evitar processar frames repetidos.

---

### OCR / Vision / Tradução

```txt
gemma4:e4b via Ollama
```

No MVP, o modelo pode fazer duas tarefas ao mesmo tempo:

```txt
Imagem → texto original + tradução
```

Na arquitetura final, a extração e a tradução devem continuar separadas por interfaces, mesmo que a primeira implementação use o mesmo modelo para ambas.

---

### Banco local

```txt
SQLite
```

**Problema que resolve:** persistência local de cache, histórico, glossário, perfis e configurações.

**Quando usar:** aplicação local single-user.

**Quando evitar:** sincronização multiusuário, uso distribuído ou backend remoto.

---

## 8. Arquitetura recomendada

A arquitetura ideal é um **monólito modular desktop**, com separação leve em camadas:

```txt
UI
Application
Domain
Infrastructure
```

Não usar microsserviços, backend web ou arquitetura distribuída no início.

---

## 9. Visão arquitetural

```txt
┌────────────────────────────┐
│        PySide6 UI           │
│  Settings / Overlay / Tray  │
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│    Application Services     │
│ TranslationPipelineService  │
│ CaptureLoopService          │
│ OverlayService              │
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│           Domain            │
│ TextRegion                  │
│ TranslationResult           │
│ GameProfile                 │
│ GlossaryTerm                │
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│       Infrastructure        │
│ MSSScreenCapture            │
│ OllamaVisionTranslator      │
│ SQLiteTranslationCache      │
│ Win32WindowDetector         │
└────────────────────────────┘
```

---

## 10. Por que essa arquitetura

### Problema que resolve

Evita misturar captura, OCR, tradução, banco, overlay e UI na mesma classe.

Sem separação, o projeto tende a virar um bloco difícil de testar e evoluir.

### Quando usar

Essa arquitetura é adequada porque o projeto envolve:

- captura de tela;
- processamento de imagem;
- chamada a modelo local;
- cache;
- overlay;
- configuração do usuário;
- suporte futuro a múltiplas versões do RPG Maker.

### Quando evitar exagero

Não aplicar Clean Architecture de forma rígida demais. Evitar excesso de DTOs, casos de uso pequenos e abstrações sem necessidade.

Regra prática:

```txt
Crie abstração onde você realmente pretende trocar implementação.
```

---

## 11. Estrutura de pastas

```txt
rpg_live_translator/
  app/
    main.py
    bootstrap.py

  ui/
    main_window.py
    overlay_window.py
    settings_window.py
    tray_icon.py

  application/
    capture_loop_service.py
    translation_pipeline_service.py
    region_selection_service.py
    hotkey_service.py

  domain/
    models.py
    interfaces.py
    errors.py

  infrastructure/
    capture/
      mss_screen_capture.py
      win32_window_detector.py

    image/
      image_preprocessor.py
      image_change_detector.py

    translation/
      ollama_vision_translator.py
      prompt_builder.py

    persistence/
      sqlite_connection.py
      translation_cache_repository.py
      glossary_repository.py
      settings_repository.py

    rpgmaker/
      game_detector.py
      mv_mz_reader.py
      vx_ace_reader.py

  config/
    settings.py
    defaults.py

  tests/
    unit/
    integration/

  pyproject.toml
  README.md
```

---

## 12. Modelo de domínio inicial

```python
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TextRegion:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class ExtractedText:
    text: str
    confidence: Optional[float] = None


@dataclass(frozen=True)
class TranslationResult:
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str = "pt-BR"


@dataclass(frozen=True)
class GameProfile:
    name: str
    window_title: str
    text_region: TextRegion
```

Usar `dataclass(frozen=True)` para evitar mutações acidentais e facilitar testes.

---

## 13. Interfaces principais

```python
from typing import Protocol
from PIL import Image

from .models import ExtractedText, TranslationResult, TextRegion


class ScreenCapture(Protocol):
    def capture_region(self, region: TextRegion) -> Image.Image:
        ...


class TextExtractor(Protocol):
    def extract(self, image: Image.Image) -> ExtractedText:
        ...


class Translator(Protocol):
    def translate(self, text: str, context: list[str]) -> TranslationResult:
        ...


class TranslationCache(Protocol):
    def get(self, source_text: str) -> TranslationResult | None:
        ...

    def save(self, result: TranslationResult) -> None:
        ...


class OverlayRenderer(Protocol):
    def show_text(self, text: str) -> None:
        ...

    def hide(self) -> None:
        ...
```

Essas interfaces permitem que agentes como Codex ou Claude Code implementem módulos isolados sem acoplar o projeto inteiro.

---

## 14. Pipeline principal

Fluxo esperado:

```txt
Capturar região
↓
Verificar se imagem mudou
↓
Extrair texto
↓
Normalizar texto
↓
Consultar cache
↓
Traduzir se necessário
↓
Salvar cache
↓
Renderizar overlay
```

Exemplo conceitual:

```python
class TranslationPipelineService:
    def __init__(
        self,
        text_extractor,
        translator,
        cache,
        overlay,
        change_detector,
    ):
        self.text_extractor = text_extractor
        self.translator = translator
        self.cache = cache
        self.overlay = overlay
        self.change_detector = change_detector
        self.context: list[str] = []

    def process_frame(self, image):
        if not self.change_detector.has_changed(image):
            return

        extracted = self.text_extractor.extract(image)

        if not extracted.text.strip():
            return

        cached = self.cache.get(extracted.text)
        if cached:
            self.overlay.show_text(cached.translated_text)
            return

        result = self.translator.translate(extracted.text, self.context)
        self.cache.save(result)

        self.context.append(extracted.text)
        self.context = self.context[-5:]

        self.overlay.show_text(result.translated_text)
```

---

## 15. Decisão sobre OCR e tradução

### MVP

No MVP, pode ser feito junto:

```txt
Imagem → gemma4:e4b → texto original + tradução
```

Resposta esperada do modelo:

```json
{
  "source_text": "I have been waiting for you.",
  "translated_text": "Eu estava esperando por você."
}
```

### Arquitetura final

Separar conceitualmente:

```txt
Imagem → TextExtractor → texto original
Texto → Translator → tradução
```

Mesmo que o mesmo adaptador faça tudo no começo, manter interfaces separadas permite trocar a implementação depois.

---

## 16. Integração com Ollama

Módulo sugerido:

```txt
infrastructure/translation/ollama_vision_translator.py
```

Responsabilidades:

- converter imagem para base64;
- chamar API local do Ollama;
- enviar prompt;
- validar JSON de resposta;
- aplicar timeout;
- tratar erros;
- registrar logs relevantes.

Prompt base:

```txt
Você é um sistema de OCR e tradução para jogos RPG.

Tarefa:
1. Leia o texto visível na imagem.
2. Ignore elementos decorativos.
3. Traduza para português brasileiro.
4. Preserve nomes próprios.
5. Não explique.
6. Responda apenas em JSON válido.

Formato:
{
  "source_text": "...",
  "translated_text": "..."
}
```

---

## 17. Cache

### Cache por texto

Primeiro nível:

```txt
source_text → translated_text
```

Bom para falas repetidas.

### Cache por imagem

Segundo nível:

```txt
image_hash → source_text → translated_text
```

Bom quando o OCR oscila ou quando o mesmo diálogo aparece repetidamente.

---

## 18. Schema SQLite inicial

```sql
CREATE TABLE translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_text TEXT NOT NULL,
    normalized_source_text TEXT NOT NULL UNIQUE,
    translated_text TEXT NOT NULL,
    source_lang TEXT,
    target_lang TEXT NOT NULL DEFAULT 'pt-BR',
    created_at TEXT NOT NULL
);

CREATE TABLE image_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_hash TEXT NOT NULL UNIQUE,
    source_text TEXT,
    translated_text TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_term TEXT NOT NULL,
    target_term TEXT NOT NULL,
    note TEXT
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 19. Overlay

Usar uma janela PySide6 com as seguintes características:

```txt
sem borda
transparente
sempre no topo
posição configurável
opacidade configurável
modo click-through opcional
```

### Modos previstos

#### 1. Legenda

Mostra a tradução embaixo da tela.

Mais simples e seguro para o MVP.

#### 2. Substituição visual

Cobre a caixa de diálogo original com fundo escuro translúcido.

Mais bonito, mas pode esconder elementos da UI.

#### 3. Janela lateral

Mostra histórico de traduções.

Útil para debug e jogos com muito texto.

---

## 20. Configurações essenciais

O usuário deve conseguir configurar:

```txt
janela do jogo
região de captura
posição do overlay
tamanho da fonte
opacidade do overlay
idioma origem
idioma destino
modelo Ollama
temperatura do modelo
timeout do modelo
atalho de pausar
atalho de repetir última tradução
modo de overlay
```

---

## 21. Fases e subfases

## Fase 0 — Fundação do projeto

### 0.1 Criar base

Entregáveis:

```txt
pyproject.toml
estrutura de pastas
README inicial
script de execução
configuração com uv
```

### 0.2 Definir contratos

Entregáveis:

```txt
domain/models.py
domain/interfaces.py
application/translation_pipeline_service.py
```

### 0.3 Criar testes mínimos

Entregáveis:

```txt
teste do cache
teste do pipeline com mocks
teste de normalização de texto
```

---

## Fase 1 — Protótipo de tradução sem UI completa

### 1.1 Captura de região fixa

Entregáveis:

```txt
MSSScreenCapture
script para salvar screenshot da região
config manual de x/y/width/height
```

### 1.2 Chamada ao Ollama

Entregáveis:

```txt
Ollama client
envio de imagem
resposta JSON validada
timeout configurável
```

### 1.3 Pipeline CLI

Entregáveis:

```txt
captura imagem
extrai texto
traduz
imprime no terminal
```

Critério de pronto:

```txt
Rodar um comando e obter tradução de uma região do jogo.
```

---

## Fase 2 — Overlay mínimo

### 2.1 Criar overlay transparente

Entregáveis:

```txt
OverlayWindow
show_text()
hide()
configuração de posição
```

### 2.2 Integrar pipeline com overlay

Entregáveis:

```txt
loop de captura
tradução aparece sobre o jogo
```

### 2.3 Atalhos básicos

Entregáveis:

```txt
pausar/resumir
repetir última tradução
fechar app
```

Critério de pronto:

```txt
Jogar com tradução aparecendo em tempo real.
```

---

## Fase 3 — Controle de latência e custo

### 3.1 Detector de mudança visual

Entregáveis:

```txt
ImageChangeDetector
hash perceptual
limiar de diferença configurável
```

### 3.2 Cache por texto

Entregáveis:

```txt
SQLiteTranslationCache
normalização de texto
consulta antes da tradução
```

### 3.3 Cache por imagem

Entregáveis:

```txt
ImageCacheRepository
evitar OCR repetido
```

Critério de pronto:

```txt
O sistema não chama o modelo repetidamente para a mesma fala.
```

---

## Fase 4 — UI de configuração

### 4.1 Janela principal

Entregáveis:

```txt
selecionar modelo
selecionar idioma
ativar/desativar overlay
status do Ollama
```

### 4.2 Seleção visual de região

Entregáveis:

```txt
tela para escolher área da caixa de diálogo
salvar região por perfil de jogo
```

### 4.3 Perfis de jogo

Entregáveis:

```txt
GameProfileRepository
criar perfil
editar perfil
carregar perfil automaticamente por título da janela
```

Critério de pronto:

```txt
Usuário não precisa editar arquivo de configuração manualmente.
```

---

## Fase 5 — Qualidade de tradução

### 5.1 Contexto curto

Entregáveis:

```txt
histórico das últimas falas
contexto enviado no prompt
limite configurável
```

### 5.2 Glossário

Entregáveis:

```txt
termos fixos
nomes próprios
traduções preferidas
injeção no prompt
```

### 5.3 Pós-processamento

Entregáveis:

```txt
remoção de lixo de OCR
quebra de linha
limite de caracteres por linha
correção de espaços
```

Critério de pronto:

```txt
Traduções ficam consistentes entre falas.
```

---

## Fase 6 — OCR dedicado opcional

### 6.1 Adapter para OCR rápido

Entregáveis:

```txt
RapidOCRTextExtractor ou EasyOCRTextExtractor
```

### 6.2 Pipeline combinado

Fluxo:

```txt
OCR dedicado
↓
LLM corrige OCR
↓
LLM traduz
```

### 6.3 Estratégia fallback

Entregáveis:

```txt
se OCR dedicado falhar → usar vision LLM
```

Critério de pronto:

```txt
Menor latência em textos simples.
```

---

## Fase 7 — Suporte específico a RPG Maker

Objetivo da fase:

```txt
reduzir dependencia de OCR
preencher cache com textos limpos do jogo
melhorar consistencia de traducao
manter o jogo original sem modificacoes
```

Escopo inicial recomendado:

```txt
RPG Maker MV/MZ primeiro
somente leitura dos arquivos do jogo
sem patchar ou sobrescrever arquivos
OCR/vision continua como fallback
```

### 7.1 Detector de versão

Entregáveis:

```txt
detectar RPG Maker MV/MZ
detectar VX/VX Ace quando possível
localizar pasta data ou www/data
validar JSONs conhecidos: System.json, MapInfos.json, CommonEvents.json
```

### 7.2 Leitor MV/MZ

Entregáveis:

```txt
ler arquivos JSON
extrair eventos
extrair diálogos
extrair nomes de personagens
extrair escolhas e texto rolante
preservar origem: arquivo, mapa, evento, pagina, indice do comando
```

Comandos de evento prioritarios em MV/MZ:

```txt
101 inicio de mensagem
401 linha de mensagem
102 escolhas
402 ramo de escolha
405 texto rolante
```

Arquivos prioritarios:

```txt
MapXXX.json
CommonEvents.json
System.json
Actors.json
Items.json
Skills.json
Weapons.json
Armors.json
Enemies.json
```

### 7.3 Pré-cache

Entregáveis:

```txt
traduzir textos conhecidos previamente
salvar no cache
usar OCR apenas para localizar texto atual
casar texto OCR com texto extraido por normalizacao/fuzzy matching simples
```

Critério de pronto:

```txt
Jogos RPG Maker MV/MZ têm tradução mais rápida e consistente.
```

---

## Fase 8 — Empacotamento

### 8.1 Build local

Entregáveis:

```txt
executável Windows
configuração em pasta do usuário
logs locais
```

### 8.2 Diagnóstico

Entregáveis:

```txt
tela de status
teste de captura
teste do Ollama
teste do modelo
teste do overlay
```

### 8.3 Distribuição

Entregáveis:

```txt
README de instalação
guia de configuração
release zip
```

---

## 22. Como usar Codex ou Claude Code

Não pedir para o agente criar o app inteiro de uma vez.

### Exemplo ruim

```txt
Crie um tradutor em tempo real para RPG Maker.
```

### Exemplo bom

```txt
Implemente a classe MSSScreenCapture que segue a interface ScreenCapture.
Ela deve receber TextRegion e retornar PIL.Image.
Inclua testes unitários usando uma região fake quando possível.
Não altere outras camadas.
```

---

## 23. Ordem recomendada para agentes

### Primeiro

Criar:

```txt
domain/models.py
domain/interfaces.py
application/translation_pipeline_service.py
tests/unit/test_translation_pipeline_service.py
```

### Depois

Implementar módulos isolados:

```txt
MSSScreenCapture
OllamaVisionTranslator
SQLiteTranslationCache
OverlayWindow
ImageChangeDetector
SettingsRepository
```

### Depois

Integrar:

```txt
capture_loop_service.py
main.py
bootstrap.py
```

---

## 24. Regras arquiteturais

### 1. UI não chama Ollama diretamente

Errado:

```txt
OverlayWindow → Ollama
```

Certo:

```txt
OverlayWindow ← TranslationPipelineService → Translator
```

---

### 2. Infraestrutura implementa interfaces

```txt
domain/interfaces.py define
infrastructure/... implementa
```

---

### 3. Pipeline não conhece detalhes de UI

O pipeline deve saber apenas isto:

```python
overlay.show_text(text)
```

---

### 4. Banco não fica espalhado pelo app

Acesso ao SQLite deve ficar em repositories:

```txt
translation_cache_repository.py
glossary_repository.py
settings_repository.py
```

---

### 5. Prompt em módulo próprio

Usar:

```txt
prompt_builder.py
```

Não deixar prompt perdido dentro do client HTTP.

---

## 25. Arquitetura de runtime

```txt
App inicia
↓
Carrega settings
↓
Detecta Ollama
↓
Carrega perfil do jogo
↓
Inicia UI
↓
Usuário ativa tradução
↓
CaptureLoopService captura região
↓
TranslationPipelineService processa imagem
↓
OverlayRenderer exibe tradução
```

---

## 26. Fluxo com cache

```txt
Imagem capturada
↓
Hash visual existe?
 ├─ sim → mostra tradução cacheada
 └─ não
      ↓
   OCR/vision
      ↓
   Texto normalizado existe?
      ├─ sim → salva hash + mostra cache
      └─ não
           ↓
        traduz
           ↓
        salva texto + hash
           ↓
        mostra overlay
```

---

## 27. Logs

Usar logs desde o início.

Arquivos sugeridos:

```txt
logs/app.log
logs/ollama.log
logs/pipeline.log
```

Registrar:

```txt
tempo de captura
tempo de OCR
tempo de tradução
cache hit/miss
erros do Ollama
texto extraído
texto traduzido
```

Permitir desligar log de texto por privacidade.

---

## 28. Configuração recomendada

Usar `pydantic-settings`.

Exemplo:

```python
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"

    target_language: str = "pt-BR"
    source_language: str = "auto"

    capture_interval_ms: int = 500
    translation_timeout_seconds: int = 30

    overlay_font_size: int = 24
    overlay_opacity: float = 0.85

    database_path: str = "data/app.sqlite3"
```

---

## 29. Critérios de sucesso do MVP

O MVP estará pronto quando:

```txt
1. O usuário escolhe uma região da tela.
2. O app captura essa região.
3. O modelo local extrai/traduz o texto.
4. A tradução aparece em overlay.
5. Falas repetidas usam cache.
6. O usuário consegue pausar e retomar.
```

### Status em 2026-05-27

O MVP esta funcionalmente concluido para o fluxo externo por captura de tela:

```txt
regiao selecionavel
captura MSS
OCR/vision via Ollama
traducao PT-BR
overlay ajustavel
cache por imagem e texto
pausa/retomada
diagnostico de pipeline e tempo
```

Validacoes manuais indicaram melhora de latencia apos desligar contexto recente
por padrao e resolucao aparente da contaminacao de falas anteriores. O projeto
deve entrar em fase de estabilizacao e evolucao especifica, em vez de expandir o
MVP com novas features grandes.

Não precisa ter ainda:

```txt
leitura de arquivos RPG Maker
detecção automática perfeita
OCR dedicado
tradução em lote
suporte Linux
UI bonita
```

O proximo eixo tecnico recomendado e suporte especifico a RPG Maker MV/MZ por
leitura dos arquivos do jogo, mantendo OCR/vision como fallback.

---

## 30. Riscos técnicos

### 1. Latência alta do modelo vision

Mitigação:

```txt
cache por imagem
captura em intervalo maior
OCR dedicado depois
recorte preciso da região
```

### 2. OCR ruim em fonte pixelada

Mitigação:

```txt
pré-processamento com OpenCV
aumento de escala
contraste
prompt específico
fallback manual de região
```

### 3. Overlay não aparece sobre alguns jogos

Mitigação:

```txt
modo janela sem borda no jogo
configurações específicas Windows
janela always-on-top
modo legenda em janela separada
```

### 4. Agente gerar código acoplado demais

Mitigação:

```txt
interfaces primeiro
testes primeiro
tarefas pequenas
não deixar UI acessar infraestrutura diretamente
```

---

## 31. Decisão final de arquitetura

A arquitetura recomendada é:

```txt
Monólito modular desktop
com separação leve em Domain, Application, Infrastructure e UI
```

### Por quê

É mais simples para desenvolver, testar, empacotar e distribuir.

### Quando evoluir

Separar em processos diferentes apenas se:

```txt
OCR/tradução travar a UI
quiser suportar múltiplos clientes
quiser rodar tradução em outro PC/GPU
```

Nesse caso, o primeiro split seria:

```txt
Desktop UI
↓
Local Translation Server
↓
Ollama / OCR / Cache
```

Para o momento atual, manter tudo no app desktop.

---

## 32. Resumo executivo

- **Stack:** Python 3.13, PySide6, MSS, OpenCV, Pillow, SQLite, Ollama com `gemma4:e4b`.
- **Arquitetura:** monólito modular desktop, com Domain/Application/Infrastructure/UI.
- **MVP:** captura de região + vision/tradução + overlay + cache.
- **Evolução:** OCR dedicado, glossário, perfis de jogo e suporte específico a RPG Maker MV/MZ.
