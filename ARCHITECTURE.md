# ARCHITECTURE.md

# RPG Live Translator — Arquitetura do Projeto

## 1. Visão geral

O projeto é um aplicativo desktop em Python para tradução em tempo real de jogos RPG Maker.

A arquitetura recomendada é um **monólito modular desktop**, organizado em camadas leves:

```txt
UI
Application
Domain
Infrastructure
```

O objetivo não é aplicar Clean Architecture de forma rígida, mas separar responsabilidades o suficiente para manter o projeto testável, evolutivo e fácil de modificar com ferramentas como Codex ou Claude Code.

---

## 2. Objetivos arquiteturais

A arquitetura deve favorecer:

- baixa latência na tradução;
- fácil troca de OCR, modelo LLM ou mecanismo de captura;
- UI desacoplada da lógica de tradução;
- cache agressivo para reduzir chamadas ao modelo;
- testes unitários nos fluxos principais;
- suporte futuro a leitura direta de arquivos RPG Maker;
- empacotamento simples para Windows.

---

## 3. Decisão arquitetural principal

## Estilo escolhido

```txt
Modular Monolith Desktop
```

## Por que usar

Resolve o problema de manter o app simples para distribuição, mas organizado o bastante para crescer.

O projeto precisa lidar com captura de tela, OCR/vision, tradução, cache, overlay, atalhos e configurações. Colocar tudo em um único arquivo ou em classes gigantes geraria acoplamento rápido.

## Quando usar

Use essa arquitetura enquanto o app for executado localmente em uma única máquina.

## Quando evitar ou evoluir

Evite transformar cedo demais em microsserviços ou backend web.

Considere dividir em processos separados apenas se:

- o OCR/tradução travar a UI;
- for necessário rodar o modelo em outro computador;
- for necessário servir múltiplos clientes;
- o pipeline de tradução precisar escalar separadamente.

Primeira evolução possível:

```txt
Desktop UI
    ↓
Local Translation Server
    ↓
Ollama / OCR / Cache
```

---

## 4. Camadas

## 4.1 UI

Responsável por interação com o usuário.

Exemplos:

- janela principal;
- overlay;
- seletor de região;
- tray icon;
- atalhos;
- telas de configuração.

A UI não deve conhecer detalhes de OCR, SQLite, Ollama ou captura de tela.

```txt
Correto:
UI → Application Service
```

```txt
Errado:
UI → Ollama Client
UI → SQLite direto
UI → MSS direto
```

---

## 4.2 Application

Responsável por orquestrar casos de uso.

Exemplos:

- loop de captura;
- pipeline de tradução;
- seleção de região;
- gerenciamento de perfis;
- controle de pausa/resume;
- aplicação de cache.

Essa camada sabe coordenar dependências, mas não conhece detalhes técnicos internos delas.

Exemplo:

```txt
CaptureLoopService
    usa ScreenCapture
    usa TranslationPipelineService
```

---

## 4.3 Domain

Responsável pelos modelos e contratos centrais.

Deve conter:

- entidades simples;
- value objects;
- interfaces;
- erros de domínio;
- regras puras quando existirem.

O domínio não deve importar PySide6, MSS, SQLite, OpenCV, requests ou bibliotecas específicas de infraestrutura.

---

## 4.4 Infrastructure

Responsável por implementações técnicas.

Exemplos:

- captura com MSS;
- detecção de janela com Win32;
- chamada HTTP para Ollama;
- cache com SQLite;
- pré-processamento com OpenCV;
- leitura de arquivos RPG Maker;
- persistência de configurações.

A infraestrutura implementa contratos definidos no domínio.

---

## 5. Diagrama de dependências

```txt
┌─────────────────────────────┐
│             UI              │
│ MainWindow / Overlay / Tray │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         Application         │
│ Pipeline / Capture Loop     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│            Domain           │
│ Models / Interfaces / Errors│
└──────────────▲──────────────┘
               │
┌──────────────┴──────────────┐
│        Infrastructure       │
│ MSS / Ollama / SQLite / OCR │
└─────────────────────────────┘
```

Regra importante:

```txt
UI e Infrastructure dependem de Domain.
Domain não depende de UI nem Infrastructure.
Application depende de Domain.
```

---

## 6. Estrutura de pastas

