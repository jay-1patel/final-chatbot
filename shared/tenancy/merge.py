"""Deep merge for tenant profile layers.

Rules, in order of importance:
  * dicts merge key-by-key
  * ``keyed`` lists of named objects merge BY NAME, not by position — a tenant
    that ships one flow replaces that flow and keeps every other default flow
    (flows, intents, menu buttons)
  * other lists REPLACE, never append
  * scalars and ``None`` on the right-hand side never clobber the left

The left layer is always lower precedence (vertical defaults), the right layer
is higher (file, then DB).

Why keyed merging for named objects: "lists replace" is right for a list of
phrases but wrong for a list of definitions. If a tenant publishes a single
changed flow, wholesale replacement would silently delete the other five
default flows. Names give us per-item overrides plus a ``__remove__`` escape
hatch for genuinely deleting a default:

    {"flows": [{"name": "get_quote", "success_message": "New text"}]}
    {"intents": [{"name": "place_order", "__remove__": true}]}
    {"menu": {"buttons": [{"id": "menu_view_cart", "__remove__": true}]}}
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

# path (tuple of keys) -> the field that names each item
KEYED_PATHS: Dict[tuple, str] = {
    ("flows",): "name",
    ("intents",): "name",
    ("menu", "buttons"): "id",
}

REMOVE_KEY = "__remove__"


def deep_merge(base: Any, override: Any, path: tuple = ()) -> Any:
    """Merge ``override`` onto ``base``. Returns a new structure."""
    if isinstance(base, Mapping) and isinstance(override, Mapping):
        out: Dict[str, Any] = dict(base)
        for key, val in override.items():
            child_path = path + (key,)
            if key in out:
                out[key] = deep_merge(out[key], val, child_path)
            else:
                out[key] = _copy(val, child_path)
        return out
    if isinstance(base, list) and isinstance(override, list):
        key_field = KEYED_PATHS.get(path)
        if key_field and _is_named(base, key_field) and _is_named(override, key_field):
            return _merge_named(base, override, key_field, path)
        # Lists replace wholesale.
        return _copy(override, path)
    if override is None:
        return _copy(base, path)
    return _copy(override, path)


def _is_named(items: List[Any], key_field: str) -> bool:
    if not items:
        return True
    return all(isinstance(i, Mapping) and key_field in i for i in items)


def _clean_title(text: str) -> str:
    import re
    cleaned = re.sub(r"[^\w\s]", " ", str(text or "")).strip().lower()
    return " ".join(cleaned.split())


def _merge_named(base: List[Any], override: List[Any], key_field: str, path: tuple) -> List[Any]:
    """Per-item override by name. Base order is preserved, new items appended."""
    merged: List[Any] = []
    index: Dict[str, int] = {}
    title_index: Dict[str, int] = {}
    is_buttons = (path == ("menu", "buttons"))

    for item in base:
        name = str(item.get(key_field, ""))
        if item.get(REMOVE_KEY):
            continue
        idx = len(merged)
        index[name] = idx
        if is_buttons and item.get("title"):
            ct = _clean_title(item["title"])
            if ct:
                title_index[ct] = idx
        merged.append(_strip_remove(item))

    # Phase 1: Apply all tombstones from override (by exact key_field ID only)
    for item in override:
        if item.get(REMOVE_KEY):
            name = str(item.get(key_field, ""))
            if name in index:
                merged[index[name]] = None

    # Phase 2: Apply active (non-tombstone) overrides
    for item in override:
        if item.get(REMOVE_KEY):
            continue
        name = str(item.get(key_field, ""))
        title = item.get("title", "") if is_buttons else ""
        clean_t = _clean_title(title) if is_buttons and title else ""

        # Match by id first, or by normalized title if base item was not tombstoned
        matched_idx = index.get(name)
        if matched_idx is None and is_buttons and clean_t and clean_t in title_index:
            candidate_idx = title_index[clean_t]
            if merged[candidate_idx] is not None:
                matched_idx = candidate_idx

        if matched_idx is not None and merged[matched_idx] is not None:
            current = merged[matched_idx]
            merged[matched_idx] = deep_merge(current, item, path)
        else:
            new_idx = len(merged)
            index[name] = new_idx
            if is_buttons and clean_t:
                title_index[clean_t] = new_idx
            merged.append(_strip_remove(item))

    final_items = [i for i in merged if i is not None]
    if is_buttons:
        seen_ids = set()
        seen_titles = set()
        deduped = []
        for b in reversed(final_items):
            b_id = str(b.get("id", ""))
            b_t = _clean_title(b.get("title", ""))
            if (b_id and b_id in seen_ids) or (b_t and b_t in seen_titles):
                continue
            if b_id:
                seen_ids.add(b_id)
            if b_t:
                seen_titles.add(b_t)
            deduped.append(b)
        return list(reversed(deduped))

    return final_items


def _strip_remove(item: Mapping) -> Dict[str, Any]:
    """Drop the __remove__ marker so it never reaches pydantic validation."""
    return {k: v for k, v in item.items() if k != REMOVE_KEY}


def merge_layers(*layers: Any) -> Dict[str, Any]:
    """Left-to-right merge of profile layers, lowest precedence first."""
    result: Dict[str, Any] = {}
    for layer in layers:
        if not layer:
            continue
        if not isinstance(layer, Mapping):
            raise TypeError(f"profile layer must be a mapping, got {type(layer).__name__}")
        result = deep_merge(result, layer, ())
    return result


def merge_drafts(base: Any, override: Any, path: tuple = ()) -> Any:
    """Merge a new draft save over the pending draft, KEEPING ``__remove__`` markers.

    The draft is a partial layer: keyed lists (intents, flows, menu buttons)
    override lower layers by name, and a deletion is a tombstone that only the
    final live merge (``deep_merge`` in build_profile) may consume. Using
    ``deep_merge`` here would consume the tombstone the moment it is saved —
    the marker would never reach the published layer, and the deleted default
    would resurrect on publish. So this variant keeps markers in the result,
    drops the matching pending item, and lets a re-added id replace its marker.
    """
    if isinstance(base, Mapping) and isinstance(override, Mapping):
        out: Dict[str, Any] = dict(base)
        for key, val in override.items():
            child_path = path + (key,)
            if key in out:
                out[key] = merge_drafts(out[key], val, child_path)
            else:
                out[key] = _copy(val, child_path)
        return out
    if isinstance(base, list) and isinstance(override, list):
        key_field = KEYED_PATHS.get(path)
        if key_field and _is_named(base, key_field) and _is_named(override, key_field):
            return _merge_named_drafts(base, override, key_field, path)
        # Unkeyed lists still replace wholesale.
        return _copy(override, path)
    if override is None:
        return _copy(base)
    return _copy(override)


def _merge_named_drafts(base: List[Any], override: List[Any], key_field: str, path: tuple) -> List[Any]:
    """Keyed merge for the draft layer, with tombstone preservation."""
    out: List[Any] = []
    index: Dict[str, int] = {}
    title_index: Dict[str, int] = {}
    is_buttons = (path == ("menu", "buttons"))

    for item in base:
        name = str(item.get(key_field, ""))
        idx = len(out)
        index[name] = idx
        if is_buttons and item.get("title") and not item.get(REMOVE_KEY):
            ct = _clean_title(item["title"])
            if ct:
                title_index[ct] = idx
        out.append(dict(item))

    for item in override:
        name = str(item.get(key_field, ""))
        title = item.get("title", "") if is_buttons else ""
        clean_t = _clean_title(title) if is_buttons and title else ""
        marker = bool(item.get(REMOVE_KEY))

        # Tombstones match ONLY by exact name (id), never by title
        if marker:
            matched_idx = index.get(name)
        else:
            matched_idx = index.get(name)
            if matched_idx is None and is_buttons and clean_t and clean_t in title_index:
                matched_idx = title_index[clean_t]

        if matched_idx is not None:
            current = out[matched_idx]
            # A marker replaces the pending item; re-adding a tombstoned id
            # replaces the marker. Neither case can deep-merge the two.
            if marker or current.get(REMOVE_KEY):
                out[matched_idx] = dict(item)
            else:
                out[matched_idx] = merge_drafts(current, item, path)
        else:
            # A tombstone for a name the draft never carried must persist too —
            # it is what deletes the *default* at publish time.
            new_idx = len(out)
            index[name] = new_idx
            if is_buttons and clean_t and not marker:
                title_index[clean_t] = new_idx
            out.append(dict(item))

    if is_buttons:
        seen_ids = set()
        seen_titles = set()
        deduped = []
        for b in reversed(out):
            b_id = str(b.get("id", ""))
            b_t = _clean_title(b.get("title", ""))
            if b.get(REMOVE_KEY):
                if b_id and b_id not in seen_ids:
                    seen_ids.add(b_id)
                    deduped.append(b)
                continue
            if (b_id and b_id in seen_ids) or (b_t and b_t in seen_titles):
                continue
            if b_id:
                seen_ids.add(b_id)
            if b_t:
                seen_titles.add(b_t)
            deduped.append(b)
        return list(reversed(deduped))

    return out


def prune_nulls(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop ``None`` values so an override can't blank out a default by omission."""
    out: Dict[str, Any] = {}
    for key, val in payload.items():
        if val is None:
            continue
        if isinstance(val, Mapping):
            out[key] = prune_nulls(val)
        elif isinstance(val, list):
            out[key] = [prune_nulls(v) if isinstance(v, Mapping) else v for v in val]
        else:
            out[key] = val
    return out


def _copy(value: Any, path: tuple = ()) -> Any:
    if isinstance(value, Mapping):
        return {k: _copy(v, path + (k,)) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v, path) for v in value]
    return value


def collect_strings(payload: Any) -> List[str]:
    """Every string leaf in a payload — used by the eval/forbidden-term linter."""
    out: List[str] = []
    if isinstance(payload, str):
        out.append(payload)
    elif isinstance(payload, Mapping):
        for v in payload.values():
            out.extend(collect_strings(v))
    elif isinstance(payload, list):
        for v in payload:
            out.extend(collect_strings(v))
    return out

