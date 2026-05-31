from live_translator.domain.models import OperationMode
from live_translator.ui.mode_control_state import resolve_mode_control_state


def test_universal_mode_enables_capture_and_disables_mvz_catalog_controls():
    state = resolve_mode_control_state(
        active_mode=OperationMode.UNIVERSAL,
        selected_mode=OperationMode.UNIVERSAL,
        catalog_has_previous=True,
        catalog_has_next=True,
        runtime_available=True,
    )

    assert state.universal_capture_enabled is True
    assert state.universal_run_enabled is True
    assert state.rpg_catalog_enabled is False
    assert state.catalog_previous_enabled is False
    assert state.catalog_next_enabled is False
    assert state.bulk_start_enabled is False
    assert state.runtime_reprocess_enabled is False


def test_rpg_maker_mode_enables_catalog_and_disables_capture_controls():
    state = resolve_mode_control_state(
        active_mode=OperationMode.RPG_MAKER_MV_MZ,
        selected_mode=OperationMode.RPG_MAKER_MV_MZ,
        catalog_has_previous=True,
        catalog_has_next=True,
        runtime_available=True,
    )

    assert state.rpg_maker_setup_enabled is True
    assert state.rpg_catalog_enabled is True
    assert state.rpg_catalog_mutation_enabled is True
    assert state.catalog_previous_enabled is True
    assert state.catalog_next_enabled is True
    assert state.universal_capture_enabled is False
    assert state.universal_run_enabled is False
    assert state.runtime_reprocess_enabled is True


def test_selecting_rpg_maker_while_universal_active_only_enables_project_setup():
    state = resolve_mode_control_state(
        active_mode=OperationMode.UNIVERSAL,
        selected_mode=OperationMode.RPG_MAKER_MV_MZ,
    )

    assert state.rpg_maker_setup_enabled is True
    assert state.universal_capture_enabled is True
    assert state.rpg_catalog_enabled is False
    assert state.bulk_start_enabled is False


def test_running_batch_limits_catalog_mutations_to_pause_resume_cancel():
    running = resolve_mode_control_state(
        active_mode=OperationMode.RPG_MAKER_MV_MZ,
        selected_mode=OperationMode.RPG_MAKER_MV_MZ,
        bulk_running=True,
        bulk_paused=False,
    )

    assert running.rpg_catalog_mutation_enabled is False
    assert running.bulk_start_enabled is False
    assert running.bulk_pause_enabled is True
    assert running.bulk_resume_enabled is False
    assert running.bulk_cancel_enabled is True

    paused = resolve_mode_control_state(
        active_mode=OperationMode.RPG_MAKER_MV_MZ,
        selected_mode=OperationMode.RPG_MAKER_MV_MZ,
        bulk_running=True,
        bulk_paused=True,
    )

    assert paused.bulk_pause_enabled is False
    assert paused.bulk_resume_enabled is True
    assert paused.bulk_cancel_enabled is True
