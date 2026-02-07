from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path
from typing import Any
import warnings


@dataclasses.dataclass(frozen=True)
class RuleDoc:
    source: str  # e.g. "pack:base", "pack:fncore-mockup"
    origin: str  # package name or filesystem path
    relpath: str
    sha256: str
    content: str
    doc_id: str | None = None
    title: str | None = None


class RulesLoadError(RuntimeError):
    pass


_SHA_CHECK_MODES = {"off", "warn", "error"}


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(_read_text_file(path))
    except Exception as e:
        raise RulesLoadError(f"Failed to read JSON: {path}: {e}")


def _parse_frontmatter(md: str) -> tuple[str | None, str | None]:
    # Minimal YAML frontmatter parser: looks for a leading '---' block.
    # We only care about simple single-line keys: doc_id and title.
    md = md.lstrip("\ufeff")

    if not md.startswith("---"):
        md2 = md.lstrip()
        if not md2.startswith("---"):
            return None, None
        md = md2

    end = md.find("\n---", 3)
    if end == -1:
        # Some of the repo's .md files use an opening '---' but no closing '---'.
        # In that case, treat the first blank line as the end of frontmatter.
        end = md.find("\n\n", 3)
        if end == -1:
            return None, None

    fm = md[3:end].splitlines()
    doc_id = None
    title = None
    for line in fm:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"')
        if k == "doc_id":
            doc_id = v
        elif k == "title":
            title = v

    return doc_id, title


def _resource_base_for_package(package_name: str) -> Traversable:
    try:
        return importlib.resources.files(package_name)
    except Exception as e:
        raise RulesLoadError(f"Failed to resolve package resources for {package_name!r}: {e}")


def _load_pack_from_root(
    *,
    pack_root: Any,
    rules_index_rel: str,
    source_label: str,
    origin: str,
    sha_check: str,
) -> list[RuleDoc]:
    idx_path = pack_root / rules_index_rel
    try:
        idx_raw = idx_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RulesLoadError(f"Failed to read rules index: {origin}:{rules_index_rel}: {e}")

    try:
        idx = json.loads(idx_raw)
    except Exception as e:
        raise RulesLoadError(f"Invalid rules index JSON: {origin}:{rules_index_rel}: {e}")

    files = idx.get("files")
    if not isinstance(files, list):
        raise RulesLoadError(f"rules_index.json missing 'files' list: {origin}:{rules_index_rel}")

    base_dir = idx_path.parent
    rules_version = idx.get("rules_version") or idx.get("driver_version")
    docs: list[RuleDoc] = []

    for ent in files:
        if not isinstance(ent, dict) or "name" not in ent:
            raise RulesLoadError(f"Invalid file entry in rules index: {origin}:{rules_index_rel}: {ent!r}")
        name = ent["name"]
        expected_sha = ent.get("sha256")

        # Some packs store docs in a versioned subdirectory (e.g. rules/0.5.0/*.md)
        # while keeping rules_index.json at rules/rules_index.json.
        md_path = base_dir / name
        relpath = Path(rules_index_rel).parent / name
        if rules_version:
            candidate = base_dir / str(rules_version) / name
            if getattr(candidate, "exists", None) and candidate.exists():
                md_path = candidate
                relpath = Path(rules_index_rel).parent / str(rules_version) / name

        try:
            md_bytes = md_path.read_bytes()
        except Exception as e:
            raise RulesLoadError(f"Failed to read rule doc: {origin}:{md_path}: {e}")

        actual_sha = hashlib.sha256(md_bytes).hexdigest()
        md = md_bytes.decode("utf-8")
        if expected_sha and expected_sha != actual_sha:
            if sha_check not in _SHA_CHECK_MODES:
                raise RulesLoadError(
                    f"Invalid sha_check mode: {sha_check!r} (expected one of: {sorted(_SHA_CHECK_MODES)})"
                )

            msg = (
                "Rule doc sha256 mismatch: "
                f"{origin}:{md_path} expected={expected_sha} actual={actual_sha}"
            )
            if sha_check == "error":
                raise RulesLoadError(msg)
            if sha_check == "warn":
                warnings.warn(msg)

        doc_id, title = _parse_frontmatter(md)
        docs.append(
            RuleDoc(
                source=source_label,
                origin=origin,
                relpath=str(relpath),
                sha256=actual_sha,
                content=md,
                doc_id=doc_id,
                title=title,
            )
        )

    return docs


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def load_registry(registry_path: Path, registry_local_path: Path | None = None) -> dict[str, Any]:
    if not registry_path.exists():
        raise RulesLoadError(f"Registry file not found: {registry_path}")

    base = _load_json(registry_path)

    local_path = registry_local_path
    if local_path is None:
        local_path = registry_path.parent / "drivers_registry.local.json"

    if not local_path.exists():
        return base

    local = _load_json(local_path)

    base_packs = base.get("packs")
    local_packs = local.get("packs")

    if not isinstance(base_packs, list):
        raise RulesLoadError("Base registry missing 'packs' list")
    if not isinstance(local_packs, list):
        raise RulesLoadError("Local registry missing 'packs' list")

    merged: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}

    # Preserve base order.
    for p in base_packs:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if isinstance(pid, str) and pid:
            by_id[pid] = p
            merged.append(p)

    # Apply overrides and append new packs.
    for p in local_packs:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            raise RulesLoadError(f"Local pack missing valid id: {p!r}")

        if pid in by_id:
            # Deep-merge override into base pack.
            updated = _deep_merge_dict(by_id[pid], p)
            by_id[pid] = updated
            for i, existing in enumerate(merged):
                if isinstance(existing, dict) and existing.get("id") == pid:
                    merged[i] = updated
                    break
        else:
            merged.append(p)
            by_id[pid] = p

    return {"packs": merged}


