from __future__ import annotations

from pathlib import Path


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e4b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 10.0

DEFAULT_CAPTURE_INTERVAL_MS = 500
DEFAULT_TARGET_LANGUAGE = "pt-BR"
DEFAULT_SOURCE_LANGUAGE = "auto"

DEFAULT_OVERLAY_OPACITY = 0.85
DEFAULT_OVERLAY_FONT_SIZE = 24

DEFAULT_DATABASE_PATH = Path("data") / "app.sqlite3"
DEFAULT_CAPTURE_PREVIEW_PATH = Path("captures") / "preview.png"

DEFAULT_RPG_MAKER_BRIDGE_ENABLED = True
DEFAULT_RPG_MAKER_BRIDGE_HOST = "127.0.0.1"
DEFAULT_RPG_MAKER_BRIDGE_PORT = 8765

# Limites de quebra de linha do patch, em caracteres visíveis. Dependem do
# jogo/tema, por isso são configuráveis; os padrões mantêm os valores antes
# fixos no exportador de patch MV/MZ.
DEFAULT_PATCH_MESSAGE_LINE_LIMIT = 58
DEFAULT_PATCH_MESSAGE_FACE_LINE_LIMIT = 44
DEFAULT_PATCH_DESCRIPTION_LINE_LIMIT = 52

# Falas anteriores do mesmo bloco (evento/pagina) enviadas como contexto na
# traducao em lote MV/MZ. 4 linhas cabem com folga no num_ctx de modelos locais
# classe 4-8B; 0 desativa o contexto.
DEFAULT_RPG_MAKER_BATCH_CONTEXT_LINES = 4
