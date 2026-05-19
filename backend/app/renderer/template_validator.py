"""
Static template contract validator.

Checks every template in backend/app/templates/<style>/ to ensure it satisfies
the render pipeline contract WITHOUT running a browser:

  Required files:
    index.html, style.css, scene.js

  scene.js must:
    - reference window.__SCENE__
    - set window.__SCENE_READY__ = true

  scene.js must NOT:
    - use setTimeout  (use CSS @keyframes instead — Playwright steps currentTime)
    - use setInterval
    - call fetch()
    - use XMLHttpRequest
    - hardcode external http(s):// URLs (local server http://local/ is allowed)

Run standalone:  python -m app.renderer.template_validator
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

_THIS_DIR     = Path(__file__).parent            # backend/app/renderer/
_APP_DIR      = _THIS_DIR.parent                 # backend/app/
_TEMPLATES_DIR = _APP_DIR / "templates"


# ── Contract rules ────────────────────────────────────────────────────────────

_REQUIRED_FILES = ["index.html", "style.css", "scene.js"]

# Patterns that MUST appear in scene.js (check, human-readable message)
_MUST_CONTAIN: list[tuple[str, str]] = [
    (r"window\.__SCENE__",             "scene.js must reference window.__SCENE__"),
    (r"window\.__SCENE_READY__\s*=\s*true",
                                       "scene.js must set window.__SCENE_READY__ = true"),
]

# Patterns that must NOT appear in scene.js
_MUST_NOT_CONTAIN: list[tuple[str, str]] = [
    (r"\bsetTimeout\s*\(",             "scene.js must not use setTimeout (use CSS @keyframes)"),
    (r"\bsetInterval\s*\(",            "scene.js must not use setInterval (use CSS @keyframes)"),
    (r"\bfetch\s*\(",                  "scene.js must not call fetch()"),
    (r"\bXMLHttpRequest\b",            "scene.js must not use XMLHttpRequest"),
    # External URLs: https?:// but NOT the local server prefix http://local
    (r"https?://(?!local[/'\"\s])",    "scene.js must not hardcode external http(s) URLs"),
]


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class TemplateViolation:
    check: str
    message: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.message}"


@dataclass
class TemplateValidationResult:
    template: str
    path: Path
    violations: list[TemplateViolation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0

    @property
    def summary(self) -> str:
        if self.ok:
            return f"Template '{self.template}': OK"
        msgs = "; ".join(str(v) for v in self.violations)
        return f"Template '{self.template}': FAILED — {msgs}"


# ── Core logic ────────────────────────────────────────────────────────────────

def validate_template(template_dir: Path) -> TemplateValidationResult:
    """Validate a single template directory against the render contract."""
    result = TemplateValidationResult(template=template_dir.name, path=template_dir)

    # 1. Required files
    for fname in _REQUIRED_FILES:
        if not (template_dir / fname).exists():
            result.violations.append(TemplateViolation(
                check="required_files",
                message=f"Missing required file: {fname}",
            ))

    # 2. scene.js content checks (only if the file exists)
    scene_js = template_dir / "scene.js"
    if scene_js.exists():
        src = scene_js.read_text(encoding="utf-8")
        for pattern, msg in _MUST_CONTAIN:
            if not re.search(pattern, src):
                result.violations.append(TemplateViolation(check="must_contain", message=msg))
        for pattern, msg in _MUST_NOT_CONTAIN:
            if re.search(pattern, src):
                result.violations.append(TemplateViolation(check="must_not_contain", message=msg))

    return result


def validate_all_templates(
    templates_dir: Path | None = None,
) -> list[TemplateValidationResult]:
    """
    Validate every *implemented* subdirectory of templates_dir.

    A directory is considered an implemented template only when it contains
    at least one of the required files (index.html / style.css / scene.js).
    Stub directories (e.g. cinematic/ with only a README.md) are silently
    skipped — they are future placeholders, not templates.
    """
    base = templates_dir or _TEMPLATES_DIR
    results: list[TemplateValidationResult] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        # Only validate directories that look like implemented templates
        if not any((child / f).exists() for f in _REQUIRED_FILES):
            continue
        results.append(validate_template(child))
    return results


def assert_all_templates_valid(templates_dir: Path | None = None) -> None:
    """Raise RuntimeError if any template fails validation. Call on startup."""
    results = validate_all_templates(templates_dir)
    failures = [r for r in results if not r.ok]
    if failures:
        lines = [r.summary for r in failures]
        raise RuntimeError(
            "Template contract violations detected:\n" + "\n".join(lines)
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = validate_all_templates()
    if not results:
        print("No templates found in", _TEMPLATES_DIR)
        sys.exit(1)

    any_fail = False
    for r in results:
        print(r.summary)
        if not r.ok:
            any_fail = True

    sys.exit(1 if any_fail else 0)