```txt
rpg_live_translator/
  app/
    main.py
    bootstrap.py

  ui/
    main_window.py
    overlay_window.py
    settings_window.py
    region_selector_window.py
    tray_icon.py

  application/
    capture_loop_service.py
    translation_pipeline_service.py
    region_selection_service.py
    hotkey_service.py
    game_profile_service.py

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
      image_hasher.py

    translation/
      ollama_client.py
      ollama_vision_text_extractor.py
      ollama_translator.py
      prompt_builder.py

    persistence/
      sqlite_connection.py
      translation_cache_repository.py
      image_cache_repository.py
      glossary_repository.py
      settings_repository.py
      game_profile_repository.py

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

## 7. Modelos de domínio

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
    source_lang: str = "auto"
    target_lang: str = "pt-BR"


@dataclass(frozen=True)
class GameProfile:
    name: str
    window_title: str
    text_region: TextRegion
```

## Por que usar dataclass frozen

Resolve o problema de mutação acidental em objetos que representam dados do fluxo.

Use quando o objeto representa um valor transportado entre camadas.

Evite se o objeto precisar de ciclo de vida complexo, estado mutável ou comportamento rico.

---

## 8. Interfaces principais

As interfaces ficam em `domain/interfaces.py`.

```python
from typing import Protocol
from PIL import Image

from .models import ExtractedText, GameProfile, TextRegion, TranslationResult


class ScreenCapture(Protocol):
    def capture_region(self, region: TextRegion) -> Image.Image:
        ...


class WindowDetector(Protocol):
    def find_game_window(self, title: str):
        ...


class TextExtractor(Protocol):
    def extract(self, image: Image.Image) -> ExtractedText:
        ...


class Translator(Protocol):
    def translate(self, text: str, context: list[str]) -> TranslationResult:
        ...


class TranslationCache(Protocol):
    def get_by_text(self, source_text: str) -> TranslationResult | None:
        ...

    def save_translation(self, result: TranslationResult) -> None:
        ...


class ImageCache(Protocol):
    def get_by_hash(self, image_hash: str) -> TranslationResult | None:
        ...

    def save_image_result(self, image_hash: str, result: TranslationResult) -> None:
        ...


class OverlayRenderer(Protocol):
    def show_text(self, text: str) -> None:
        ...

    def hide(self) -> None:
        ...


class GameProfileRepository(Protocol):
    def get_active_profile(self) -> GameProfile | None:
        ...

    def save(self, profile: GameProfile) -> None:
        ...
```

---

## 9. Pipeline de tradução

## Fluxo principal

```txt
Capturar região
    ↓
Verificar mudança visual
    ↓
Gerar hash da imagem
    ↓
Consultar cache por imagem
    ↓
Extrair texto
    ↓
Normalizar texto
    ↓
Consultar cache por texto
    ↓
Traduzir se necessário
    ↓
Salvar cache
    ↓
Renderizar overlay
```

---

## 10. Serviço principal de pipeline

```python
class TranslationPipelineService:
    def __init__(
        self,
        text_extractor,
        translator,
        translation_cache,
        image_cache,
        image_hasher,
        change_detector,
        overlay,
        text_normalizer,
    ):
        self.text_extractor = text_extractor
        self.translator = translator
        self.translation_cache = translation_cache
        self.image_cache = image_cache
        self.image_hasher = image_hasher
        self.change_detector = change_detector
        self.overlay = overlay
        self.text_normalizer = text_normalizer
        self.context: list[str] = []

    def process_frame(self, image):
        if not self.change_detector.has_changed(image):
            return

        image_hash = self.image_hasher.hash(image)
        cached_by_image = self.image_cache.get_by_hash(image_hash)

        if cached_by_image:
            self.overlay.show_text(cached_by_image.translated_text)
            return

        extracted = self.text_extractor.extract(image)
        normalized_text = self.text_normalizer.normalize(extracted.text)

        if not normalized_text:
            return

        cached_by_text = self.translation_cache.get_by_text(normalized_text)

        if cached_by_text:
            self.image_cache.save_image_result(image_hash, cached_by_text)
            self.overlay.show_text(cached_by_text.translated_text)
            return

        result = self.translator.translate(normalized_text, self.context)

        self.translation_cache.save_translation(result)
        self.image_cache.save_image_result(image_hash, result)

        self.context.append(normalized_text)
        self.context = self.context[-5:]

        self.overlay.show_text(result.translated_text)
```

