from __future__ import annotations

from pathlib import Path

from live_translator.domain.interfaces import RpgMakerProjectDetector
from live_translator.domain.models import RpgMakerProject, RpgMakerVersion


class RpgMakerProjectDetectionError(ValueError):
    """Raised when a folder is not a readable RPG Maker MV/MZ project."""


class FileSystemRpgMakerProjectDetector(RpgMakerProjectDetector):
    def detect(self, path: str | Path) -> RpgMakerProject:
        candidate = Path(path).expanduser().resolve()
        data_path = self._find_data_path(candidate)
        if data_path is None:
            raise RpgMakerProjectDetectionError(
                "pasta MV/MZ invalida: data ou www/data nao encontrado"
            )

        missing_files = [
            name
            for name in ("System.json", "MapInfos.json", "CommonEvents.json")
            if not (data_path / name).is_file()
        ]
        if missing_files:
            joined = ", ".join(missing_files)
            raise RpgMakerProjectDetectionError(
                f"pasta MV/MZ invalida: arquivos ausentes em data: {joined}"
            )

        root_path = data_path.parent
        if data_path.name == "data" and root_path.name == "www":
            root_path = root_path.parent

        return RpgMakerProject(
            root_path=root_path,
            data_path=data_path,
            version=self._detect_version(root_path),
        )

    def _find_data_path(self, path: Path) -> Path | None:
        candidates = []
        if path.name == "data":
            candidates.append(path)
        candidates.extend((path / "www" / "data", path / "data"))

        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return None

    def _detect_version(self, root_path: Path) -> RpgMakerVersion:
        js_paths = (root_path / "www" / "js", root_path / "js")
        for js_path in js_paths:
            if (js_path / "rmmz_core.js").is_file():
                return RpgMakerVersion.MZ
            if (js_path / "rpg_core.js").is_file():
                return RpgMakerVersion.MV
        return RpgMakerVersion.MV_MZ
