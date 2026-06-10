"""Guard-rails de arquitetura (ver ARCHITECTURE.md, secao 2).

Estes testes falham quando as regras de dependencia entre camadas sao
violadas, antes de o problema chegar a runtime ou a review manual.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "live_translator"

FORBIDDEN_IN_DOMAIN = frozenset({"PySide6", "mss", "sqlite3", "requests", "PIL"})
FORBIDDEN_DOMAIN_INTERNAL_PREFIXES = (
    "live_translator.application",
    "live_translator.infrastructure",
    "live_translator.ui",
)
DESKTOP_MODULES = frozenset({"PySide6", "mss"})
DESKTOP_ALLOWED_DIRS = (
    SRC_ROOT / "ui",
    SRC_ROOT / "infrastructure" / "capture",
)


def _collect_imports(
    tree: ast.AST,
    *,
    include_function_bodies: bool,
) -> list[str]:
    """Retorna nomes de modulos importados na arvore.

    Com include_function_bodies=False, considera apenas imports executados na
    importacao do modulo (topo, classes, try/if de modulo), ignorando corpos de
    funcao — que e onde os imports lazy de desktop sao permitidos.
    """
    imports: list[str] = []
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if not include_function_bodies and isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
            ):
                continue
            if isinstance(child, ast.Import):
                imports.extend(alias.name for alias in child.names)
            elif isinstance(child, ast.ImportFrom):
                if child.level == 0 and child.module:
                    imports.append(child.module)
            else:
                stack.append(child)
    return imports


def _top_level_name(module: str) -> str:
    return module.split(".", 1)[0]


def _python_files(root: Path) -> list[Path]:
    files = sorted(root.rglob("*.py"))
    assert files, f"nenhum arquivo Python encontrado em {root}"
    return files


def test_domain_does_not_import_external_or_upper_layers() -> None:
    violations: list[str] = []
    for path in _python_files(SRC_ROOT / "domain"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _collect_imports(tree, include_function_bodies=True):
            relative = path.relative_to(SRC_ROOT)
            if _top_level_name(module) in FORBIDDEN_IN_DOMAIN:
                violations.append(f"{relative}: import proibido '{module}'")
            if module.startswith(FORBIDDEN_DOMAIN_INTERNAL_PREFIXES):
                violations.append(
                    f"{relative}: domain importando camada superior '{module}'"
                )
    assert violations == []


def test_infrastructure_does_not_import_application_or_ui() -> None:
    violations: list[str] = []
    for path in _python_files(SRC_ROOT / "infrastructure"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _collect_imports(tree, include_function_bodies=True):
            if module.startswith(("live_translator.application", "live_translator.ui")):
                violations.append(
                    f"{path.relative_to(SRC_ROOT)}: infraestrutura importando "
                    f"camada superior '{module}'"
                )
    assert violations == []


def test_desktop_imports_only_at_module_level_in_ui_and_capture() -> None:
    violations: list[str] = []
    for path in _python_files(SRC_ROOT):
        if any(path.is_relative_to(allowed) for allowed in DESKTOP_ALLOWED_DIRS):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for module in _collect_imports(tree, include_function_bodies=False):
            if _top_level_name(module) in DESKTOP_MODULES:
                violations.append(
                    f"{path.relative_to(SRC_ROOT)}: import de desktop no topo "
                    f"do modulo '{module}' (use import lazy dentro de funcao)"
                )
    assert violations == []