---

## 11. Loop de captura

O `CaptureLoopService` controla quando capturar e processar frames.

Responsabilidades:

- respeitar intervalo configurado;
- capturar a região ativa;
- evitar bloquear a UI;
- pausar e retomar;
- lidar com erros sem derrubar o app.

Fluxo:

```txt
Timer dispara
    ↓
Verifica se tradução está ativa
    ↓
Obtém perfil de jogo
    ↓
Captura região
    ↓
Envia imagem ao pipeline
```

Importante: a chamada ao modelo não deve rodar na thread principal da UI.

---

## 12. OCR e tradução

## MVP

No MVP, pode existir um adaptador combinado:

```txt
Imagem → Ollama Vision → source_text + translated_text
```

Isso acelera o desenvolvimento.

Mesmo assim, internamente, mantenha o contrato separado:

```txt
TextExtractor
Translator
```

## Arquitetura final

Fluxo recomendado depois do MVP:

```txt
Imagem
    ↓
OCR dedicado
    ↓
Correção com LLM
    ↓
Tradução com LLM
```

## Quando usar vision direto

Use quando:

- o OCR dedicado falhar;
- a fonte for muito estilizada;
- houver texto com sombra, contorno ou baixa resolução;
- for mais importante funcionar do que ser rápido.

## Quando evitar vision direto

Evite quando:

- o texto é simples e frequente;
- há muitas chamadas repetidas;
- a latência está alta;
- o hardware local é limitado.

---

## 13. Integração com Ollama

Módulos sugeridos:

```txt
infrastructure/translation/ollama_client.py
infrastructure/translation/ollama_vision_text_extractor.py
infrastructure/translation/ollama_translator.py
infrastructure/translation/prompt_builder.py
```

Responsabilidades do client:

- chamar API local do Ollama;
- aplicar timeout;
- tratar erro HTTP;
- validar JSON de resposta;
- registrar logs úteis;
- não conter regra de UI.

Prompt base para MVP:

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

## 14. Cache

O cache é parte crítica da performance.

## Cache por imagem

Resolve chamadas repetidas quando a mesma caixa de diálogo continua na tela.

Chave:

```txt
image_hash
```

Valor:

```txt
source_text
translated_text
```

## Cache por texto

Resolve falas repetidas mesmo quando a imagem muda levemente.

Chave:

```txt
normalized_source_text
```

Valor:

```txt
translated_text
```

## Ordem recomendada

```txt
1. cache por imagem
2. OCR / extração
3. cache por texto
4. tradução
5. salvar ambos
```

---

## 15. Banco de dados SQLite

Schema inicial:

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

CREATE TABLE game_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    window_title TEXT NOT NULL,
    region_x INTEGER NOT NULL,
    region_y INTEGER NOT NULL,
    region_width INTEGER NOT NULL,
    region_height INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 16. Overlay

O overlay deve ser uma implementação de `OverlayRenderer`.

Características:

- sem borda;
- sempre no topo;
- fundo transparente ou translúcido;
- posição configurável;
- tamanho de fonte configurável;
- modo legenda;
- modo caixa sobreposta;
- modo histórico lateral no futuro.

## Regras

O overlay apenas exibe texto.

Não deve:

- chamar tradutor;
- consultar banco;
- capturar tela;
- montar prompt;
- conhecer Ollama.

---

## 17. Configurações

Use `pydantic-settings` para carregar configurações.

Exemplo:

```python
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"

    source_language: str = "auto"
    target_language: str = "pt-BR"

    capture_interval_ms: int = 500
    translation_timeout_seconds: int = 30

    overlay_font_size: int = 24
    overlay_opacity: float = 0.85

    database_path: str = "data/app.sqlite3"
```

Configurações editáveis pela UI devem ser persistidas no SQLite ou em arquivo local do usuário.

---

## 18. Logs

Use logs desde o início.

Eventos importantes:

- app iniciado;
- perfil carregado;
- região capturada;
- cache hit/miss;
- tempo de OCR;
- tempo de tradução;
- erro do Ollama;
- texto extraído;
- tradução final.

Atenção: permita desligar logs de texto para preservar privacidade.

---

## 19. Tratamento de erros

Erros esperados:

