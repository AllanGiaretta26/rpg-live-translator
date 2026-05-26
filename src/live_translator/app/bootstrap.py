from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from live_translator.application.capture_loop_service import CaptureLoopService
from live_translator.application.capture_preview_service import CapturePreviewService
from live_translator.application.profile_settings_service import ProfileSettingsService
from live_translator.application.translation_pipeline_service import TranslationPipelineService
from live_translator.config.settings import AppSettings
from live_translator.infrastructure.image.image_change_detector import ImageChangeDetector
from live_translator.infrastructure.image.image_hasher import ImageHasher
from live_translator.infrastructure.persistence.game_profile_repository import SQLiteGameProfileRepository
from live_translator.infrastructure.persistence.image_cache_repository import SQLiteImageCacheRepository
from live_translator.infrastructure.persistence.settings_repository import SQLiteSettingsRepository
from live_translator.infrastructure.persistence.sqlite_connection import SQLiteConnectionManager
from live_translator.infrastructure.persistence.translation_cache_repository import (
    SQLiteTranslationCacheRepository,
)
from live_translator.infrastructure.translation.ollama_client import OllamaClient
from live_translator.infrastructure.translation.ollama_translator import OllamaTranslator
from live_translator.infrastructure.translation.ollama_vision_text_extractor import (
    OllamaVisionTextExtractor,
)


class Overlay(Protocol):
    def show_text(self, text: str) -> None: ...

    def hide(self) -> None: ...


class UiApp(Protocol):
    def run(self) -> int: ...


class ConsoleOverlay:
    def show_text(self, text: str) -> None:
        print(text)

    def hide(self) -> None:
        return


class ConsoleUiApp:
    def __init__(
        self,
        overlay: Overlay,
        capture_loop: object | None = None,
        profile_settings: object | None = None,
        capture_preview: object | None = None,
        pipeline_diagnostics: object | None = None,
    ) -> None:
        self._overlay = overlay
        self._capture_loop = capture_loop
        self._profile_settings = profile_settings
        self._capture_preview = capture_preview
        self._pipeline_diagnostics = pipeline_diagnostics

    def run(self) -> int:
        self._overlay.show_text("Live Translator pronto.")
        return 0


class NullScreenCaptureService:
    def capture_region(self, region: object) -> object:
        return object()


@dataclass(frozen=True)
class AppRuntime:
    settings: AppSettings
    database: SQLiteConnectionManager
    settings_repository: SQLiteSettingsRepository
    game_profile_repository: SQLiteGameProfileRepository
    translation_cache_repository: SQLiteTranslationCacheRepository
    image_cache_repository: SQLiteImageCacheRepository
    profile_settings_service: ProfileSettingsService
    capture_preview_service: CapturePreviewService
    ollama_client: OllamaClient
    capture_service: object
    pipeline: TranslationPipelineService
    capture_loop: CaptureLoopService
    overlay: Overlay
    ui: UiApp

    def start(self) -> int:
        if not self.ollama_client.is_available():
            self.overlay.show_text(
                "Ollama indisponivel. Verifique o servico e continue usando o app."
            )
        return self.ui.run()


def bootstrap(
    settings: AppSettings | None = None,
    overlay_factory: Callable[[], Overlay] | None = None,
    ui_factory: Callable[
        [
            Overlay,
            CaptureLoopService,
            ProfileSettingsService,
            CapturePreviewService,
            TranslationPipelineService,
        ],
        UiApp,
    ]
    | None = None,
) -> AppRuntime:
    resolved_settings = settings or AppSettings()

    database = SQLiteConnectionManager(resolved_settings.database_path)
    settings_repository = SQLiteSettingsRepository(database)
    game_profile_repository = SQLiteGameProfileRepository(database, settings_repository)
    profile_settings_service = ProfileSettingsService(game_profile_repository)
    translation_cache_repository = SQLiteTranslationCacheRepository(database)
    image_cache_repository = SQLiteImageCacheRepository(database)

    ollama_client = OllamaClient(
        base_url=str(resolved_settings.ollama_base_url),
        model=resolved_settings.ollama_model,
        timeout_seconds=float(resolved_settings.ollama_timeout_seconds),
    )
    capture_service = _create_capture_service()
    capture_preview_service = CapturePreviewService(
        capture_service,
        resolved_settings.capture_preview_path,
    )

    image_hasher = ImageHasher()
    change_detector = ImageChangeDetector()
    overlay = (overlay_factory or _create_overlay)()
    pipeline = TranslationPipelineService(
        text_extractor=OllamaVisionTextExtractor(
            ollama_client,
            target_language=resolved_settings.target_language,
        ),
        translator=OllamaTranslator(
            ollama_client,
            source_language=resolved_settings.source_language,
            target_language=resolved_settings.target_language,
        ),
        translation_cache=translation_cache_repository,
        image_cache=image_cache_repository,
        image_hasher=image_hasher,
        change_detector=change_detector,
        overlay=overlay,
    )
    capture_loop = CaptureLoopService(
        screen_capture=capture_service,
        pipeline=pipeline,
        profile_repository=game_profile_repository,
        capture_interval_ms=resolved_settings.capture_interval_ms,
    )
    ui = (ui_factory or _create_ui)(
        overlay,
        capture_loop,
        profile_settings_service,
        capture_preview_service,
        pipeline,
    )

    return AppRuntime(
        settings=resolved_settings,
        database=database,
        settings_repository=settings_repository,
        game_profile_repository=game_profile_repository,
        translation_cache_repository=translation_cache_repository,
        image_cache_repository=image_cache_repository,
        profile_settings_service=profile_settings_service,
        capture_preview_service=capture_preview_service,
        ollama_client=ollama_client,
        capture_service=capture_service,
        pipeline=pipeline,
        capture_loop=capture_loop,
        overlay=overlay,
        ui=ui,
    )


def _create_capture_service() -> object:
    try:
        from live_translator.infrastructure.capture.mss_screen_capture import (
            MSSScreenCapture,
        )
    except ImportError:
        return NullScreenCaptureService()
    return MSSScreenCapture()


def _create_overlay() -> Overlay:
    try:
        from live_translator.ui.overlay_window import OverlayStyle, OverlayWindow

        return OverlayWindow(OverlayStyle())
    except ImportError:
        return ConsoleOverlay()


def _create_ui(
    overlay: Overlay,
    capture_loop: CaptureLoopService,
    profile_settings: ProfileSettingsService,
    capture_preview: CapturePreviewService,
    pipeline_diagnostics: TranslationPipelineService,
) -> UiApp:
    try:
        from live_translator.ui.main_window import QtUiApp, QtUiSettings

        return QtUiApp(
            overlay,
            capture_loop,
            profile_settings,
            capture_preview,
            pipeline_diagnostics,
            QtUiSettings(),
        )
    except ImportError:
        return ConsoleUiApp(
            overlay,
            capture_loop,
            profile_settings,
            capture_preview,
            pipeline_diagnostics,
        )
