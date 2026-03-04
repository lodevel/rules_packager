---
doc_id: result-module-v1
title: Result Module — Public API Contract
type: api_contract
domain: internal-test-automation
language: en
version: 1.2.0
status: current
effective_date: 2026-03-03
audience: [llm, test]
product: RESULT_MODULE
class_name: Result

methods_index:
  - overall
  - criteria_overall
  - add_evidence
  - to_json
  - print_json
  - export_html
  - from_json_dict
  - from_json_file

exceptions: [ValueError, TypeError, FileNotFoundError, json.JSONDecodeError]

related:
  - test-helpers-v1
  - test-rules-llm-ready-v1
  - scpi-psu-api-v1
  - scpi-eload-api-v1
  - scpi-oscilloscope-api-v2

checksum: 965cfc19f00dd7104e063868c4be77398eb45158e8152353d296e876a987f843
---

# Result Module — Public API Contract v1

Defines the public interface of `Result` used by generated tests to store results and export reports.


## Usage

```python
from rules_packager_base import Result

res = Result(test_name="EXAMPLE-001")
res.measurements[7] = 3.30
res.criteria[1] = {"type": "range_abs", "ref": 7, "expr": "{7} = 3.30 V ± 5%"}
res.verdicts[1] = "PASS"  # verdicts are keyed by criterion id

res.print_json()
res.export_html("EXAMPLE-001.html")
```


## Data Model

### `Result` fields

- `test_name: str` — human-readable test identifier.
- `measurements: Dict[int, Any]` — measurement ID → recorded value.
- `verdicts: Dict[int, str]` — **criterion ID** → verdict token.
- `criteria: Dict[int, Dict[str, Any]]` — criterion ID → criterion object.
- `log: List[str]` — sequential log lines (including operator prompts and responses).
- `evidence: List[Dict[str, Any]]` — evidence records.
- `aborted: bool` — `True` if the run was stopped by the operator/environment (e.g., `KeyboardInterrupt`, `SystemExit`, `EOFError`).
- `error: bool` — `True` if the run ended due to an unexpected exception (bug, driver/instrument failure, etc.).
- `exception_type: str` — exception class name (only meaningful when `aborted` or `error` is true).
- `exception_message: str` — exception message (only meaningful when `aborted` or `error` is true).
- `traceback_last: str` — last-line traceback summary (only meaningful when `aborted` or `error` is true).

Notes
- Criterion IDs are the keys of `RULES` / `criteria` and are independent of measurement IDs.
- JSON encoders convert integer dict keys to strings.

### Evidence record

Evidence records are dictionaries with this shape:

```json
{"label": "<string>", "file": "<path>", "meas_id": 123}
```

`meas_id` may be `null`.


## API Reference

### `overall` (property)

- `overall -> str`

Allowed values: `PASS`, `FAIL`, `SKIP`, `PARTIAL`, `ERROR`, `ABORTED`.

Definition
- If `aborted == True` → `"ABORTED"`
- Else if `error == True` → `"ERROR"`
- Else criteria aggregation derived from `verdicts.values()`:
  - No verdicts present → `"SKIP"`
  - Any `"FAIL"` present → `"FAIL"`
  - All `"SKIP"` → `"SKIP"`
  - All `"PASS"` → `"PASS"`
  - Anything else (mixed PASS/SKIP, unknown tokens, lowercase tokens like `"pass"`, etc.) → `"PARTIAL"`

### `criteria_overall` (property)

- `criteria_overall -> str`

Returns the criteria aggregation derived from `verdicts.values()` regardless of execution status.

Allowed values: `PASS`, `FAIL`, `SKIP`, `PARTIAL`.

### `add_evidence`

- `add_evidence(label: str, path: str, meas_id: int | None = None) -> None`

Appends a new evidence record to `evidence`. No validation is performed on `path` or `meas_id`.

### `to_json`

- `to_json() -> dict`

Returns a JSON-serializable dict matching the `Result` fields, plus `criteria_overall` and `overall`.

Example JSON (after `json.dumps(res.to_json(), indent=2)`):

```json
{
  "test_name": "...",
  "measurements": {"7": 3.3},
  "verdicts": {"1": "PASS"},
  "criteria": {"1": {"type": "range_abs", "ref": 7, "expr": "{7} = 3.3 V ± 5%"}},
  "evidence": [{"label": "scope", "file": "capture.png", "meas_id": 7}],
  "log": ["..."],
  "aborted": false,
  "error": false,
  "exception_type": "",
  "exception_message": "",
  "traceback_last": "",
  "criteria_overall": "PASS",
  "overall": "PASS"
}
```

### `print_json`

- `print_json() -> None`

Prints a blank line, then `RESULTS:`, then `json.dumps(self.to_json(), indent=2)` to stdout.

### `export_html`

- `export_html(output: str | Path | None = None) -> Path`

Writes an HTML report and returns the output path.

Output naming
- If `output` is `None`, a filename is derived from `test_name` (spaces replaced with underscores) and written in the current working directory.
- If `output` has no file suffix, `.html` is appended.

Report content
- **Procedure** section (optional): includes log entries starting with `"STEP "` or `"Step "`.
- **Requirements and Results** table: built from `criteria` (iterated in sorted key order).
  - For each criterion, the table displays `expr`, a selected measurement value, units, and a verdict.
  - Measurement display:
    - If `ref` exists: display `measurements[ref]`.
    - If `refs` exists: display multiple values.
  - Verdict display: `verdicts[crit_id]` only.
- **Logs** section (optional): includes all entries from `log`.

### `from_json_dict` (classmethod)

- `from_json_dict(data: dict) -> Result`

Builds a `Result` from a JSON-like dictionary.

Key conversion
- Converts keys of `measurements`, `verdicts`, and `criteria` to `int` using `int(k)`.
- Does not coerce nested fields (e.g., `criteria[*]["ref"]`).

### `from_json_file` (classmethod)

- `from_json_file(path: str) -> Result`

Loads a JSON file (UTF-8) and delegates to `from_json_dict`.


## Machine-Readable Method Table (JSON)

```json
{
  "types": {
    "VerdictToken": ["PASS", "FAIL", "SKIP"],
    "CriteriaOverallStatus": ["PASS", "FAIL", "SKIP", "PARTIAL"],
    "OverallStatus": ["PASS", "FAIL", "SKIP", "PARTIAL", "ERROR", "ABORTED"],
    "EvidenceItem": {"label": "string", "file": "string", "meas_id": "int|null"}
  },
  "methods": [
    {"name":"overall","args":[],"returns":"str"},
    {"name":"criteria_overall","args":[],"returns":"str"},
    {"name":"add_evidence","args":[["label","str"],["path","str"],["meas_id","int|null",null]],"returns":"None"},
    {"name":"to_json","args":[],"returns":"object"},
    {"name":"print_json","args":[],"returns":"None"},
    {"name":"export_html","args":[["output","str|Path|null",null]],"returns":"Path"},
    {"name":"from_json_dict","args":[["data","object"]],"returns":"Result"},
    {"name":"from_json_file","args":[["path","str"]],"returns":"Result"}
  ]
}
```