- Ollama indisponível;
- modelo não instalado;
- resposta inválida do modelo;
- região de captura inválida;
- janela do jogo não encontrada;
- overlay não consegue ficar no topo;
- SQLite bloqueado ou inacessível.

Cada erro deve ser tratado de forma localizada.

Exemplo:

```txt
Ollama indisponível → mostrar aviso na UI, manter app aberto
Região inválida → pedir nova seleção
Cache falhou → seguir sem cache e registrar log
```

---

## 20. Testes

## Unitários

Prioridade:

- normalização de texto;
- cache repository;
- pipeline com mocks;
- prompt builder;
- image change detector.

## Integração

Prioridade:

- SQLite real em banco temporário;
- chamada ao Ollama opcional;
- captura de região opcional;
- overlay manual.

## O que evitar testar cedo

Evite gastar muito tempo tentando automatizar testes de overlay e captura de jogo no início. Esses pontos podem ter teste manual guiado.

---

## 21. Regras para agentes de código

Ao usar Codex ou Claude Code, peça módulos pequenos.

## Bom pedido

```txt
Implemente SQLiteTranslationCache seguindo a interface TranslationCache.
Use sqlite3 padrão do Python.
Inclua testes unitários com banco temporário.
Não altere a UI.
```

## Pedido ruim

```txt
Crie o app inteiro de tradução em tempo real.
```

## Ordem recomendada

```txt
1. domain/models.py
2. domain/interfaces.py
3. application/translation_pipeline_service.py
4. infrastructure/persistence/sqlite repositories
5. infrastructure/capture/mss_screen_capture.py
6. infrastructure/translation/ollama client
7. ui/overlay_window.py
8. application/capture_loop_service.py
9. app/bootstrap.py
10. app/main.py
```

---

## 22. Regras de acoplamento

## Regra 1

UI não acessa infraestrutura diretamente.

```txt
Errado:
MainWindow → SQLiteTranslationCache
```

```txt
Certo:
MainWindow → GameProfileService → GameProfileRepository
```

## Regra 2

Prompt não fica espalhado pelo código.

```txt
Correto:
prompt_builder.py
```

## Regra 3

Banco só é acessado por repositories.

```txt
Correto:
translation_cache_repository.py
settings_repository.py
```

## Regra 4

Pipeline não deve saber se o overlay é PySide6, console ou outro renderer.

```txt
Correto:
overlay.show_text(text)
```

## Regra 5

Infraestrutura pode depender de bibliotecas externas. Domínio não.

---

## 23. Runtime esperado

```txt
App inicia
    ↓
Carrega settings
    ↓
Inicializa SQLite
    ↓
Verifica Ollama
    ↓
Carrega perfil ativo
    ↓
Inicializa UI
    ↓
Usuário ativa tradução
    ↓
CaptureLoopService captura região
    ↓
TranslationPipelineService processa imagem
    ↓
OverlayRenderer mostra tradução
```

---

## 24. MVP arquitetural

O MVP deve conter:

```txt
Domain models
Domain interfaces
TranslationPipelineService
MSSScreenCapture
Ollama vision adapter
SQLite cache
OverlayWindow simples
CaptureLoopService
Config básica
```

Não precisa conter ainda:

```txt
leitor RPG Maker
OCR dedicado
UI completa
histórico lateral
detecção automática perfeita
build final
```

---

## 25. Riscos arquiteturais

## Risco 1: UI travar durante tradução

Mitigação:

- worker thread;
- fila de processamento;
- timeout no Ollama;
- não processar novo frame enquanto outro está em andamento.

## Risco 2: agentes criarem dependências cruzadas

Mitigação:

- interfaces primeiro;
- testes do pipeline;
- revisar imports;
- tarefas pequenas.

## Risco 3: cache mal desenhado

Mitigação:

- normalizar texto antes de salvar;
- cache por imagem e por texto;
- constraints únicas no SQLite.

## Risco 4: OCR caro demais

Mitigação:

- região pequena;
- detector de mudança;
- hash perceptual;
- OCR dedicado no futuro.

---

## 26. Decisão final

A arquitetura final recomendada é:

```txt
Monólito modular desktop
com separação leve entre UI, Application, Domain e Infrastructure
```

Essa escolha maximiza velocidade de desenvolvimento sem sacrificar manutenção, testabilidade e evolução futura.
