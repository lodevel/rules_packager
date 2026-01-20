# Drivers Registry (`drivers_registry.json`)

`drivers_registry.json` is a type-agnostic registry that defines which **rule packs** are enabled and where to load their documents from.

It is used by:
- `tools/generate_all.py` to assemble the selected rule documents into `output/config/rules/`.
- `tools/generate_all.py` (optional) to build wheels for the enabled packs into `output/config/wheels/`.

## Key concepts

- A **pack** is an independently enabled/disabled unit.
- The tool supports a local override registry (`drivers_registry.local.json`) that can:
  - add new packs
  - override existing packs (e.g. flip `enabled`)
- A pack may be:
  - **rules-only** (Markdown docs + `rules_index.json`)
  - **rules + python code** (a Python project with `pyproject.toml`)
- Packs are **not** categorized (no “scpi vs driver” distinction). They are just enabled or not.

## Registry files

- Baseline (committed): `test_procedure_generation/drivers_registry.json`
- Local override (ignored): `test_procedure_generation/drivers_registry.local.json`
  - To enable optional packs (e.g. FNCORE mockup) without changing the committed baseline, copy:
    - `drivers_registry.local.json.example` → `drivers_registry.local.json`

Relative paths inside registry files are resolved relative to the folder containing `drivers_registry.json`.

## Local packs folder (optional)

This repo supports optional packs checked out under:
- `test_procedure_generation/packages/`

In this layout:
- `packages/labscpi/` is expected to exist (subrepo/submodule).
- Optional packs (e.g. `packages/fncore_mockup_driver/`) can exist locally and be enabled via `drivers_registry.local.json`.

## Schema

Top-level:

```json
{
  "packs": [
    {
      "id": "...",
      "enabled": true,
      "rules": {
        "source": { "type": "path" | "package", "path": "...", "name": "..." },
        "rules_index": "..."
      },
      "wheel": {
        "enabled": true,
        "project_root": "optional"
      }
    }
  ]
}
```

### Pack fields

- `id` (string, required)
  - Must be unique across all packs.
  - Used to label assembled docs as `pack:<id>`.

- `enabled` (bool)
  - If `true`, this pack’s docs are included in the assembled rule collection.

- `rules` (object, required if pack enabled)
  - `rules.source` describes where the docs live.
  - `rules.rules_index` points to the `rules_index.json` relative to the source root.

- `wheel` (object)
  - Used only when running `--build-wheels`.
  - If the pack is enabled and `wheel.enabled` is **not** `true`, wheel building hard-fails (by design).

### `rules.source`

Two source types are supported:

1) `type = "path"`
- `path` points to a directory on disk that contains the pack’s `rules_index.json` and referenced `.md` files.
- The directory can be **any folder** (rules-only packs can live anywhere).
- If `path` is relative, it is resolved relative to the registry file.

2) `type = "package"`
- `name` is a Python package name loaded via `importlib.resources`.
- Use this when the pack is installed as a Python package.

## Minimum required pack layout (important)

If a pack is `enabled: true`, rule assembly will try to load `rules.rules_index`. If that file does not exist, the assembler will fail.

In other words: **an enabled pack must provide a `rules_index.json` and the referenced `.md` files**.

### Example layout for `source.type = "path"`

If your registry says:

```json
"rules": {
  "source": { "type": "path", "path": "../some_pack_root" },
  "rules_index": "rules/rules_index.json"
}
```

Then your filesystem must contain either:

Versioned layout (recommended):

```text
../some_pack_root/
  rules/
    rules_index.json
    0.1.0/
      some_doc.md
      other_doc.md
```

or flat layout:

```text
../some_pack_root/
  rules/
    rules_index.json
    some_doc.md
    other_doc.md
```

### Example layout for `source.type = "package"`

If your registry says:

```json
"rules": {
  "source": { "type": "package", "name": "some_package" },
  "rules_index": "rules/rules_index.json"
}
```

Then after installing the wheel, the installed package must ship the same files as package-data.

Typical installed layout (site-packages):

```text
<venv>/.../site-packages/
  some_package/
    __init__.py
    rules/
      rules_index.json
      0.1.0/
        some_doc.md
```

There is no `src/` folder in a virtualenv; `src/` is only a source-tree convention.

## Pack-local `rules_index.json`

Each pack must provide a `rules_index.json` listing `.md` documents and their sha256.

Typical structure:

