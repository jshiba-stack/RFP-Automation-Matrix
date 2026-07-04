"""Append records to a data-store file without disturbing the rest of it.

The store YAMLs are hand-curated (comments, ordering, spacing), so a naive
``yaml.safe_load`` + ``safe_dump`` round-trip would destroy them. Instead we
edit at the *text* level: locate the top-level list key (``projects`` /
``past_performance``), find where its block ends, and splice the new item in --
leaving every other byte of the file untouched. The result is re-parsed before
writing; if it doesn't round-trip, nothing is written.

JSON stores have no comments, so those are load/append/dump.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

YAML_EXTS = {".yaml", ".yml"}
STORE_EXTS = YAML_EXTS | {".json"}

# A top-level YAML key line, e.g. `projects:` or `projects: []`
_KEY_LINE = r"^(?P<key>[A-Za-z_][\w-]*)\s*:\s*(?P<rest>.*?)\s*$"


def slugify(*parts: str, max_len: int = 48) -> str:
    txt = "-".join(p for p in parts if p)
    slug = re.sub(r"[^a-z0-9]+", "-", txt.lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0] or slug[:max_len]
    return slug or "entry"


def _load_data(path: Path) -> dict:
    if not path.exists():
        return {}
    if path.suffix.lower() in YAML_EXTS:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8") or "{}")


def read_records(path, key: str) -> list[dict]:
    """The dict records under ``key`` at ``path`` ([] on any problem)."""
    p = Path(path)
    if p.suffix.lower() not in STORE_EXTS:
        return []
    try:
        recs = _load_data(p).get(key) or []
    except Exception:  # noqa: BLE001 - unreadable store -> just no records
        return []
    return [r for r in recs if isinstance(r, dict)]


def existing_ids(path: Path, key: str) -> set[str]:
    """All record ids under ``key`` in the store at ``path`` (empty if absent)."""
    out = set()
    for rec in read_records(path, key):
        if rec.get("id") is not None:
            out.add(str(rec["id"]))
    return out


def unique_id(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _render_item(record: dict, indent: str) -> str:
    """Render ``record`` as a YAML list item at the given indent."""
    body = yaml.safe_dump(
        record, sort_keys=False, allow_unicode=True, width=100000,
        default_flow_style=False,
    ).rstrip("\n")
    lines = body.split("\n")
    out = [f"{indent}- {lines[0]}"]
    pad = indent + "  "
    out.extend(f"{pad}{ln}" for ln in lines[1:])
    return "\n".join(out) + "\n"


def _find_block(lines: list[str], key: str):
    """Return (key_line_index, insert_index, item_indent) for ``key``'s list block.

    ``insert_index`` is the line index where a new item belongs (after the last
    existing item, before any trailing blank/comment lines that lead into the
    next top-level key). Returns None if the key is not in the file.
    """
    key_i = None
    for i, ln in enumerate(lines):
        m = re.match(_KEY_LINE, ln)
        if m and m.group("key") == key:
            key_i = i
            break
    if key_i is None:
        return None

    # Where does the block end? At the next top-level key (col-0 `word:`).
    end = len(lines)
    for j in range(key_i + 1, len(lines)):
        if re.match(_KEY_LINE, lines[j]):
            end = j
            break

    # Walk back over trailing blanks/comments (they belong to the NEXT key).
    insert = end
    while insert > key_i + 1 and (
        not lines[insert - 1].strip() or lines[insert - 1].lstrip().startswith("#")
    ):
        insert -= 1

    # Item indent: copy the existing items' indentation if any.
    indent = "  "
    for j in range(key_i + 1, insert):
        m = re.match(r"^(\s*)- ", lines[j])
        if m:
            indent = m.group(1)
    return key_i, insert, indent


def append_record(path, key: str, record: dict, *, id_prefix: str = "") -> str:
    """Append ``record`` to the top-level list ``key`` in the store at ``path``.

    Generates a unique ``id`` if the record has none. Preserves the file's
    existing text (comments included) for YAML; creates the file if missing.
    Returns the record id. Raises ``ValueError`` if the store is not a
    YAML/JSON file or the edited text fails to re-parse (nothing written).
    """
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in STORE_EXTS:
        raise ValueError(f"Not a YAML/JSON data store: {path.name}")

    if not record.get("id"):
        base = slugify(id_prefix, str(record.get("client", "")), str(record.get("project", "")))
        record = {"id": unique_id(base, existing_ids(path, key)), **record}
    rid = str(record["id"])

    if ext == ".json":
        data = json.loads(path.read_text(encoding="utf-8") or "{}") if path.exists() else {}
        data.setdefault(key, []).append(record)
        _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return rid

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.split("\n")
    found = _find_block(lines, key)

    if found is None:
        if text and not text.endswith("\n"):
            text += "\n"
        sep = "\n" if text.strip() else ""
        new_text = text + f"{sep}{key}:\n" + _render_item(record, "  ")
    else:
        key_i, insert, indent = found
        m = re.match(_KEY_LINE, lines[key_i])
        rest = m.group("rest")
        if rest and not rest.startswith("#"):
            if rest.split("#")[0].strip() in ("[]", ""):
                # `key: []` (possibly with a comment) -> open the block form
                lines[key_i] = f"{key}:"
            else:
                raise ValueError(f"'{key}' in {path.name} is not a list block")
        item = _render_item(record, indent).rstrip("\n")
        lines.insert(insert, item)
        new_text = "\n".join(lines)

    # Never write something that doesn't parse back with the record present.
    data = yaml.safe_load(new_text)
    recs = (data or {}).get(key) or []
    if not any(isinstance(r, dict) and str(r.get("id")) == rid for r in recs):
        raise ValueError(f"internal error: edited store failed round-trip for '{key}'")

    _atomic_write(path, new_text)
    return rid


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# --- edit / delete / reorder existing records --------------------------------

def _item_spans(lines: list[str], key_i: int, end: int, indent: str):
    """(start, end) line spans of each ``- ...`` item inside a located block."""
    spans = []
    dash = f"{indent}- "
    start = None
    for j in range(key_i + 1, end):
        if lines[j].startswith(dash):
            if start is not None:
                spans.append((start, j))
            start = j
    if start is not None:
        spans.append((start, end))
    return spans


def _locate(path: Path, key: str, rid: str):
    """Return (lines, key_i, spans, idx, records, indent) for record ``rid``.

    Raises ``ValueError`` when the record can't be located safely (missing, or
    the text layout doesn't line up with the parsed records -- e.g. flow-style
    lists, which are better edited by hand).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    found = _find_block(lines, key)
    if found is None:
        raise ValueError(f"'{key}' not found in {path.name}")
    key_i, end, indent = found
    spans = _item_spans(lines, key_i, end, indent)
    records = read_records(path, key)
    if len(spans) != len(records):
        raise ValueError(f"'{key}' in {path.name} has a layout this tool can't "
                         "edit safely -- edit the file by hand")
    idx = next((i for i, r in enumerate(records) if str(r.get("id")) == str(rid)), None)
    if idx is None:
        raise ValueError(f"no '{key}' record with id '{rid}' in {path.name}")
    return lines, key_i, spans, idx, records, indent


