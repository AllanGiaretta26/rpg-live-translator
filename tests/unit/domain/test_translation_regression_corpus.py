"""Corpus de regressao de qualidade de traducao.

Roda os pares fonte/traducao de tests/data/translation_regression_corpus.json
contra invalid_translation_reason: pares 'valid' (traducoes boas, no formato
real do jogo) nao podem virar falso positivo; pares 'invalid' precisam ser
rejeitados pela regra esperada. Permite validar mudancas de prompt e de
heuristicas sem rodar o jogo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from live_translator.domain.models import RpgMakerTextType
from live_translator.domain.translation_quality import invalid_translation_reason

# parents[2] = tests/ (este arquivo vive em tests/unit/domain/).
_CORPUS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "translation_regression_corpus.json"
)


def _load_corpus() -> dict:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def _case_id(case: dict) -> str:
    return f"{case['text_type']}:{case['source_text'][:40]}"


_CORPUS = _load_corpus()


@pytest.mark.parametrize("case", _CORPUS["valid"], ids=_case_id)
def test_valid_pairs_are_not_rejected(case: dict):
    reason = invalid_translation_reason(
        case["source_text"],
        case["translated_text"],
        text_type=RpgMakerTextType(case["text_type"]),
    )

    assert reason is None, (
        f"traducao boa rejeitada por '{reason}': {case['translated_text']!r}"
    )


@pytest.mark.parametrize("case", _CORPUS["invalid"], ids=_case_id)
def test_invalid_pairs_are_rejected_by_expected_rule(case: dict):
    reason = invalid_translation_reason(
        case["source_text"],
        case["translated_text"],
        text_type=RpgMakerTextType(case["text_type"]),
    )

    assert reason == case["expected_rule"]
