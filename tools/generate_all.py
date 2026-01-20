#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    # .../test_procedure_generation/tools/generate_all.py -> project root
    return Path(__file__).resolve().parents[1]


def _ensure_import_paths(project_root: Path) -> None:
    # Allow running without installing the package.
    sys.path.insert(0, str(project_root / "src"))


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "doc"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _clean_output_dir(out_dir: Path) -> None:
    # Only remove files we own.
    for p in out_dir.glob("*.md"):
        p.unlink(missing_ok=True)
    (out_dir / "manifest.json").unlink(missing_ok=True)


def _clean_wheels_dir(out_dir: Path) -> None:
    # Only remove files we own.
    for p in out_dir.glob("*.whl"):
        p.unlink(missing_ok=True)
    (out_dir / "requirements.txt").unlink(missing_ok=True)


def _ensure_gui_project_layout(
    *,
    project_out: Path,
    overwrite: bool,
    init_empty_test: bool,
    empty_test_name: str,
) -> None:
    if project_out.exists() and not project_out.is_dir():
        raise SystemExit(f"--project-out must be a directory path: {project_out}")

    project_out.mkdir(parents=True, exist_ok=True)

    # GUI expects these directories to exist.
    for rel in (
        Path("config") / "rules",
        Path("config") / "wheels",
        Path("tests"),
        Path("results"),
        Path("scenarios"),
        Path("reports"),
    ):
        (project_out / rel).mkdir(parents=True, exist_ok=True)

    if not init_empty_test:
        return

    # Create a starter test so the GUI has a valid structure to scan.
    test_dir = project_out / "tests" / empty_test_name
    proc_path = test_dir / "procedure.json"
    script_path = test_dir / "test.py"

    if test_dir.exists() and any(test_dir.iterdir()) and not overwrite:
        raise SystemExit(
            f"Empty test folder already exists and is not empty: {test_dir} (use --overwrite)"
        )

    test_dir.mkdir(parents=True, exist_ok=True)

    if overwrite or not proc_path.exists():
        proc = {
            "name": "EMPTY-TEST-001",
            "description": "",
            "equipment": [],
            "steps": [],
            "expected": [],
            "board": "",
        }
        proc_path.write_text(json.dumps(proc, indent=2) + "\n", encoding="utf-8")

    if overwrite or not script_path.exists():
        script_path.write_text(
            """#!/usr/bin/env python3
import json
from pathlib import Path


def main() -> int:
    # The GUI runs this script with cwd=results/<test_name>/
    out = Path("results.json")
    out.write_text(
        json.dumps(
            {
                "overall": "PASS",
                "measurements": {},
                "criteria": {},
                "verdicts": {},
                "log": ["EMPTY-TEST-001: placeholder test script"],
            },
            indent=2,
        )
        + "\\n",
        encoding="utf-8",
    )
    print(f"Wrote {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
            encoding="utf-8",
        )


def collect_rules(*, registry_path: Path, out_dir: Path, overwrite: bool) -> None:
    _ensure_import_paths(_project_root())
    from test_procedure_generation.driver_links import build_llm_context  # type: ignore[import-not-found]  # noqa: E402

    if out_dir.exists():
        if not overwrite:
            raise SystemExit(f"Output folder already exists: {out_dir} (use --overwrite)")
        _clean_output_dir(out_dir)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    docs = build_llm_context(registry_path=registry_path)

    manifest: list[dict[str, object]] = []

    for i, d in enumerate(docs, start=1):
        doc_id = d.doc_id or f"no-doc-id-{d.sha256[:8]}"
        filename = f"{i:03d}_{_slug(d.source)}_{_slug(doc_id)}.md"
        (out_dir / filename).write_text(d.content, encoding="utf-8")

        manifest.append(
            {
                "index": i,
                "filename": filename,
                "source": d.source,
                "origin": d.origin,
                "relpath": d.relpath,
                "doc_id": d.doc_id,
                "title": d.title,
                "sha256": d.sha256,
            }
        )

    _write_json(out_dir / "manifest.json", manifest)

    print(f"Wrote {len(docs)} documents to {out_dir}")
    print(f"Manifest: {out_dir / 'manifest.json'}")


def _find_project_root_from_package_dir(package_dir: Path) -> Path:
    cur = package_dir.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError(f"Could not find pyproject.toml above: {package_dir}")


def _pip_available() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _ensure_pip() -> None:
    # Only install pip if the user explicitly asked for it.
    if _pip_available():
        return

    print("pip not found; attempting: python -m ensurepip --upgrade")
    try:
        _run([sys.executable, "-m", "ensurepip", "--upgrade"])
    except Exception as e:
        raise SystemExit(
            "Failed to run ensurepip. On some Python builds, ensurepip is not included. "
            "Install pip using your system package manager or Python installer. "
            f"Details: {e}"
        )

    if not _pip_available():
        raise SystemExit(
            "pip is still unavailable after ensurepip. Install pip using your system Python installer."
        )


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}")


def build_selected_wheels(
    *,
    registry_path: Path,
    out_dir: Path,
    overwrite: bool,
    ensure_pip: bool,
    only_binary: bool,
) -> None:
    print(f"Wheel output folder: {out_dir}")

    if out_dir.exists() and overwrite:
        _clean_wheels_dir(out_dir)

    if ensure_pip:
        _ensure_pip()

    if not _pip_available():
        print("ERROR: pip is not available for this Python interpreter.")
        print("Rerun with: --ensure-pip")
        raise SystemExit(1)

    _ensure_import_paths(_project_root())
    from test_procedure_generation.driver_links import load_registry  # type: ignore[import-not-found]  # noqa: E402

    reg = load_registry(registry_path)
    packs = reg.get("packs")
    if not isinstance(packs, list):
        raise SystemExit("Registry missing 'packs' list")

    selected_project_roots: list[Path] = []

    # Enabled packs must explicitly declare wheel.enabled=true for wheel building.
    for pack in packs:
        if not isinstance(pack, dict):
            continue

        pack_id = pack.get("id")
        enabled = bool(pack.get("enabled", False))
        if not enabled:
            continue

        wheel = pack.get("wheel")
        if not isinstance(wheel, dict) or not bool(wheel.get("enabled", False)):
            raise SystemExit(
                f"Enabled pack {pack_id!r} does not declare wheel.enabled=true; cannot build wheels"
            )

        # Determine project root.
        project_root: Path | None = None

        wheel_project_root = wheel.get("project_root")
        if isinstance(wheel_project_root, str) and wheel_project_root:
            project_root = Path(wheel_project_root)
            if not project_root.is_absolute():
                project_root = registry_path.parent / project_root
        else:
            rules = pack.get("rules")
            if not isinstance(rules, dict):
                raise SystemExit(f"Enabled pack {pack_id!r} missing rules block")
            src = rules.get("source")
            if not isinstance(src, dict) or "type" not in src:
                raise SystemExit(f"Enabled pack {pack_id!r} missing rules.source")

            if src["type"] == "path":
                p = src.get("path")
                if not isinstance(p, str) or not p:
                    raise SystemExit(f"Enabled pack {pack_id!r} has invalid rules.source.path")
                pkg_dir = Path(p)
                if not pkg_dir.is_absolute():
                    pkg_dir = registry_path.parent / pkg_dir
                project_root = _find_project_root_from_package_dir(pkg_dir)
            elif src["type"] == "package":
                raise SystemExit(
                    f"Enabled pack {pack_id!r} uses package source; set wheel.project_root explicitly"
                )
            else:
                raise SystemExit(f"Unsupported rules.source.type for pack {pack_id!r}: {src['type']!r}")

        if project_root is None:
            raise SystemExit(f"Could not resolve project root for enabled pack {pack_id!r}")

        selected_project_roots.append(project_root)

    # De-dup
    uniq_roots: list[Path] = []
    seen = set()
    for r in selected_project_roots:
        rr = str(r.resolve())
        if rr not in seen:
            seen.add(rr)
            uniq_roots.append(r)

    out_dir.mkdir(parents=True, exist_ok=True)

    print("Selected projects:")
    for project_root in uniq_roots:
        print(f"- {project_root}")

    for project_root in uniq_roots:
        print(f"Building wheel: {project_root}")
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--wheel-dir",
                str(out_dir),
                str(project_root),
            ]
        )

        # Cleanup common build artifacts so the repo doesn't get polluted.
        import shutil

        for artifact in ("build", "dist"):
            p = project_root / artifact
            if p.exists() and p.is_dir():
                shutil.rmtree(p)
        for egginfo in project_root.glob("*.egg-info"):
            if egginfo.is_dir():
                shutil.rmtree(egginfo)

    # Optional: write a helper requirements.txt that installs from this folder.
    # - Use --find-links . so it works after copying the folder elsewhere.
    # - Do NOT use --no-index so pip can still resolve third-party deps from PyPI.
    wheel_files = sorted([p.name for p in out_dir.glob("*.whl")])

    req_lines = ["--find-links ."]
    if only_binary:
        req_lines.append("--only-binary :all:")
    req_lines.extend(wheel_files)

    (out_dir / "requirements.txt").write_text(
        "\n".join(req_lines) + "\n",
        encoding="utf-8",
    )

    print(f"Wheels written to: {out_dir}")
    print(f"Install helper: {out_dir / 'requirements.txt'}")


def main(argv: list[str] | None = None) -> int:
    project_root = _project_root()

    ap = argparse.ArgumentParser(description="Generate rule collection and optional wheel bundle")
    ap.add_argument(
        "--registry",
        default=str(project_root / "drivers_registry.json"),
        help="Path to drivers_registry.json",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite outputs if they exist",
    )

    ap.add_argument(
        "--collect-rules",
        action="store_true",
        help="Collect selected rule documents into output/config/rules/",
    )
    ap.add_argument(
        "--rules-out",
        default=str(project_root / "output" / "config" / "rules"),
        help="Output folder for collected rules",
    )

    ap.add_argument(
        "--build-wheels",
        action="store_true",
        help="Build wheels for enabled local projects into output/config/wheels/",
    )
    ap.add_argument(
        "--ensure-pip",
        action="store_true",
        help="Attempt to install/enable pip via ensurepip before building wheels",
    )
    ap.add_argument(
        "--only-binary",
        action="store_true",
        help="Write requirements.txt with --only-binary :all: (fail if deps have no wheels)",
    )
    ap.add_argument(
        "--wheels-out",
        default=str(project_root / "output" / "config" / "wheels"),
        help="Output folder for wheels",
    )

    ap.add_argument(
        "--project-out",
        default=None,
        help=(
            "Generate a GUI-ready project folder (compatible with test_procedure_gui). "
            "If set, --rules-out and --wheels-out default to <project-out>/config/{rules,wheels}."
        ),
    )
    ap.add_argument(
        "--init-empty-test",
        action="store_true",
        help="Create a starter test under <project-out>/tests/",
    )
    ap.add_argument(
        "--empty-test-name",
        default="empty_test",
        help="Name of the starter test folder created under <project-out>/tests/ (used with --init-empty-test)",
    )

    args = ap.parse_args(argv)

    registry_path = Path(args.registry)

    project_out: Path | None = Path(args.project_out) if args.project_out else None
    if project_out is not None:
        _ensure_gui_project_layout(
            project_out=project_out,
            overwrite=bool(args.overwrite),
            init_empty_test=bool(args.init_empty_test),
            empty_test_name=str(args.empty_test_name),
        )

        # Override outputs to point at the project folder unless the user explicitly set them.
        default_rules_out = str(_project_root() / "output" / "config" / "rules")
        default_wheels_out = str(_project_root() / "output" / "config" / "wheels")

        if str(args.rules_out) == default_rules_out:
            args.rules_out = str(project_out / "config" / "rules")
        if str(args.wheels_out) == default_wheels_out:
            args.wheels_out = str(project_out / "config" / "wheels")

    did_something = False

    if args.collect_rules:
        collect_rules(
            registry_path=registry_path,
            out_dir=Path(args.rules_out),
            overwrite=bool(args.overwrite),
        )
        did_something = True

    if args.build_wheels:
        build_selected_wheels(
            registry_path=registry_path,
            out_dir=Path(args.wheels_out),
            overwrite=bool(args.overwrite),
            ensure_pip=bool(args.ensure_pip),
            only_binary=bool(args.only_binary),
        )
        did_something = True

    if not did_something:
        # Default behavior: collect rules + build wheels.
        collect_rules(
            registry_path=registry_path,
            out_dir=Path(args.rules_out),
            overwrite=bool(args.overwrite),
        )
        build_selected_wheels(
            registry_path=registry_path,
            out_dir=Path(args.wheels_out),
            overwrite=bool(args.overwrite),
            ensure_pip=bool(getattr(args, "ensure_pip", False)),
            only_binary=bool(getattr(args, "only_binary", False)),
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