```json
{
  "rules_version": "0.1.0",
  "files": [
    { "name": "LLM Automated Test Code Generation Gui.md", "sha256": "..." },
    { "name": "test_rules_llm_ready.md", "sha256": "..." }
  ]
}
```

Notes:
- Files are resolved relative to the directory containing the index.
- If the index contains `rules_version`, the loader also supports docs under a version folder:
  - `<index_dir>/<rules_version>/<name>`

## Output folders

When running `generate_all.bat` or `python tools/generate_all.py`:

- Collected docs:
  - `output/config/rules/*.md`
  - `output/config/rules/manifest.json`

- Wheels (only if wheel build succeeds):
  - `output/config/wheels/*.whl`
  - `output/config/wheels/requirements.txt`

## Wheel building behavior

Wheel building is performed by `tools/generate_all.py --build-wheels`.

Rules:
- When running with `--build-wheels`, **every enabled pack must declare** `"wheel": {"enabled": true}`. If not, wheel building hard-fails.
- For packs using `rules.source.type = "path"`, the project root is discovered by walking upward from `rules.source.path` until a `pyproject.toml` is found.
- For packs using `rules.source.type = "package"`, wheel building hard-fails unless you set `wheel.project_root` (because the project root cannot be inferred from installed package resources).

### Minimum buildable wheel pack layout

To be wheel-buildable, a pack must ultimately correspond to a Python project where:

- A `pyproject.toml` exists at the project root.
- `pip wheel <project_root>` succeeds.

Typical source-tree layout:

```text
<project_root>/
  pyproject.toml
  src/
    <package_name>/
      __init__.py
      rules/
        rules_index.json
        <rules_version>/
          *.md
```

Notes:
- The `src/` folder is a source-tree convention; it is not present inside a virtualenv/site-packages.
- The `rules/` folder must be included as package data for `rules.source.type = "package"` to work.

### Choosing `wheel.project_root`

- If your pack uses `rules.source.type = "path"`, you typically do **not** need `wheel.project_root`.
  - The tool finds the nearest parent folder containing `pyproject.toml`.
- If your pack uses `rules.source.type = "package"`, set `wheel.project_root` explicitly if you want wheel building:

```json
{
  "id": "labscpi",
  "enabled": true,
  "rules": {
    "source": { "type": "package", "name": "labscpi" },
    "rules_index": "rules/rules_index.json"
  },
  "wheel": { "enabled": true, "project_root": "../labscpi" }
}
```

### Requirements output

The generated `requirements.txt` is designed for distributing wheels:
- Uses `--find-links .`
- Does **not** include `--no-index` (pip can fetch third-party dependencies from PyPI)
- Lists wheel filenames exactly
- Optional: use `--only-binary :all:` via `tools/generate_all.py --only-binary`

## Examples

### Base pack (this project)

```json
{
  "id": "base",
  "enabled": true,
  "rules": {
    "source": { "type": "path", "path": "src/test_procedure_generation" },
    "rules_index": "rules/rules_index.json"
  },
  "wheel": { "enabled": true }
}
```

### Controller driver pack (rules + code)

```json
{
  "id": "fncore-mockup",
  "enabled": true,
  "rules": {
    "source": { "type": "path", "path": "../fncore_mockup_driver/src/fncore_mockup_driver" },
    "rules_index": "rules/rules_index.json"
  },
  "wheel": { "enabled": true }
}
```

### SCPI contract pack (rules + code)

```json
{
  "id": "labscpi",
  "enabled": true,
  "rules": {
    "source": { "type": "path", "path": "../labscpi/src/labscpi" },
    "rules_index": "rules/rules_index.json"
  },
  "wheel": { "enabled": true }
}
```

### Rules-only pack (docs only)

```json
{
  "id": "my-rules-only-pack",
  "enabled": true,
  "rules": {
    "source": { "type": "path", "path": "../some_rules_folder" },
    "rules_index": "rules_index.json"
  },
  "wheel": { "enabled": false }
}
```

Note: if you run `--build-wheels` with this pack enabled, wheel building will hard-fail because `wheel.enabled` is false.

## Common errors

- Duplicate pack id:
  - Fix by making every `packs[].id` unique.

- `Rule doc sha256 mismatch`:
  - A doc changed but its `rules_index.json` wasn’t regenerated.

- `Enabled pack ... does not declare wheel.enabled=true; cannot build wheels`:
  - You enabled a pack but did not mark it wheel-buildable.
  - Either disable the pack, or set `wheel.enabled=true` and ensure it is a real Python project.
