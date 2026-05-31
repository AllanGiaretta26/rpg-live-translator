from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import Callable, Protocol

from live_translator.application.geometry import rectangles_overlap
from live_translator.application.mode_settings_service import (
    CatalogTranslationProgress,
    CatalogTranslationResult,
)
from live_translator.domain.models import (
    CatalogTranslationError,
    GameProfile,
    OperationMode,
    OverlayPlacement,
    RpgMakerImportResult,
    RpgMakerTextEntry,
    RpgMakerTextType,
    TranslationResult,
    TextRegion,
)
from live_translator.ui.mode_control_state import resolve_mode_control_state


class TickableCaptureLoop(Protocol):
    @property
    def is_paused(self) -> bool: ...

    @property
    def is_busy(self) -> bool: ...

    @property
    def last_error_message(self) -> str | None: ...

    def resume(self) -> None: ...

    def pause(self) -> None: ...

    def tick(self) -> bool: ...


class ProfileSettings(Protocol):
    def get_active_profile(self) -> GameProfile | None: ...

    def save_profile(
        self,
        *,
        name: str,
        window_title: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> GameProfile: ...


class CapturePreview(Protocol):
    def capture_preview(
        self,
        *,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Path: ...


class PipelineDiagnostics(Protocol):
    @property
    def last_diagnostic(self) -> str | None: ...

    @property
    def last_timing_summary(self) -> str | None: ...


class RuntimeDiagnostics(Protocol):
    @property
    def last_diagnostic(self) -> str | None: ...

    @property
    def last_timing_summary(self) -> str | None: ...

    @property
    def last_source_text(self) -> str | None: ...

    @property
    def last_translated_text(self) -> str | None: ...

    def reprocess_last_text(self) -> TranslationResult | None: ...


class OverlaySettings(Protocol):
    def get_placement(self) -> OverlayPlacement: ...

    def save_placement(self, placement: OverlayPlacement) -> None: ...


class ModeSettings(Protocol):
    def get_active_mode(self) -> OperationMode: ...

    def set_active_mode(self, mode: OperationMode) -> None: ...

    def get_rpg_maker_project_path(self) -> Path | None: ...

    def set_rpg_maker_project_path(self, path: str | Path | None) -> None: ...

    def import_rpg_maker_project(self, path: str | Path) -> RpgMakerImportResult: ...

    def list_rpg_maker_entries(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RpgMakerTextEntry]: ...

    def count_rpg_maker_entries(self) -> int: ...

    def get_rpg_maker_entry(self, entry_id: int) -> RpgMakerTextEntry | None: ...

    def translate_catalog_entry(self, entry_id: int) -> TranslationResult | None: ...

    def retranslate_catalog_entry(self, entry_id: int) -> TranslationResult | None: ...

    def translate_catalog_entries(
        self,
        *,
        limit: int | None = None,
        text_types: set[RpgMakerTextType] | frozenset[RpgMakerTextType] | None = None,
        on_progress: Callable[[CatalogTranslationProgress], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        should_pause: Callable[[], bool] | None = None,
        wait_if_paused: Callable[[], None] | None = None,
    ) -> CatalogTranslationResult: ...

    def count_cached_catalog_entries(self) -> int: ...

    def clear_contaminated_catalog_cache(self) -> int: ...

    def list_last_batch_errors(self) -> list[CatalogTranslationError]: ...


class EditableOverlay(Protocol):
    def apply_placement(self, placement: OverlayPlacement) -> None: ...

    def current_placement(self) -> OverlayPlacement: ...

    def show_calibration_text(self) -> None: ...

    def set_edit_mode(
        self,
        enabled: bool,
        on_changed: Callable[[OverlayPlacement], None] | None = None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class QtUiSettings:
    capture_interval_ms: int = 500
    rpg_maker_bridge_endpoint: str = "http://127.0.0.1:8765/rpgmaker/text"


class QtUiApp:
    def __init__(
        self,
        overlay: EditableOverlay,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        capture_preview: CapturePreview,
        pipeline_diagnostics: PipelineDiagnostics,
        runtime_diagnostics: RuntimeDiagnostics | None,
        overlay_settings: OverlaySettings,
        mode_settings: ModeSettings,
        settings: QtUiSettings,
    ) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        self._overlay = overlay
        self._capture_loop = capture_loop
        self._mode_settings = mode_settings
        self._settings = settings
        self._timer = QTimer()
        self._timer.setInterval(settings.capture_interval_ms)
        self._timer.timeout.connect(self._tick_capture_loop)
        self._app = QApplication.instance() or getattr(overlay, "app")
        self._window = SettingsWindow(
            overlay,
            capture_loop,
            profile_settings,
            capture_preview,
            pipeline_diagnostics,
            runtime_diagnostics,
            overlay_settings,
            mode_settings,
            settings,
        )

    def run(self) -> int:
        if self._mode_settings.get_active_mode() == OperationMode.UNIVERSAL:
            self._capture_loop.resume()
        else:
            self._capture_loop.pause()
        self._timer.start()
        self._window.show()
        return int(self._app.exec())

    def _tick_capture_loop(self) -> None:
        if self._mode_settings.get_active_mode() == OperationMode.UNIVERSAL:
            self._capture_loop.tick()
        self._window.refresh_capture_status()
        self._window.refresh_pipeline_status()


class SettingsWindow:
    def __init__(
        self,
        overlay: EditableOverlay,
        capture_loop: TickableCaptureLoop,
        profile_settings: ProfileSettings,
        capture_preview: CapturePreview,
        pipeline_diagnostics: PipelineDiagnostics,
        runtime_diagnostics: RuntimeDiagnostics | None,
        overlay_settings: OverlaySettings,
        mode_settings: ModeSettings,
        settings: QtUiSettings,
    ) -> None:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import (
            QDoubleSpinBox,
            QFileDialog,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QCheckBox,
            QComboBox,
            QPushButton,
            QProgressBar,
            QTableWidget,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        self._overlay = overlay
        self._capture_loop = capture_loop
        self._profile_settings = profile_settings
        self._capture_preview = capture_preview
        self._pipeline_diagnostics = pipeline_diagnostics
        self._runtime_diagnostics = runtime_diagnostics
        self._overlay_settings = overlay_settings
        self._mode_settings = mode_settings
        self._settings = settings
        self._file_dialog = QFileDialog
        self._region_selector = None
        self._bulk_progress_queue: Queue[CatalogTranslationProgress] = Queue()
        self._bulk_result_queue: Queue[CatalogTranslationResult | Exception] = Queue()
        self._bulk_cancel_requested = False
        self._bulk_pause_requested = False
        self._bulk_pause_event = Event()
        self._bulk_pause_event.set()
        self._bulk_thread: Thread | None = None
        self._bulk_timer = QTimer()
        self._bulk_timer.setInterval(200)
        self._bulk_timer.timeout.connect(self._poll_bulk_translation)

        self._widget = QWidget()
        self._widget.setWindowTitle("RPG Live Translator")
        self._widget.setMinimumWidth(620)

        self._capture_status = QLabel("Rodando")
        self._pipeline_status = QLabel("Pipeline: aguardando")
        self._pipeline_timing = QLabel("Tempo: aguardando")
        self._pipeline_timing.setWordWrap(True)
        self._runtime_source = QLabel("Fonte MV/MZ: aguardando")
        self._runtime_source.setWordWrap(True)
        self._runtime_translation = QLabel("Traducao MV/MZ: aguardando")
        self._runtime_translation.setWordWrap(True)
        self._mode_status = QLabel("Modo: Universal")
        self._mode_status.setWordWrap(True)
        self._status = QLabel("")
        self._overlap_warning = QLabel("")
        self._overlap_warning.setWordWrap(True)
        self._overlap_warning.setStyleSheet(
            "QLabel {"
            "color: #ffd166;"
            "background-color: rgba(80, 45, 0, 120);"
            "border: 1px solid #b7791f;"
            "padding: 8px;"
            "}"
        )
        self._overlap_warning.hide()

        self._name = QLineEdit()
        self._x = self._spinbox(-10000, 10000)
        self._y = self._spinbox(-10000, 10000)
        self._width = self._spinbox(1, 10000)
        self._height = self._spinbox(1, 10000)
        self._preview = QLabel("Nenhuma area capturada")
        self._preview.setMinimumHeight(170)
        self._preview.setStyleSheet(
            "border: 1px solid #555; background: #111; color: #ddd;"
        )
        self._preview.setScaledContents(False)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._overlay_x = self._spinbox(0, 10000)
        self._overlay_y = self._spinbox(0, 10000)
        self._overlay_width = self._spinbox(160, 10000)
        self._overlay_height = self._spinbox(60, 10000)
        self._overlay_font_size = self._spinbox(8, 96)
        self._overlay_opacity = QDoubleSpinBox()
        self._overlay_opacity.setRange(0.1, 1.0)
        self._overlay_opacity.setSingleStep(0.05)
        self._overlay_opacity.setDecimals(2)

        self._mode = QComboBox()
        self._mode.addItem("Universal", OperationMode.UNIVERSAL.value)
        self._mode.addItem("RPG Maker MV/MZ", OperationMode.RPG_MAKER_MV_MZ.value)
        self._rpg_maker_path = QLineEdit()
        self._rpg_maker_path.setPlaceholderText("Pasta do jogo RPG Maker MV/MZ")
        self._choose_rpg_maker_path = QPushButton("Selecionar pasta")
        self._save_mode = QPushButton("Salvar modo")
        self._import_rpg_maker = QPushButton("Importar catalogo")
        self._catalog_page_size = 500
        self._catalog_offset = 0
        self._catalog_total = 0
        self._catalog_table = QTableWidget(0, 4)
        self._catalog_table.setHorizontalHeaderLabels(("Origem", "Tipo", "Texto", "ID"))
        self._catalog_table.setColumnHidden(3, True)
        self._catalog_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._catalog_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._catalog_table.verticalHeader().hide()
        self._catalog_table.horizontalHeader().setStretchLastSection(False)
        self._catalog_table.setMinimumHeight(220)
        self._refresh_catalog = QPushButton("Atualizar catalogo")
        self._previous_catalog_page = QPushButton("Anterior 500")
        self._next_catalog_page = QPushButton("Proximos 500")
        self._translate_catalog_entry = QPushButton("Traduzir selecionado")
        self._catalog_id = QLineEdit()
        self._catalog_id.setPlaceholderText("ID")
        self._search_catalog_id = QPushButton("Buscar ID")
        self._retranslate_catalog_id = QPushButton("Retraduzir ID")
        self._clear_contaminated_cache = QPushButton("Limpar cache contaminado")
        self._show_batch_errors = QPushButton("Ver erros do ultimo lote")
        self._catalog_cache_status = QLabel("Cache: aguardando")
        self._catalog_cache_status.setWordWrap(True)
        self._bulk_limit = QComboBox()
        self._bulk_limit.addItem("100", 100)
        self._bulk_limit.addItem("500", 500)
        self._bulk_limit.addItem("Todos", 0)
        self._bulk_type_checkboxes = {
            RpgMakerTextType.MESSAGE: QCheckBox("message"),
            RpgMakerTextType.CHOICE: QCheckBox("choice"),
            RpgMakerTextType.SPEAKER: QCheckBox("speaker"),
            RpgMakerTextType.SCROLLING_TEXT: QCheckBox("scrolling_text"),
        }
        self._bulk_type_checkboxes[RpgMakerTextType.MESSAGE].setChecked(True)
        self._bulk_type_checkboxes[RpgMakerTextType.CHOICE].setChecked(True)
        self._bulk_type_checkboxes[RpgMakerTextType.SPEAKER].setChecked(False)
        self._bulk_type_checkboxes[RpgMakerTextType.SCROLLING_TEXT].setChecked(True)
        self._translate_catalog = QPushButton("Traduzir catalogo")
        self._pause_catalog_translation = QPushButton("Pausar lote")
        self._pause_catalog_translation.setEnabled(False)
        self._resume_catalog_translation = QPushButton("Retomar lote")
        self._resume_catalog_translation.setEnabled(False)
        self._cancel_catalog_translation = QPushButton("Cancelar")
        self._cancel_catalog_translation.setEnabled(False)
        self._bulk_progress = QProgressBar()
        self._bulk_progress.setRange(0, 100)
        self._bulk_progress.setValue(0)
        self._bulk_status = QLabel("Lote: aguardando")
        self._bulk_status.setWordWrap(True)

        self._select_region = QPushButton("Selecionar area do texto")
        self._preview_capture = QPushButton("Ver preview da area")
        self._save = QPushButton("Salvar area")
        self._show_overlay = QPushButton("Ajustar overlay")
        self._save_overlay = QPushButton("Salvar overlay")
        self._reprocess_runtime_text = QPushButton("Reprocessar fala atual")
        self._pause = QPushButton("Pausar")
        self._resume = QPushButton("Retomar")
        self._quit = QPushButton("Fechar")

        tabs = QTabWidget()
        tabs.addTab(
            self._build_mode_tab(QFormLayout, QHBoxLayout, QVBoxLayout), "0. Modo"
        )
        tabs.addTab(
            self._build_capture_tab(QFormLayout, QHBoxLayout, QVBoxLayout),
            "1. Universal",
        )
        tabs.addTab(
            self._build_catalog_tab(QGroupBox, QHBoxLayout, QVBoxLayout),
            "2. RPG Maker MV/MZ",
        )
        tabs.addTab(
            self._build_overlay_tab(QFormLayout, QHBoxLayout, QVBoxLayout), "3. Overlay"
        )
        tabs.addTab(
            self._build_run_tab(QGroupBox, QHBoxLayout, QVBoxLayout), "4. Executar"
        )

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addWidget(self._overlap_warning)
        layout.addWidget(self._status)
        self._widget.setLayout(layout)

        self._select_region.clicked.connect(self._select_region_on_screen)
        self._choose_rpg_maker_path.clicked.connect(self._choose_rpg_maker_folder)
        self._save_mode.clicked.connect(self._save_mode_settings)
        self._mode.currentIndexChanged.connect(self._refresh_mode_controls)
        self._import_rpg_maker.clicked.connect(self._import_rpg_maker_catalog)
        self._refresh_catalog.clicked.connect(self._refresh_catalog_page)
        self._previous_catalog_page.clicked.connect(self._show_previous_catalog_page)
        self._next_catalog_page.clicked.connect(self._show_next_catalog_page)
        self._translate_catalog_entry.clicked.connect(
            self._translate_selected_catalog_entry
        )
        self._search_catalog_id.clicked.connect(self._search_catalog_entry_by_id)
        self._retranslate_catalog_id.clicked.connect(
            self._retranslate_catalog_entry_by_id
        )
        self._clear_contaminated_cache.clicked.connect(
            self._clear_contaminated_catalog_cache
        )
        self._show_batch_errors.clicked.connect(self._show_last_batch_errors)
        self._translate_catalog.clicked.connect(self._start_bulk_catalog_translation)
        self._pause_catalog_translation.clicked.connect(
            self._pause_bulk_catalog_translation
        )
        self._resume_catalog_translation.clicked.connect(
            self._resume_bulk_catalog_translation
        )
        self._cancel_catalog_translation.clicked.connect(
            self._cancel_bulk_catalog_translation
        )
        self._preview_capture.clicked.connect(self._capture_preview_image)
        self._save.clicked.connect(self._save_profile)
        self._show_overlay.clicked.connect(self._start_overlay_adjustment)
        self._save_overlay.clicked.connect(self._save_overlay_placement)
        self._reprocess_runtime_text.clicked.connect(
            self._reprocess_current_runtime_text
        )
        self._pause.clicked.connect(self._pause_loop)
        self._resume.clicked.connect(self._resume_loop)
        self._quit.clicked.connect(self._widget.close)
        self._widget.closeEvent = self._close_event
        for widget in (
            self._x,
            self._y,
            self._width,
            self._height,
            self._overlay_x,
            self._overlay_y,
            self._overlay_width,
            self._overlay_height,
        ):
            widget.valueChanged.connect(self._refresh_overlap_warning)

        self._load_active_profile()
        self._load_overlay_placement()
        self._load_mode_settings()
        self._refresh_catalog_page()
        self._refresh_mode_controls()

    def show(self) -> None:
        self._widget.show()

    def refresh_capture_status(self) -> None:
        if self._mode_settings.get_active_mode() == OperationMode.RPG_MAKER_MV_MZ:
            self._capture_status.setText("Captura: desativada no modo RPG Maker MV/MZ")
            return

        error_message = self._capture_loop.last_error_message
        if error_message:
            self._capture_status.setText(f"Captura: erro - {error_message}")
        elif self._capture_loop.is_paused:
            self._capture_status.setText("Captura: pausada")
        elif self._capture_loop.is_busy:
            self._capture_status.setText("Captura: processando frame")
        else:
            self._capture_status.setText("Captura: rodando")

    def refresh_pipeline_status(self) -> None:
        if self._mode_settings.get_active_mode() == OperationMode.RPG_MAKER_MV_MZ:
            self._refresh_runtime_status()
            return

        diagnostic = self._pipeline_diagnostics.last_diagnostic
        if diagnostic:
            self._pipeline_status.setText(f"Pipeline: {diagnostic}")
        else:
            self._pipeline_status.setText("Pipeline: aguardando")

        timing_summary = self._pipeline_diagnostics.last_timing_summary
        if timing_summary:
            self._pipeline_timing.setText(f"Tempo: {timing_summary}")
        else:
            self._pipeline_timing.setText("Tempo: aguardando")
        self._runtime_source.setText("Fonte MV/MZ: aguardando")
        self._runtime_translation.setText("Traducao MV/MZ: aguardando")

    def _refresh_runtime_status(self) -> None:
        if self._runtime_diagnostics is None:
            self._pipeline_status.setText("Pipeline: runtime MV/MZ indisponivel")
            self._pipeline_timing.setText("Tempo: aguardando")
            return

        diagnostic = self._runtime_diagnostics.last_diagnostic
        if diagnostic:
            self._pipeline_status.setText(f"Pipeline: {diagnostic}")
        else:
            self._pipeline_status.setText("Pipeline: aguardando runtime MV/MZ")

        timing_summary = self._runtime_diagnostics.last_timing_summary
        if timing_summary:
            self._pipeline_timing.setText(f"Tempo: {timing_summary}")
        else:
            self._pipeline_timing.setText("Tempo: aguardando")

        source_text = self._runtime_diagnostics.last_source_text
        self._runtime_source.setText(
            f"Fonte MV/MZ: {self._short_debug_text(source_text)}"
        )
        translated_text = self._runtime_diagnostics.last_translated_text
        self._runtime_translation.setText(
            f"Traducao MV/MZ: {self._short_debug_text(translated_text)}"
        )

    def _build_mode_tab(self, form_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        form = form_cls()
        form.addRow("Fluxo ativo", self._mode)
        buttons = hbox_cls()
        buttons.addWidget(self._save_mode)

        rpg_form = form_cls()
        rpg_form.addRow("Pasta do jogo", self._rpg_maker_path)
        rpg_buttons = hbox_cls()
        rpg_buttons.addWidget(self._choose_rpg_maker_path)
        rpg_buttons.addWidget(self._import_rpg_maker)

        tab.addLayout(form)
        tab.addWidget(self._mode_status)
        tab.addLayout(buttons)
        tab.addWidget(self._group("Projeto RPG Maker MV/MZ", rpg_form, rpg_buttons))
        return self._wrap(tab)

    def _build_catalog_tab(self, group_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        catalog_group = group_cls("Catalogo MV/MZ")
        catalog_layout = vbox_cls()
        catalog_buttons = hbox_cls()
        catalog_buttons.addWidget(self._refresh_catalog)
        catalog_buttons.addWidget(self._previous_catalog_page)
        catalog_buttons.addWidget(self._next_catalog_page)
        catalog_buttons.addWidget(self._translate_catalog_entry)
        catalog_layout.addWidget(self._catalog_table)
        catalog_layout.addLayout(catalog_buttons)
        catalog_group.setLayout(catalog_layout)

        maintenance_group = group_cls("Busca e manutencao")
        maintenance_layout = vbox_cls()
        id_lookup = hbox_cls()
        id_lookup.addWidget(self._catalog_id)
        id_lookup.addWidget(self._search_catalog_id)
        id_lookup.addWidget(self._retranslate_catalog_id)
        maintenance_buttons = hbox_cls()
        maintenance_buttons.addWidget(self._clear_contaminated_cache)
        maintenance_buttons.addWidget(self._show_batch_errors)
        maintenance_layout.addLayout(id_lookup)
        maintenance_layout.addWidget(self._catalog_cache_status)
        maintenance_layout.addLayout(maintenance_buttons)
        maintenance_group.setLayout(maintenance_layout)

        bulk_group = group_cls("Traducao em lote")
        bulk_layout = vbox_cls()
        type_filters = hbox_cls()
        for checkbox in self._bulk_type_checkboxes.values():
            type_filters.addWidget(checkbox)
        bulk_buttons = hbox_cls()
        bulk_buttons.addWidget(self._bulk_limit)
        bulk_buttons.addWidget(self._translate_catalog)
        bulk_buttons.addWidget(self._pause_catalog_translation)
        bulk_buttons.addWidget(self._resume_catalog_translation)
        bulk_buttons.addWidget(self._cancel_catalog_translation)
        bulk_layout.addLayout(type_filters)
        bulk_layout.addWidget(self._bulk_progress)
        bulk_layout.addWidget(self._bulk_status)
        bulk_layout.addLayout(bulk_buttons)
        bulk_group.setLayout(bulk_layout)

        tab.addWidget(catalog_group)
        tab.addWidget(maintenance_group)
        tab.addWidget(bulk_group)
        return self._wrap(tab)

    def _build_capture_tab(self, form_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        capture_group = self._group("Captura Universal / OCR")
        form = form_cls()
        form.addRow("Perfil", self._name)
        form.addRow("X", self._x)
        form.addRow("Y", self._y)
        form.addRow("Largura", self._width)
        form.addRow("Altura", self._height)
        buttons = hbox_cls()
        buttons.addWidget(self._select_region)
        buttons.addWidget(self._preview_capture)
        buttons.addWidget(self._save)
        capture_layout = vbox_cls()
        capture_layout.addLayout(form)
        capture_layout.addWidget(self._preview)
        capture_layout.addLayout(buttons)
        capture_group.setLayout(capture_layout)
        tab.addWidget(capture_group)
        return self._wrap(tab)

    def _build_overlay_tab(self, form_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        overlay_group = self._group("Overlay compartilhado")
        form = form_cls()
        form.addRow("X", self._overlay_x)
        form.addRow("Y", self._overlay_y)
        form.addRow("Largura", self._overlay_width)
        form.addRow("Altura", self._overlay_height)
        form.addRow("Fonte", self._overlay_font_size)
        form.addRow("Opacidade", self._overlay_opacity)
        buttons = hbox_cls()
        buttons.addWidget(self._show_overlay)
        buttons.addWidget(self._save_overlay)
        overlay_layout = vbox_cls()
        overlay_layout.addLayout(form)
        overlay_layout.addLayout(buttons)
        overlay_group.setLayout(overlay_layout)
        tab.addWidget(overlay_group)
        return self._wrap(tab)

    def _build_run_tab(self, group_cls, hbox_cls, vbox_cls):
        tab = vbox_cls()
        status_group = group_cls("Status do fluxo ativo")
        status_layout = vbox_cls()
        status_layout.addWidget(self._capture_status)
        status_layout.addWidget(self._pipeline_status)
        status_layout.addWidget(self._pipeline_timing)
        status_layout.addWidget(self._runtime_source)
        status_layout.addWidget(self._runtime_translation)
        status_group.setLayout(status_layout)
        buttons = hbox_cls()
        buttons.addWidget(self._pause)
        buttons.addWidget(self._resume)
        buttons.addWidget(self._reprocess_runtime_text)
        buttons.addWidget(self._quit)
        tab.addWidget(status_group)
        tab.addWidget(self._group("Acoes", buttons))
        return self._wrap(tab)

    def _group(self, title: str, *layouts):
        from PySide6.QtWidgets import QGroupBox, QVBoxLayout

        group = QGroupBox(title)
        if layouts:
            group_layout = QVBoxLayout()
            for layout in layouts:
                group_layout.addLayout(layout)
            group.setLayout(group_layout)
        return group

    def _wrap(self, layout):
        from PySide6.QtWidgets import QWidget

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _spinbox(self, minimum: int, maximum: int):
        from PySide6.QtWidgets import QSpinBox

        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)
        return spinbox

    def _capture_preview_image(self) -> bool:
        try:
            path = self._capture_preview.capture_preview(
                x=self._x.value(),
                y=self._y.value(),
                width=self._width.value(),
                height=self._height.value(),
            )
        except Exception as error:
            self._status.setText(f"Preview falhou: {error}")
            return False

        self._show_preview(path)
        self._status.setText(f"Preview atualizado: {path}")
        return True

    def _choose_rpg_maker_folder(self) -> None:
        selected_path = self._file_dialog.getExistingDirectory(
            self._widget,
            "Selecionar pasta RPG Maker MV/MZ",
            self._rpg_maker_path.text(),
        )
        if selected_path:
            self._rpg_maker_path.setText(selected_path)

    def _save_mode_settings(self) -> None:
        mode = self._selected_mode()
        self._mode_settings.set_active_mode(mode)
        if self._rpg_maker_path.text().strip():
            self._mode_settings.set_rpg_maker_project_path(self._rpg_maker_path.text())

        if mode == OperationMode.RPG_MAKER_MV_MZ:
            self._capture_loop.pause()
            self._status.setText("Modo RPG Maker MV/MZ salvo.")
        else:
            self._capture_loop.resume()
            self._status.setText("Modo Universal salvo.")
        self._refresh_mode_status()
        self.refresh_capture_status()
        self._refresh_overlap_warning()
        self._refresh_mode_controls()
        self._refresh_catalog_page()

    def _import_rpg_maker_catalog(self) -> bool:
        try:
            result = self._mode_settings.import_rpg_maker_project(
                self._rpg_maker_path.text()
            )
        except Exception as error:
            self._status.setText(f"Importacao MV/MZ falhou: {error}")
            self._refresh_mode_status()
            return False

        self._mode_settings.set_active_mode(OperationMode.RPG_MAKER_MV_MZ)
        self._mode.setCurrentIndex(
            self._mode.findData(OperationMode.RPG_MAKER_MV_MZ.value)
        )
        self._capture_loop.pause()
        self._status.setText(
            "Catalogo MV/MZ importado: "
            f"{result.imported_count} textos de {result.project.data_path}"
        )
        self._refresh_mode_status(result)
        self._refresh_catalog_page()
        self.refresh_capture_status()
        self._refresh_overlap_warning()
        self._refresh_mode_controls()
        return True

    def _refresh_catalog_page(self) -> None:
        if self._mode_settings.get_active_mode() != OperationMode.RPG_MAKER_MV_MZ:
            self._catalog_offset = 0
            self._catalog_total = 0
            self._catalog_table.setRowCount(0)
            self._catalog_cache_status.setText(
                "Cache MV/MZ: ativo apenas no modo RPG Maker MV/MZ."
            )
            self._bulk_status.setText(
                "Lote MV/MZ: ativo apenas no modo RPG Maker MV/MZ."
            )
            self._refresh_mode_controls()
            return

        self._catalog_offset = 0
        self._load_catalog_entries()

    def _show_previous_catalog_page(self) -> None:
        self._catalog_offset = max(0, self._catalog_offset - self._catalog_page_size)
        self._load_catalog_entries()

    def _show_next_catalog_page(self) -> None:
        next_offset = self._catalog_offset + self._catalog_page_size
        if next_offset >= self._catalog_total:
            return
        self._catalog_offset = next_offset
        self._load_catalog_entries()

    def _load_catalog_entries(self) -> None:
        if self._mode_settings.get_active_mode() != OperationMode.RPG_MAKER_MV_MZ:
            self._refresh_catalog_page()
            return

        try:
            total = self._mode_settings.count_rpg_maker_entries()
            if total and self._catalog_offset >= total:
                self._catalog_offset = max(
                    0,
                    ((total - 1) // self._catalog_page_size) * self._catalog_page_size,
                )
            entries = self._mode_settings.list_rpg_maker_entries(
                limit=self._catalog_page_size,
                offset=self._catalog_offset,
            )
        except Exception as error:
            self._status.setText(f"Catalogo MV/MZ indisponivel: {error}")
            self._catalog_table.setRowCount(0)
            self._catalog_total = 0
            self._update_catalog_page_buttons()
            return

        self._catalog_total = total
        self._populate_catalog_table(entries)
        if total == 0:
            self._status.setText("Catalogo carregado: 0 textos.")
        else:
            start = self._catalog_offset + 1
            end = self._catalog_offset + len(entries)
            self._status.setText(f"Catalogo: {start}-{end} de {total} textos.")
        self._refresh_catalog_cache_status(total)
        self._update_catalog_page_buttons()

    def _populate_catalog_table(self, entries: list[RpgMakerTextEntry]) -> None:
        self._catalog_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            origin_item = self._table_item(self._format_origin(entry))
            type_item = self._table_item(entry.text_type.value)
            text_item = self._table_item(entry.source_text)
            id_item = self._table_item(str(entry.id or ""))
            self._catalog_table.setItem(row, 0, origin_item)
            self._catalog_table.setItem(row, 1, type_item)
            self._catalog_table.setItem(row, 2, text_item)
            self._catalog_table.setItem(row, 3, id_item)

        self._catalog_table.resizeColumnsToContents()

    def _update_catalog_page_buttons(self) -> None:
        self._refresh_mode_controls()

    def _translate_selected_catalog_entry(self) -> bool:
        selected_rows = self._catalog_table.selectionModel().selectedRows()
        if not selected_rows:
            self._status.setText("Selecione uma linha do catalogo.")
            return False

        row = selected_rows[0].row()
        id_item = self._catalog_table.item(row, 3)
        if id_item is None or not id_item.text().strip():
            self._status.setText("Entrada do catalogo sem ID persistido.")
            return False

        try:
            result = self._mode_settings.translate_catalog_entry(int(id_item.text()))
        except Exception as error:
            self._status.setText(f"Traducao do catalogo falhou: {error}")
            return False

        if result is None:
            self._status.setText("Entrada do catalogo nao encontrada.")
            return False

        self._overlay.show_text(result.translated_text)
        self._status.setText(f"Traduzido: {result.translated_text}")
        self._refresh_catalog_cache_status()
        return True

    def _search_catalog_entry_by_id(self) -> bool:
        entry_id = self._catalog_entry_id_from_field()
        if entry_id is None:
            return False

        try:
            entry = self._mode_settings.get_rpg_maker_entry(entry_id)
        except Exception as error:
            self._status.setText(f"Busca no catalogo falhou: {error}")
            return False

        if entry is None:
            self._populate_catalog_table([])
            self._status.setText("Entrada do catalogo nao encontrada.")
            return False

        self._populate_catalog_table([entry])
        self._previous_catalog_page.setEnabled(False)
        self._next_catalog_page.setEnabled(False)
        self._status.setText(f"Entrada do catalogo encontrada: ID {entry_id}.")
        return True

    def _retranslate_catalog_entry_by_id(self) -> bool:
        entry_id = self._catalog_entry_id_from_field()
        if entry_id is None:
            return False

        try:
            result = self._mode_settings.retranslate_catalog_entry(entry_id)
        except Exception as error:
            self._status.setText(f"Retraducao do catalogo falhou: {error}")
            return False

        if result is None:
            self._status.setText("Entrada do catalogo nao encontrada.")
            return False

        self._overlay.show_text(result.translated_text)
        self._status.setText(f"Retraduzido ID {entry_id}: {result.translated_text}")
        self._refresh_catalog_cache_status(self._catalog_total or None)
        return True

    def _catalog_entry_id_from_field(self) -> int | None:
        raw_value = self._catalog_id.text().strip()
        if not raw_value:
            self._status.setText("Informe um ID do catalogo.")
            return None

        try:
            entry_id = int(raw_value)
        except ValueError:
            self._status.setText("ID do catalogo deve ser um numero.")
            return None

        if entry_id <= 0:
            self._status.setText("ID do catalogo deve ser maior que zero.")
            return None

        return entry_id

    def _clear_contaminated_catalog_cache(self) -> bool:
        try:
            deleted = self._mode_settings.clear_contaminated_catalog_cache()
        except Exception as error:
            self._status.setText(f"Limpeza de cache falhou: {error}")
            return False

        self._refresh_catalog_cache_status()
        self._status.setText(f"Cache contaminado limpo: {deleted} traducoes removidas.")
        return True

    def _start_bulk_catalog_translation(self) -> bool:
        if self._bulk_thread is not None and self._bulk_thread.is_alive():
            self._status.setText("Traducao em lote ja esta rodando.")
            return False

        limit = self._selected_bulk_limit()
        text_types = self._selected_bulk_text_types()
        if not text_types:
            self._status.setText("Selecione ao menos um tipo de texto para o lote.")
            return False

        self._clear_bulk_queues()
        self._bulk_cancel_requested = False
        self._bulk_pause_requested = False
        self._bulk_pause_event.set()
        self._bulk_progress.setRange(0, 0)
        self._bulk_status.setText("Lote: iniciando...")

        self._bulk_thread = Thread(
            target=self._run_bulk_catalog_translation,
            args=(limit, text_types),
            daemon=True,
        )
        self._bulk_thread.start()
        self._bulk_timer.start()
        self._refresh_mode_controls()
        return True

    def _pause_bulk_catalog_translation(self) -> None:
        self._bulk_pause_requested = True
        self._bulk_pause_event.clear()
        self._pause_catalog_translation.setEnabled(False)
        self._resume_catalog_translation.setEnabled(True)
        self._bulk_status.setText("Lote: pausando apos a entrada atual...")
        self._refresh_mode_controls()

    def _resume_bulk_catalog_translation(self) -> None:
        self._bulk_pause_requested = False
        self._bulk_pause_event.set()
        self._pause_catalog_translation.setEnabled(True)
        self._resume_catalog_translation.setEnabled(False)
        self._bulk_status.setText("Lote: retomando...")
        self._refresh_mode_controls()

    def _cancel_bulk_catalog_translation(self) -> None:
        self._bulk_cancel_requested = True
        self._bulk_pause_requested = False
        self._bulk_pause_event.set()
        self._bulk_status.setText("Lote: cancelando...")
        self._refresh_mode_controls()

    def _run_bulk_catalog_translation(
        self,
        limit: int | None,
        text_types: set[RpgMakerTextType],
    ) -> None:
        try:
            result = self._mode_settings.translate_catalog_entries(
                limit=limit,
                text_types=text_types,
                on_progress=self._bulk_progress_queue.put,
                should_cancel=lambda: self._bulk_cancel_requested,
                should_pause=lambda: self._bulk_pause_requested,
                wait_if_paused=self._bulk_pause_event.wait,
            )
        except Exception as error:
            self._bulk_result_queue.put(error)
            return

        self._bulk_result_queue.put(result)

    def _poll_bulk_translation(self) -> None:
        while True:
            try:
                progress = self._bulk_progress_queue.get_nowait()
            except Empty:
                break
            self._apply_bulk_progress(progress)

        try:
            result = self._bulk_result_queue.get_nowait()
        except Empty:
            return

        self._finish_bulk_translation(result)

    def _apply_bulk_progress(self, progress: CatalogTranslationProgress) -> None:
        if progress.total > 0:
            self._bulk_progress.setRange(0, progress.total)
            self._bulk_progress.setValue(progress.processed)
        else:
            self._bulk_progress.setRange(0, 1)
            self._bulk_progress.setValue(0)

        self._bulk_status.setText(
            "Lote: "
            f"{progress.processed}/{progress.total} processados | "
            f"{progress.translated} traduzidos | "
            f"{progress.cache_hits} cache hits | "
            f"{progress.errors} erros | "
            f"tempo {self._format_seconds(progress.elapsed_seconds)}"
        )
        if progress.paused:
            self._bulk_status.setText(
                "Lote pausado: "
                f"{progress.processed}/{progress.total} processados | "
                f"{progress.translated} traduzidos | "
                f"{progress.cache_hits} cache hits | "
                f"{progress.errors} erros"
            )

    def _finish_bulk_translation(
        self,
        result: CatalogTranslationResult | Exception,
    ) -> None:
        self._bulk_timer.stop()
        self._bulk_thread = None
        self._bulk_pause_requested = False
        self._bulk_pause_event.set()
        self._refresh_mode_controls()

        if isinstance(result, Exception):
            self._bulk_progress.setRange(0, 1)
            self._bulk_progress.setValue(0)
            self._bulk_status.setText(f"Lote: falhou - {result}")
            self._status.setText(f"Traducao em lote falhou: {result}")
            return

        if result.total > 0:
            self._bulk_progress.setRange(0, result.total)
            self._bulk_progress.setValue(result.processed)
        else:
            self._bulk_progress.setRange(0, 1)
            self._bulk_progress.setValue(0)

        status = "cancelado" if result.cancelled else "concluido"
        message = (
            f"Lote {status}: {result.processed}/{result.total} processados | "
            f"{result.translated} traduzidos | "
            f"{result.cache_hits} cache hits | "
            f"{result.errors} erros | "
            f"tempo {self._format_seconds(result.elapsed_seconds)} | "
            f"media traducao {self._format_seconds(result.average_translation_seconds)}"
        )
        self._bulk_status.setText(message)
        self._status.setText(message)
        self._refresh_catalog_cache_status()

    def _selected_bulk_limit(self) -> int | None:
        value = int(self._bulk_limit.currentData())
        if value == 0:
            return None
        return value

    def _selected_bulk_text_types(self) -> set[RpgMakerTextType]:
        return {
            text_type
            for text_type, checkbox in self._bulk_type_checkboxes.items()
            if checkbox.isChecked()
        }

    def _format_seconds(self, seconds: float) -> str:
        return f"{seconds:.2f}s"

    def _short_debug_text(self, text: str | None, limit: int = 220) -> str:
        if text is None or not text.strip():
            return "aguardando"
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit]}..."

    def _clear_bulk_queues(self) -> None:
        while True:
            try:
                self._bulk_progress_queue.get_nowait()
            except Empty:
                break
        while True:
            try:
                self._bulk_result_queue.get_nowait()
            except Empty:
                break

    def _refresh_catalog_cache_status(self, total: int | None = None) -> None:
        try:
            resolved_total = (
                self._mode_settings.count_rpg_maker_entries()
                if total is None
                else total
            )
            cached = self._mode_settings.count_cached_catalog_entries()
        except Exception as error:
            self._catalog_cache_status.setText(f"Cache: indisponivel - {error}")
            return

        self._catalog_cache_status.setText(
            f"Cache: {cached}/{resolved_total} entradas ja traduzidas"
        )

    def _show_last_batch_errors(self) -> None:
        from PySide6.QtWidgets import QDialog, QPushButton, QTableWidget, QVBoxLayout

        try:
            errors = self._mode_settings.list_last_batch_errors()
        except Exception as error:
            self._status.setText(f"Consulta de erros falhou: {error}")
            return

        dialog = QDialog(self._widget)
        dialog.setWindowTitle("Erros do ultimo lote")
        dialog.resize(900, 420)

        table = QTableWidget(len(errors), 4)
        table.setHorizontalHeaderLabels(("ID", "Origem", "Texto fonte", "Erro"))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().hide()
        for row, error in enumerate(errors):
            table.setItem(row, 0, self._table_item(str(error.entry_id or "")))
            table.setItem(row, 1, self._table_item(error.origin))
            table.setItem(row, 2, self._table_item(error.source_text))
            table.setItem(row, 3, self._table_item(error.error_message))
        table.resizeColumnsToContents()

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout = QVBoxLayout()
        layout.addWidget(table)
        layout.addWidget(close_button)
        dialog.setLayout(layout)
        self._status.setText(f"Erros do ultimo lote: {len(errors)}.")
        dialog.exec()

    def _table_item(self, text: str):
        from PySide6.QtWidgets import QTableWidgetItem

        return QTableWidgetItem(text)

    def _format_origin(self, entry: RpgMakerTextEntry) -> str:
        origin = entry.origin
        parts = [origin.file_name]
        if origin.event_id is not None:
            parts.append(f"ev {origin.event_id}")
        if origin.page_index is not None:
            parts.append(f"pg {origin.page_index}")
        if origin.command_index is not None:
            parts.append(f"cmd {origin.command_index}")
        return " | ".join(parts)

    def _select_region_on_screen(self) -> None:
        from live_translator.ui.region_selector_window import RegionSelectorWindow

        self._status.setText("Arraste a caixa de texto do jogo. ESC cancela.")
        self._region_selector = RegionSelectorWindow(self._apply_selected_region)
        self._region_selector.show()

    def _apply_selected_region(self, region: TextRegion) -> None:
        self._x.setValue(region.x)
        self._y.setValue(region.y)
        self._width.setValue(region.width)
        self._height.setValue(region.height)
        self._status.setText(
            "Area selecionada: "
            f"x={region.x} y={region.y} {region.width}x{region.height}"
        )
        self._refresh_overlap_warning()
        self._capture_preview_image()

    def _start_overlay_adjustment(self) -> None:
        placement = self._placement_from_fields()
        self._overlay.apply_placement(placement)
        self._overlay.show_calibration_text()
        self._overlay.set_edit_mode(True, self._sync_overlay_fields)
        self._status.setText(
            "Arraste o overlay para mover. Arraste bordas ou cantos para redimensionar."
        )

    def _save_overlay_placement(self) -> None:
        placement = self._overlay.current_placement()
        self._overlay.set_edit_mode(False)
        self._overlay_settings.save_placement(placement)
        self._sync_overlay_fields(placement)
        self._refresh_overlap_warning()
        self._status.setText("Overlay salvo.")

    def _sync_overlay_fields(self, placement: OverlayPlacement) -> None:
        widgets = (
            self._overlay_x,
            self._overlay_y,
            self._overlay_width,
            self._overlay_height,
            self._overlay_font_size,
            self._overlay_opacity,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self._overlay_x.setValue(placement.x)
        self._overlay_y.setValue(placement.y)
        self._overlay_width.setValue(placement.width)
        self._overlay_height.setValue(placement.height)
        self._overlay_font_size.setValue(placement.font_size)
        self._overlay_opacity.setValue(placement.opacity)
        for widget in widgets:
            widget.blockSignals(False)
        self._refresh_overlap_warning()

    def _text_region_from_fields(self) -> TextRegion:
        return TextRegion(
            x=self._x.value(),
            y=self._y.value(),
            width=self._width.value(),
            height=self._height.value(),
        )

    def _placement_from_fields(self) -> OverlayPlacement:
        return OverlayPlacement(
            x=self._overlay_x.value(),
            y=self._overlay_y.value(),
            width=self._overlay_width.value(),
            height=self._overlay_height.value(),
            opacity=self._overlay_opacity.value(),
            font_size=self._overlay_font_size.value(),
        )

    def _refresh_overlap_warning(self, *_unused: object) -> None:
        if self._mode_settings.get_active_mode() == OperationMode.RPG_MAKER_MV_MZ:
            self._overlap_warning.hide()
            return

        try:
            region = self._text_region_from_fields()
            placement = self._placement_from_fields()
        except ValueError:
            self._overlap_warning.hide()
            return

        if rectangles_overlap(region, placement):
            self._overlap_warning.setText(
                "O overlay esta sobre a area capturada. "
                "Isso pode fazer o OCR ler a traducao em vez do texto do jogo."
            )
            self._overlap_warning.show()
            return

        self._overlap_warning.hide()

    def _show_preview(self, path: Path) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImageReader, QPixmap

        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            self._preview.setText(f"Preview salvo, mas nao foi possivel abrir: {path}")
            return

        pixmap = QPixmap.fromImage(image)
        scaled = pixmap.scaled(
            460,
            170,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def _load_active_profile(self) -> None:
        profile = self._profile_settings.get_active_profile()
        if profile is None:
            self._name.setText("Default Lower Screen")
            self._x.setValue(256)
            self._y.setValue(950)
            self._width.setValue(2048)
            self._height.setValue(360)
            self._status.setText("Selecione a area do texto ou ajuste os numeros.")
            self._refresh_overlap_warning()
            return

        self._name.setText(profile.name)
        self._x.setValue(profile.text_region.x)
        self._y.setValue(profile.text_region.y)
        self._width.setValue(profile.text_region.width)
        self._height.setValue(profile.text_region.height)
        self._refresh_overlap_warning()

    def _load_overlay_placement(self) -> None:
        placement = self._overlay_settings.get_placement()
        self._overlay.apply_placement(placement)
        self._sync_overlay_fields(placement)
        self._refresh_overlap_warning()

    def _load_mode_settings(self) -> None:
        mode = self._mode_settings.get_active_mode()
        mode_index = self._mode.findData(mode.value)
        if mode_index >= 0:
            self._mode.setCurrentIndex(mode_index)

        project_path = self._mode_settings.get_rpg_maker_project_path()
        if project_path is not None:
            self._rpg_maker_path.setText(str(project_path))
        self._refresh_mode_status()

    def _selected_mode(self) -> OperationMode:
        return OperationMode(self._mode.currentData())

    def _refresh_mode_controls(self, *_unused: object) -> None:
        state = resolve_mode_control_state(
            active_mode=self._mode_settings.get_active_mode(),
            selected_mode=self._selected_mode(),
            catalog_has_previous=self._catalog_offset > 0,
            catalog_has_next=(
                self._catalog_offset + self._catalog_page_size < self._catalog_total
            ),
            bulk_running=self._bulk_is_running(),
            bulk_paused=self._bulk_pause_requested,
            runtime_available=self._runtime_diagnostics is not None,
        )

        for widget in (
            self._rpg_maker_path,
            self._choose_rpg_maker_path,
            self._import_rpg_maker,
        ):
            widget.setEnabled(state.rpg_maker_setup_enabled)

        for widget in (
            self._name,
            self._x,
            self._y,
            self._width,
            self._height,
            self._select_region,
            self._preview_capture,
            self._save,
        ):
            widget.setEnabled(state.universal_capture_enabled)

        for widget in (
            self._catalog_table,
            self._refresh_catalog,
            self._catalog_id,
            self._search_catalog_id,
            self._clear_contaminated_cache,
            self._show_batch_errors,
            self._bulk_limit,
        ):
            widget.setEnabled(state.rpg_catalog_enabled)

        for checkbox in self._bulk_type_checkboxes.values():
            checkbox.setEnabled(state.rpg_catalog_enabled)

        self._previous_catalog_page.setEnabled(state.catalog_previous_enabled)
        self._next_catalog_page.setEnabled(state.catalog_next_enabled)
        self._translate_catalog_entry.setEnabled(state.rpg_catalog_mutation_enabled)
        self._retranslate_catalog_id.setEnabled(state.rpg_catalog_mutation_enabled)
        self._translate_catalog.setEnabled(state.bulk_start_enabled)
        self._pause_catalog_translation.setEnabled(state.bulk_pause_enabled)
        self._resume_catalog_translation.setEnabled(state.bulk_resume_enabled)
        self._cancel_catalog_translation.setEnabled(state.bulk_cancel_enabled)
        self._pause.setEnabled(state.universal_run_enabled)
        self._resume.setEnabled(state.universal_run_enabled)
        self._reprocess_runtime_text.setEnabled(state.runtime_reprocess_enabled)

    def _bulk_is_running(self) -> bool:
        return self._bulk_thread is not None and self._bulk_thread.is_alive()

    def _refresh_mode_status(
        self,
        import_result: RpgMakerImportResult | None = None,
    ) -> None:
        mode = self._mode_settings.get_active_mode()
        if mode == OperationMode.UNIVERSAL:
            self._mode_status.setText(
                "Modo: Universal. Usa captura de tela, OCR/vision, cache e overlay."
            )
            return

        project_path = self._mode_settings.get_rpg_maker_project_path()
        if import_result is not None:
            self._mode_status.setText(
                "Modo: RPG Maker MV/MZ. "
                f"{import_result.imported_count} textos importados de "
                f"{import_result.project.version.value}."
            )
            return

        if project_path is None:
            self._mode_status.setText(
                "Modo: RPG Maker MV/MZ. Selecione a pasta do jogo e importe o catalogo."
            )
            return

        self._mode_status.setText(
            "Modo: RPG Maker MV/MZ. "
            f"Pasta configurada: {project_path}. "
            f"Bridge: {self._settings.rpg_maker_bridge_endpoint}."
        )

    def _save_profile(self) -> None:
        try:
            profile = self._profile_settings.save_profile(
                name=self._name.text(),
                window_title="Manual Region",
                x=self._x.value(),
                y=self._y.value(),
                width=self._width.value(),
                height=self._height.value(),
            )
        except ValueError as error:
            self._status.setText(f"Area invalida: {error}")
            return

        self._status.setText(
            "Area salva: "
            f"x={profile.text_region.x} y={profile.text_region.y} "
            f"{profile.text_region.width}x{profile.text_region.height}"
        )
        self._refresh_overlap_warning()

    def _pause_loop(self) -> None:
        self._capture_loop.pause()
        self.refresh_capture_status()

    def _resume_loop(self) -> None:
        self._capture_loop.resume()
        self.refresh_capture_status()

    def _reprocess_current_runtime_text(self) -> bool:
        if self._runtime_diagnostics is None:
            self._status.setText("Runtime MV/MZ indisponivel.")
            return False

        try:
            result = self._runtime_diagnostics.reprocess_last_text()
        except Exception as error:
            self._status.setText(f"Reprocessamento falhou: {error}")
            self.refresh_pipeline_status()
            return False

        self.refresh_pipeline_status()
        if result is None:
            self._status.setText("Nenhuma fala MV/MZ atual para reprocessar.")
            return False

        self._status.setText("Fala MV/MZ retraduzida e cache atualizado.")
        self._refresh_catalog_cache_status()
        return True

    def _close_event(self, event) -> None:
        from PySide6.QtWidgets import QApplication

        self._capture_loop.pause()
        self._overlay.set_edit_mode(False)
        QApplication.quit()
        event.accept()