def _validate_and_write(path: Path, key: str, lines: list[str], check) -> None:
    new_text = "\n".join(lines)
    data = yaml.safe_load(new_text)
    recs = (data or {}).get(key)
    recs = recs if isinstance(recs, list) else []
    if not check([r for r in recs if isinstance(r, dict)]):
        raise ValueError(f"internal error: edited store failed round-trip for '{key}'")
    _atomic_write(path, new_text)


def update_record(path, key: str, rid: str, fields: dict) -> dict:
    """Merge ``fields`` into the record ``rid`` (its other fields survive).

    Returns the merged record. Text outside the record is left untouched.
    """
    path = Path(path)
    rid = str(rid)
    if path.suffix.lower() == ".json":
        data = _load_data(path)
        for i, r in enumerate(data.get(key) or []):
            if isinstance(r, dict) and str(r.get("id")) == rid:
                merged = {**r, **fields, "id": r.get("id")}
                data[key][i] = merged
                _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
                return merged
        raise ValueError(f"no '{key}' record with id '{rid}' in {path.name}")

    lines, _key_i, spans, idx, records, indent = _locate(path, key, rid)
    merged = {**records[idx], **fields, "id": records[idx].get("id")}
    s, e = spans[idx]
    lines[s:e] = _render_item(merged, indent).rstrip("\n").split("\n")
    _validate_and_write(path, key, lines,
                        lambda recs: any(str(r.get("id")) == rid for r in recs))
    return merged


def delete_record(path, key: str, rid: str) -> None:
    """Remove the record ``rid``; an emptied block becomes ``key: []``."""
    path = Path(path)
    rid = str(rid)
    if path.suffix.lower() == ".json":
        data = _load_data(path)
        before = data.get(key) or []
        after = [r for r in before
                 if not (isinstance(r, dict) and str(r.get("id")) == rid)]
        if len(after) == len(before):
            raise ValueError(f"no '{key}' record with id '{rid}' in {path.name}")
        data[key] = after
        _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return

    lines, key_i, spans, idx, _records, _indent = _locate(path, key, rid)
    s, e = spans[idx]
    del lines[s:e]
    if len(spans) == 1:
        # last item removed: `key:` alone parses as None, which downstream code
        # doesn't expect -- pin it to an explicit empty list.
        lines[key_i] = f"{key}: []"
    _validate_and_write(path, key, lines,
                        lambda recs: not any(str(r.get("id")) == rid for r in recs))


def move_record(path, key: str, rid: str, offset: int) -> None:
    """Swap the record ``rid`` with its neighbor (``offset`` -1 = up, +1 = down)."""
    path = Path(path)
    rid = str(rid)
    if offset not in (-1, 1):
        raise ValueError("offset must be -1 or +1")
    if path.suffix.lower() == ".json":
        data = _load_data(path)
        recs = data.get(key) or []
        idx = next((i for i, r in enumerate(recs)
                    if isinstance(r, dict) and str(r.get("id")) == rid), None)
        if idx is None:
            raise ValueError(f"no '{key}' record with id '{rid}' in {path.name}")
        j = idx + offset
        if 0 <= j < len(recs):
            recs[idx], recs[j] = recs[j], recs[idx]
            _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return

    lines, _key_i, spans, idx, _records, _indent = _locate(path, key, rid)
    j = idx + offset
    if not 0 <= j < len(spans):
        return  # already at the edge -- nothing to do
    a, b = sorted((idx, j))
    (a_s, a_e), (b_s, b_e) = spans[a], spans[b]
    lines[a_s:b_e] = lines[b_s:b_e] + lines[a_e:b_s] + lines[a_s:a_e]
    _validate_and_write(path, key, lines,
                        lambda recs: any(str(r.get("id")) == rid for r in recs))
