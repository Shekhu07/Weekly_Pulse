"""Guard rails for the project layout.

Fails when files land outside their designated subfolders, so clutter is
caught by the test suite instead of accumulating. See CLAUDE.md for the
layout rules. If a new file legitimately belongs somewhere unusual, add it
to the relevant whitelist below.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories that are not part of the source tree
IGNORED_DIRS = {".git", "venv", ".venv", "data", "__pycache__", ".pytest_cache"}

ALLOWED_ROOT_FILES = {
    "api.py",
    "CLAUDE.md",
    "Dockerfile",
    "README.md",
    "requirements.txt",
    "mcp_config.json",
    "script.md",
}

ALLOWED_ROOT_DIRS = IGNORED_DIRS | {
    "pulse",
    "config",
    "docs",
    "scripts",
    "static",
    "tests",
}


def _visible(entries):
    return [e for e in entries if not e.name.startswith(".")]


def test_root_has_no_stray_files():
    stray = [
        e.name
        for e in _visible(ROOT.iterdir())
        if e.is_file() and e.name not in ALLOWED_ROOT_FILES
    ]
    assert not stray, f"Unexpected files at project root: {stray}"


def test_root_has_no_unknown_dirs():
    unknown = [
        e.name
        for e in _visible(ROOT.iterdir())
        if e.is_dir() and e.name not in ALLOWED_ROOT_DIRS
    ]
    assert not unknown, f"Unexpected directories at project root: {unknown}"


def test_pulse_contains_only_python():
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "pulse").rglob("*")
        if p.is_file()
        and p.suffix not in {".py", ".pyc"}
        and "__pycache__" not in p.parts
        and not p.name.startswith(".")
    ]
    assert not offenders, f"Non-Python files in pulse/: {offenders}"


def test_pulse_submodules_have_init():
    missing = [
        str(d.relative_to(ROOT))
        for d in (ROOT / "pulse").rglob("*")
        if d.is_dir()
        and d.name != "__pycache__"
        and not (d / "__init__.py").exists()
    ]
    assert not missing, f"pulse/ submodules missing __init__.py: {missing}"


def test_tests_follow_naming_convention():
    offenders = [
        p.name
        for p in (ROOT / "tests").glob("*.py")
        if not (p.name.startswith("test_") or p.name in {"conftest.py", "__init__.py"})
    ]
    assert not offenders, f"Non-test Python files in tests/: {offenders}"


def test_config_contains_only_config_files():
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "config").rglob("*")
        if p.is_file()
        and p.suffix not in {".yaml", ".yml", ".example"}
        and not p.name.startswith(".")
    ]
    assert not offenders, f"Non-config files in config/: {offenders}"


def test_static_contains_only_web_assets():
    allowed = {".html", ".css", ".js", ".svg", ".png", ".ico", ".webp", ".woff2"}
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "static").rglob("*")
        if p.is_file() and p.suffix not in allowed and not p.name.startswith(".")
    ]
    assert not offenders, f"Non-web-asset files in static/: {offenders}"


def test_docs_contains_only_markdown_and_text():
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "docs").rglob("*")
        if p.is_file()
        and p.suffix not in {".md", ".txt"}
        and not p.name.startswith(".")
    ]
    assert not offenders, f"Unexpected files in docs/: {offenders}"
