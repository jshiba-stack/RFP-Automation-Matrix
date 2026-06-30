"""Tests for materials-folder discovery (the dashboard's auto-detection)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import discovery  # noqa: E402

REFS = ROOT / "assets/refs"
pytestmark = pytest.mark.skipif(not REFS.exists(), reason="reference materials not available")


def test_classify_docx():
    assert discovery.classify_docx("Acme ... (FINAL).docx") == "final"
    assert discovery.classify_docx("x (SIGNED).pdf") == "signed"
    assert discovery.classify_docx("y (DRAFT) 2027.docx") == "draft"
    assert discovery.classify_docx("base_template.docx") == "template"
    assert discovery.classify_docx("RY Master copy.docx") == "master"
    assert discovery.classify_docx("something.docx") == "other"


def test_scan_finds_docx_and_orders_final_first():
    found = discovery.scan_folder(str(REFS))
    assert found["error"] is None
    names = [d["name"] for d in found["docx"]]
    assert any("FINAL" in n for n in names)
    # signed/final come before draft/other
    kinds = [d["kind"] for d in found["docx"]]
    assert kinds == sorted(kinds, key=lambda k: discovery._KIND_ORDER.get(k, 9))


def test_scan_excludes_instance_and_output():
    found = discovery.scan_folder(str(ROOT))
    store_names = [s["name"] for s in found["stores"]]
    assert "config.json" not in store_names               # instance/ excluded
    assert all("_DRAFT_" not in d["name"] for d in found["docx"])  # data/output excluded


def test_scan_finds_yaml_stores():
    found = discovery.scan_folder(str(ROOT))
    assert any(s["name"].endswith((".yaml", ".yml")) for s in found["stores"])


def test_list_dir_navigates():
    d = discovery.list_dir(str(ROOT))
    assert d["error"] is None
    names = [f["name"] for f in d["folders"]]
    assert "assets" in names and "proposal" in names
    assert d["parent"]  # has a parent to go up to


def test_scan_bad_folder_reports_error():
    found = discovery.scan_folder(str(ROOT / "does-not-exist"))
    assert found["error"] and not found["docx"]


def test_detect_sources_returns_list_of_dicts():
    out = discovery.detect_sources()
    assert isinstance(out, list)
    for s in out:
        assert {"kind", "name", "path"} <= set(s)
        assert Path(s["path"]).is_dir()  # only existing folders suggested


def test_active_workspace_none_without_sources():
    from proposal import config
    assert config.active_workspace_path({"sources": [], "active_source": ""}) is None
    cfg = {"sources": [{"name": "X", "path": str(REFS)}], "active_source": "X"}
    assert config.active_workspace_path(cfg) == REFS


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
