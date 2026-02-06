---
doc_id: result-module-v1
title: Result Module — Public API Contract
type: api_contract
domain: internal-test-automation
language: en
version: 1.0.0
status: current
effective_date: 2026-01-02
audience: [llm, test]
product: RESULT_MODULE
class_name: Result

methods_index:
  - overall
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

checksum: 8b0664b247db37239a7b0dacc7335417a6459936627e4f5276e39ea3e9c1b062
---

# Result Module — Public API Contract v1

This document defines the **authoritative public interface** of the `Result` class used by test executors and generated tests to store measurements, verdicts, criteria, and evidence, and to export reports.

Scope
- Defines *data shape* and *method behavior* for `Result`.
- Does not define instrument APIs (see SCPI contracts).


## Usage

```python
from rules_packager_base import Result

res = Result(test_name="EXAMPLE-001")
res.measurements[1] = 3.30
res.verdicts[1] = "PASS"

# Persist / display
res.print_json()
res.export_html("EXAMPLE-001.html")
```

Notes
- Measurement IDs are integers in-memory; when serialized to JSON, keys become strings.
- `export_html()` writes a self-contained HTML report.


## Data Model

### `Result` fields

- `test_name: str` — human-readable test identifier.
- `measurements: Dict[int, Any]` — measurement ID → recorded value.
- `verdicts: Dict[int, str]` — measurement ID (or criterion ID) → verdict token.
- `criteria: Dict[int, Dict[str, Any]]` — criterion ID → criterion object.
- `log: List[str]` — sequential log lines (including operator prompts and responses).
- `evidence: List[Dict[str, Any]]` — evidence records.

### Evidence record

Evidence records are dictionaries with this shape:

```json
{"label": "<string>", "file": "<path>", "meas_id": 123}
```

`meas_id` may be `null`.


## API Reference

### `overall` (property)

- `overall -> str`

Returns an aggregate status derived from `verdicts.values()`:
- No verdicts present → `"SKIP"`
- Any `"FAIL"` present → `"FAIL"`
- All `"SKIP"` → `"SKIP"`
- All `"PASS"` → `"PASS"`
- Anything else (mixed PASS/SKIP, unknown tokens, lowercase tokens like `"pass"`, etc.) → `"PARTIAL"`

### `add_evidence`

- `add_evidence(label: str, path: str, meas_id: int | None = None) -> None`

Appends a new evidence record to `evidence`. No validation is performed on `path` or `meas_id`.

### `to_json`

- `to_json() -> dict`

Returns a dictionary intended for JSON encoding with keys.

Example JSON text (after `json.dumps(...)`):

```json
{
  "test_name": "...",
  "measurements": {"1": 3.3},
  "verdicts": {"1": "PASS"},
  "criteria": {"1": {"type": "range_abs", "expr": "{1} = 3.3 V ± 5%"}},
  "evidence": [{"label": "scope", "file": "capture.png", "meas_id": 1}],
  "log": ["..."],
  "overall": "PASS"
}
```

Notes
- The returned Python dict preserves in-memory key types (measurement/verdict/criteria keys are `int`).
- When encoded as JSON text, integer keys appear as strings.

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
- **Procedure** section (optional): includes log entries that are strings starting with `"Step"`.
- **Requirements and Results** table: built from `criteria` (iterated in sorted key order).
  - For each criterion, the table displays `expr`, a selected measurement value, units, and a verdict.
  - If a criterion contains `ref`, it is used *as-is* as the measurement ID for lookup; it is not coerced to `int`.
- **Logs** section (optional): includes all entries from `log`.

### `from_json_dict` (classmethod)

- `from_json_dict(data: dict) -> Result`

Builds a `Result` from a JSON-like dictionary.

Key conversion
- Converts keys of `measurements`, `verdicts`, and `criteria` to `int` using `int(k)`.
- Raises `ValueError` or `TypeError` if a key cannot be converted.
- Only the top-level keys are converted; nested fields (e.g., `criteria[*]["ref"]`) are not coerced.

### `from_json_file` (classmethod)

- `from_json_file(path: str) -> Result`

Loads a JSON file (UTF-8) and delegates to `from_json_dict`.


## Machine-Readable Method Table (JSON)

```json
{
  "types": {
    "VerdictToken": ["PASS", "FAIL", "SKIP"],
    "OverallStatus": ["PASS", "FAIL", "SKIP", "PARTIAL"],
    "EvidenceItem": {
      "label": "string",
      "file": "string",
      "meas_id": "int|null"
    }
  },
  "methods": [
    {"name":"overall","args":[],"returns":"str","notes":"Aggregate status derived from verdicts"},
    {"name":"add_evidence","args":[["label","str"],["path","str"],["meas_id","int|null",null]],"returns":"None"},
    {"name":"to_json","args":[],"returns":"object","notes":"Returns dict for JSON serialization"},
    {"name":"print_json","args":[],"returns":"None"},
    {"name":"export_html","args":[["output","str|Path|null",null]],"returns":"Path"},
    {"name":"from_json_dict","args":[["data","object"]],"returns":"Result","notes":"Coerces measurement/verdict/criteria keys to int"},
    {"name":"from_json_file","args":[["path","str"]],"returns":"Result"}
  ]
}
```
