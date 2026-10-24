"""Documentation stays true: every route is documented, every internal link resolves."""

import importlib.util
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
DOCS = sorted([ROOT / "README.md", *(ROOT / "docs").glob("*.md")])


def _generator():
    spec = importlib.util.spec_from_file_location("generate_api_docs", ROOT / "scripts" / "generate_api_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _routes():
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and not route.path.startswith(("/docs", "/openapi", "/redoc"))
        for method in route.methods - {"HEAD", "OPTIONS"}
    }


def test_every_route_has_a_curated_description_and_none_is_stale():
    described = set(_generator().DESCRIPTIONS)
    assert _routes() - described == set(), "route(s) missing from scripts/generate_api_docs.py DESCRIPTIONS"
    assert described - _routes() == set(), "DESCRIPTIONS mentions route(s) that no longer exist"


def test_the_generated_reference_lists_every_route():
    reference = (ROOT / "docs" / "api-reference.md").read_text()
    for _method, path in _routes():
        assert f"`{path}`" in reference, f"{path} missing from docs/api-reference.md - re-run scripts/generate_api_docs.py"
    assert f"**{len(_routes())} HTTP routes + 1 WebSocket.**" in reference


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_point_at_real_files(doc):
    broken = []
    for target in re.findall(r"\]\(([^)\s]+)\)", doc.read_text()):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = target.split("#")[0]
        if path and not (doc.parent / path).resolve().exists():
            broken.append(target)
    assert broken == [], f"{doc.name} links to missing files: {broken}"


def test_the_docs_the_readme_promises_exist():
    for name in ("architecture", "ai-analyst", "ml-and-datasets", "demo-script", "troubleshooting", "api-reference"):
        assert (ROOT / "docs" / f"{name}.md").exists(), name
