from __future__ import annotations

from dataclasses import dataclass

from live_translator.domain.models import OperationMode


@dataclass(frozen=True)
class ModeControlState:
    rpg_maker_setup_enabled: bool
    universal_capture_enabled: bool
    universal_run_enabled: bool
    rpg_catalog_enabled: bool
    rpg_catalog_mutation_enabled: bool
    catalog_previous_enabled: bool
    catalog_next_enabled: bool
    bulk_start_enabled: bool
    bulk_pause_enabled: bool
    bulk_resume_enabled: bool
    bulk_cancel_enabled: bool
    runtime_reprocess_enabled: bool


def resolve_mode_control_state(
    *,
    active_mode: OperationMode,
    selected_mode: OperationMode | None = None,
    catalog_has_previous: bool = False,
    catalog_has_next: bool = False,
    bulk_running: bool = False,
    bulk_paused: bool = False,
    runtime_available: bool = False,
) -> ModeControlState:
    selected_mode = selected_mode or active_mode
    universal_active = active_mode == OperationMode.UNIVERSAL
    rpg_maker_active = active_mode == OperationMode.RPG_MAKER_MV_MZ
    rpg_maker_selected = selected_mode == OperationMode.RPG_MAKER_MV_MZ

    rpg_catalog_enabled = rpg_maker_active
    rpg_catalog_mutation_enabled = rpg_maker_active and not bulk_running

    return ModeControlState(
        rpg_maker_setup_enabled=rpg_maker_active or rpg_maker_selected,
        universal_capture_enabled=universal_active,
        universal_run_enabled=universal_active,
        rpg_catalog_enabled=rpg_catalog_enabled,
        rpg_catalog_mutation_enabled=rpg_catalog_mutation_enabled,
        catalog_previous_enabled=rpg_catalog_enabled and catalog_has_previous,
        catalog_next_enabled=rpg_catalog_enabled and catalog_has_next,
        bulk_start_enabled=rpg_catalog_mutation_enabled,
        bulk_pause_enabled=rpg_maker_active and bulk_running and not bulk_paused,
        bulk_resume_enabled=rpg_maker_active and bulk_running and bulk_paused,
        bulk_cancel_enabled=rpg_maker_active and bulk_running,
        runtime_reprocess_enabled=rpg_maker_active and runtime_available,
    )
