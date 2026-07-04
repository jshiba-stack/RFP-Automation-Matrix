"""Tests for storewrite: comment-preserving appends to YAML/JSON stores.

All data here is fictional placeholder (public repo).
"""

import json

import pytest
import yaml

from proposal import storewrite

COMMENTED_STORE = """\
# Example store (fictional).
firm:
  legal_name: "Acme Consulting"   # trailing comment

# IV. Capacity / Project Listing.
projects:
  - id: acme-web
    client: "Example City"
    project: "Web Portal"
    start_year: 2020
    end: "ongoing"

# III. Past Performance.
past_performance:
  - id: pp-example
    client: "Example City Department of Records"

# V. Additional Criteria.
additional_criteria: ""
"""


def _write(tmp_path, text, name="store.yaml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_append_preserves_comments_and_existing_content(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    rid = storewrite.append_record(
        p, "projects",
        {"client": "Example Utility Co", "project": "Data Mart", "start_year": 2022,
         "end": "ongoing"},
    )
    text = p.read_text(encoding="utf-8")
    # every original comment survives
    for comment in ("# Example store (fictional).", "# trailing comment",
                    "# IV. Capacity / Project Listing.", "# III. Past Performance.",
                    "# V. Additional Criteria."):
        assert comment in text
    data = yaml.safe_load(text)
    ids = [r["id"] for r in data["projects"]]
    assert ids == ["acme-web", rid]
    # the new item lands inside the projects block, before past_performance
    assert text.index("Example Utility Co") < text.index("past_performance:")
    # other sections untouched
    assert data["firm"]["legal_name"] == "Acme Consulting"
    assert data["past_performance"][0]["id"] == "pp-example"


def test_append_past_performance_with_multiline_scope(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    scope = "Line one of scope\nLine two: details, punctuation & symbols"
    rid = storewrite.append_record(
        p, "past_performance",
        {"client": "Example Hospital", "project": "Reporting", "scope": scope},
        id_prefix="pp",
    )
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    rec = next(r for r in data["past_performance"] if r["id"] == rid)
    assert rec["scope"] == scope
    assert rid.startswith("pp-")


def test_append_creates_missing_key_and_missing_file(tmp_path):
    # key absent from an existing file
    p = _write(tmp_path, "firm:\n  legal_name: Acme\n")
    storewrite.append_record(p, "projects", {"client": "A", "project": "B"})
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["projects"][0]["client"] == "A"

    # file doesn't exist at all
    p2 = tmp_path / "new_store.yaml"
    storewrite.append_record(p2, "past_performance", {"client": "C", "project": "D"})
    data2 = yaml.safe_load(p2.read_text(encoding="utf-8"))
    assert data2["past_performance"][0]["client"] == "C"


def test_append_opens_inline_empty_list(tmp_path):
    p = _write(tmp_path, "projects: []\nother: 1\n")
    storewrite.append_record(p, "projects", {"client": "A", "project": "B"})
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["projects"][0]["client"] == "A"
    assert data["other"] == 1


def test_append_rejects_non_list_key(tmp_path):
    p = _write(tmp_path, "projects: not-a-list\n")
    with pytest.raises(ValueError):
        storewrite.append_record(p, "projects", {"client": "A", "project": "B"})
    assert p.read_text(encoding="utf-8") == "projects: not-a-list\n"  # untouched


def test_id_uniqueness(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    rec = {"client": "Same Client", "project": "Same Project"}
    r1 = storewrite.append_record(p, "projects", dict(rec))
    r2 = storewrite.append_record(p, "projects", dict(rec))
    assert r1 != r2
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert len({r["id"] for r in data["projects"]}) == len(data["projects"])


def test_json_store_roundtrip(tmp_path):
    p = tmp_path / "store.json"
    p.write_text(json.dumps({"firm": {"legal_name": "Acme"}}), encoding="utf-8")
    rid = storewrite.append_record(p, "projects", {"client": "A", "project": "B"})
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["projects"][0]["id"] == rid
    assert data["firm"]["legal_name"] == "Acme"


def test_rejects_unknown_extension(tmp_path):
    with pytest.raises(ValueError):
        storewrite.append_record(tmp_path / "store.txt", "projects", {"client": "A"})


def test_update_merges_fields_and_preserves_comments(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    merged = storewrite.update_record(p, "projects", "acme-web",
                                      {"project": "Web Portal v2", "end": 2025})
    assert merged["client"] == "Example City"        # untouched field survives
    text = p.read_text(encoding="utf-8")
    assert "# IV. Capacity / Project Listing." in text
    assert "# III. Past Performance." in text
    data = yaml.safe_load(text)
    rec = data["projects"][0]
    assert rec["project"] == "Web Portal v2" and rec["end"] == 2025
    assert rec["start_year"] == 2020


def test_update_missing_id_raises_and_leaves_file(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    before = p.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        storewrite.update_record(p, "projects", "nope", {"client": "X"})
    assert p.read_text(encoding="utf-8") == before


def test_delete_middle_and_last_record(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    storewrite.append_record(p, "projects", {"client": "B", "project": "P2"})
    storewrite.delete_record(p, "projects", "acme-web")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert [r["client"] for r in data["projects"]] == ["B"]
    # deleting the last one leaves an explicit empty list, not `key:` -> None
    rid = data["projects"][0]["id"]
    storewrite.delete_record(p, "projects", rid)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["projects"] == []
    # comments elsewhere still intact
    assert "# III. Past Performance." in p.read_text(encoding="utf-8")


def test_move_up_down_and_edges(tmp_path):
    p = _write(tmp_path, COMMENTED_STORE)
    storewrite.append_record(p, "projects", {"id": "b", "client": "B", "project": "P"})
    storewrite.append_record(p, "projects", {"id": "c", "client": "C", "project": "P"})

    def ids():
        return [r["id"] for r in yaml.safe_load(p.read_text(encoding="utf-8"))["projects"]]

    assert ids() == ["acme-web", "b", "c"]
    storewrite.move_record(p, "projects", "c", -1)
    assert ids() == ["acme-web", "c", "b"]
    storewrite.move_record(p, "projects", "acme-web", 1)
    assert ids() == ["c", "acme-web", "b"]
    storewrite.move_record(p, "projects", "c", -1)      # already on top: no-op
    assert ids() == ["c", "acme-web", "b"]


def test_json_update_delete_move(tmp_path):
    p = tmp_path / "store.json"
    p.write_text(json.dumps({"projects": [
        {"id": "a", "client": "A", "project": "P"},
        {"id": "b", "client": "B", "project": "P"},
    ]}), encoding="utf-8")
    storewrite.update_record(p, "projects", "a", {"client": "A2"})
    storewrite.move_record(p, "projects", "b", -1)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert [r["id"] for r in data["projects"]] == ["b", "a"]
    assert data["projects"][1]["client"] == "A2"
    storewrite.delete_record(p, "projects", "b")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert [r["id"] for r in data["projects"]] == ["a"]


def test_read_records_tolerates_bad_files(tmp_path):
    assert storewrite.read_records(tmp_path / "missing.yaml", "projects") == []
    bad = tmp_path / "bad.yaml"
    bad.write_text("::: not yaml {{{", encoding="utf-8")
    assert storewrite.read_records(bad, "projects") == []