def build_llm_context(*, registry_path: Path, sha_check: str = "off") -> list[RuleDoc]:
    """Build a deterministic list of rule documents for LLM context.

    The registry is type-agnostic: it is a list of independently enabled "packs".
    Each pack may contain only rules (docs) or rules + python code.
    """

    reg = load_registry(registry_path)
    packs = reg.get("packs")
    if not isinstance(packs, list):
        raise RulesLoadError("Registry missing 'packs' list")

    out: list[RuleDoc] = []
    seen_ids: set[str] = set()

    for pack in packs:
        if not isinstance(pack, dict):
            continue

        pack_id = pack.get("id")
        if not isinstance(pack_id, str) or not pack_id:
            raise RulesLoadError(f"Pack missing valid 'id': {pack!r}")
        if pack_id in seen_ids:
            raise RulesLoadError(f"Duplicate pack id: {pack_id!r}")
        seen_ids.add(pack_id)

        if not bool(pack.get("enabled", False)):
            continue

        rules = pack.get("rules")
        if not isinstance(rules, dict):
            raise RulesLoadError(f"Enabled pack {pack_id!r} missing 'rules' block")

        rules_index_rel = rules.get("rules_index")
        if not isinstance(rules_index_rel, str) or not rules_index_rel:
            raise RulesLoadError(f"Enabled pack {pack_id!r} missing rules.rules_index")

        src = rules.get("source")
        if not isinstance(src, dict) or "type" not in src:
            raise RulesLoadError(f"Enabled pack {pack_id!r} missing rules.source")

        if src["type"] == "package":
            pkg = src.get("name")
            if not isinstance(pkg, str) or not pkg:
                raise RulesLoadError(f"Pack {pack_id!r} has invalid package name")
            root = _resource_base_for_package(pkg)
            out.extend(
                _load_pack_from_root(
                    pack_root=root,
                    rules_index_rel=rules_index_rel,
                    source_label=f"pack:{pack_id}",
                    origin=pkg,
                    sha_check=sha_check,
                )
            )
        elif src["type"] == "path":
            p = src.get("path")
            if not isinstance(p, str) or not p:
                raise RulesLoadError(f"Pack {pack_id!r} has invalid path")
            root = Path(p)
            if not root.is_absolute():
                root = registry_path.parent / root
            out.extend(
                _load_pack_from_root(
                    pack_root=root,
                    rules_index_rel=rules_index_rel,
                    source_label=f"pack:{pack_id}",
                    origin=str(root),
                    sha_check=sha_check,
                )
            )
        else:
            raise RulesLoadError(f"Unsupported pack source type: {src['type']!r}")

    return out


def _default_registry_path() -> Path:
    # Static-only: default to local dev file in CWD.
    return Path.cwd() / "drivers_registry.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load driver rule packs for LLM context")
    ap.add_argument(
        "--registry",
        type=str,
        default=str(_default_registry_path()),
        help="Path to drivers_registry.json (default: ./drivers_registry.json)",
    )
    ap.add_argument(
        "--dump",
        action="store_true",
        help="Print loaded docs (doc_id/title/source) and exit",
    )
    ap.add_argument(
        "--sha-check",
        choices=sorted(_SHA_CHECK_MODES),
        default="off",
        help="Rule doc sha256 verification mode (default: off)",
    )

    args = ap.parse_args(argv)
    docs = build_llm_context(registry_path=Path(args.registry), sha_check=str(args.sha_check))

    if args.dump:
        for d in docs:
            ident = d.doc_id or "(no doc_id)"
            title = d.title or "(no title)"
            print(f"{d.source}: {ident} — {title} ({d.origin}:{d.relpath})")
        return 0

    print(f"Loaded {len(docs)} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
