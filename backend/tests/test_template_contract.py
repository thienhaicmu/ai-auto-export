"""
Template contract tests.

Verifies that all shipped templates pass the static validator, and that
deliberately broken templates produce the expected violations.
"""
import pytest
from pathlib import Path

from app.renderer.template_validator import (
    validate_template,
    validate_all_templates,
    TemplateValidationResult,
)

# Path to the real templates directory
_TEMPLATES_DIR = Path(__file__).parent.parent / "app" / "templates"


# ── Real template checks ──────────────────────────────────────────────────────

def test_viral_template_passes_contract():
    """The shipped viral template must satisfy all contract requirements."""
    result = validate_template(_TEMPLATES_DIR / "viral")
    assert result.ok, result.summary


def test_all_shipped_templates_pass():
    """Every template in the templates directory must pass."""
    results = validate_all_templates(_TEMPLATES_DIR)
    assert results, "No templates found — check templates directory path"
    failures = [r for r in results if not r.ok]
    assert not failures, "\n".join(r.summary for r in failures)


# ── Violation detection tests (using tmp_path fixtures) ──────────────────────

def test_missing_files_detected(tmp_path: Path):
    """A template directory with no files should report missing file violations."""
    template_dir = tmp_path / "empty_template"
    template_dir.mkdir()
    result = validate_template(template_dir)
    assert not result.ok
    checks = {v.check for v in result.violations}
    assert "required_files" in checks


def test_missing_scene_ready_detected(tmp_path: Path):
    """A scene.js without __SCENE_READY__ = true should be flagged."""
    template_dir = tmp_path / "bad_template"
    template_dir.mkdir()
    (template_dir / "index.html").write_text("<html></html>")
    (template_dir / "style.css").write_text("body {}")
    # Missing window.__SCENE_READY__ = true
    (template_dir / "scene.js").write_text(
        "var scene = window.__SCENE__ || {};"  # has __SCENE__ but not SCENE_READY
    )
    result = validate_template(template_dir)
    assert not result.ok
    msgs = [v.message for v in result.violations]
    assert any("__SCENE_READY__" in m for m in msgs)


def test_settimeout_detected(tmp_path: Path):
    """setTimeout usage in scene.js should be flagged."""
    template_dir = tmp_path / "timeout_template"
    template_dir.mkdir()
    (template_dir / "index.html").write_text("<html></html>")
    (template_dir / "style.css").write_text("body {}")
    (template_dir / "scene.js").write_text(
        "var scene = window.__SCENE__ || {};\n"
        "window.__SCENE_READY__ = true;\n"
        "setTimeout(function() {}, 500);\n"
    )
    result = validate_template(template_dir)
    assert not result.ok
    msgs = [v.message for v in result.violations]
    assert any("setTimeout" in m for m in msgs)


def test_setinterval_detected(tmp_path: Path):
    """setInterval usage in scene.js should be flagged."""
    template_dir = tmp_path / "interval_template"
    template_dir.mkdir()
    (template_dir / "index.html").write_text("<html></html>")
    (template_dir / "style.css").write_text("body {}")
    (template_dir / "scene.js").write_text(
        "var scene = window.__SCENE__ || {};\n"
        "window.__SCENE_READY__ = true;\n"
        "setInterval(function() {}, 100);\n"
    )
    result = validate_template(template_dir)
    assert not result.ok
    msgs = [v.message for v in result.violations]
    assert any("setInterval" in m for m in msgs)


def test_external_fetch_detected(tmp_path: Path):
    """fetch() calls in scene.js should be flagged."""
    template_dir = tmp_path / "fetch_template"
    template_dir.mkdir()
    (template_dir / "index.html").write_text("<html></html>")
    (template_dir / "style.css").write_text("body {}")
    (template_dir / "scene.js").write_text(
        "var scene = window.__SCENE__ || {};\n"
        "window.__SCENE_READY__ = true;\n"
        "fetch('https://api.example.com/data').then(r => r.json());\n"
    )
    result = validate_template(template_dir)
    assert not result.ok
    msgs = [v.message for v in result.violations]
    assert any("fetch" in m or "external" in m for m in msgs)


def test_valid_minimal_template_passes(tmp_path: Path):
    """A minimal but fully compliant template should pass all checks."""
    template_dir = tmp_path / "minimal_template"
    template_dir.mkdir()
    (template_dir / "index.html").write_text("<html><body><script src='scene.js'></script></body></html>")
    (template_dir / "style.css").write_text("body { margin: 0; }")
    (template_dir / "scene.js").write_text(
        "(function() {\n"
        "  var scene = window.__SCENE__ || {};\n"
        "  document.fonts.ready.then(function() {\n"
        "    window.__SCENE_READY__ = true;\n"
        "  });\n"
        "})();\n"
    )
    result = validate_template(template_dir)
    assert result.ok, result.summary
