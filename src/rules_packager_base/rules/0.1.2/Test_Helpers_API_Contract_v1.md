---
doc_id: test-helpers-v1
title: Test Helpers — Public API Contract
type: api_contract
domain: internal-test-automation
language: en
version: 1.6.0
status: current
effective_date: 2026-03-03

audience: [llm, test]
product: TEST_HELPERS
module_name: test_helpers

methods_index:
  - prompt
  - prompt_choice
  - parse_quantity
  - read_measurement
  - operator_judgment
  - checkpoint_results
  - finalize_partial_results


exceptions: [ValueError, EOFError, KeyboardInterrupt]

related:
  - result-module-v1
  - test-rules-llm-ready-v1

checksum: 7fe3c83b371dec7db4343aa22702ee203939884fe8f3385a64cd301b5342d9ee
---

# Test Helpers — Public API Contract v1

Defines helper functions used by generated tests for operator I/O, unit parsing, and result checkpointing.


## API Reference

### `prompt`

- `prompt(msg: str, log: list) -> str`

Behavior
- Print `msg.strip()` (preceded by a blank line), append to `log`, read stdin (`"> "`), append response to `log`, return response.

### `prompt_choice`

- `prompt_choice(msg: str, mapping: dict, log: list) -> str`

Behavior
- Re-prompts until the user enters a valid choice.
- The user response is normalized by `strip().lower()` before lookup.
- Returns `str(mapping[ans])`.

Notes
- Mapping keys must match the normalized form (lowercase) of the intended user input.
- Mapping values SHOULD be strings. If a numeric value is needed, return a string token (e.g., `"0"`, `"1"`) and convert at the call site.
- On invalid input, prints and logs: `Enter one of: ...`.

### `parse_quantity`

- `parse_quantity(s: str, default_unit: str = "V") -> float`

Parses a numeric input string with an optional suffix.

Accepted numeric formats
- Integer or decimal, optional sign.
- Scientific notation (e.g., `1e-3`).
- Decimal comma is accepted and converted to a decimal point.

Supported unit handling
- SI prefix scaling is supported.
  - Prefix-only suffix: `10m`, `47u`.
  - Prefix + any unit text: `3.3V`, `10mA`, `10ms`, `10kHz`, `5kΩ`.
  - The return value is a float only; unit semantics are not preserved.

Notable limitations
- Unit suffix semantics are not interpreted; only SI prefix scaling is applied (prefix-only suffix, or the first character of the suffix).
- Multi-letter prefixes are not supported (e.g., `10milliV` returns `10.0`).
- The `default_unit` parameter is currently not applied to enforce/convert units.

Errors
- Raises `ValueError("Invalid numeric input")` if the input does not match the numeric pattern.

### `read_measurement`

- `read_measurement(msg: str, log: list, default_unit: str = "V") -> float`

Behavior
- Calls `prompt(msg, log)` and passes the response to `parse_quantity(...)`.
- Repeats until parsing succeeds.
- On parsing error, prints and logs: `Invalid input: <error>. Use SI units (e.g., 2.40V).`

Notes
- The current implementation catches `Exception` broadly during parsing and will reprompt on most errors.

### `operator_judgment`

- `operator_judgment(meas_id: int, target: str, log: list) -> tuple[str, str]`

Behavior
- Prompts the operator to enter a free-text observation for the measurement ID (may be empty) using:
  - `Observation for {<meas_id>} (target: "<target>"). Free text (may be empty):`
- Prompts the operator to decide verdict (PASS/FAIL/SKIP) using:
  - `Is the result for {<meas_id>} "<target>"? [y/n/skip]: `
- Uses `prompt_choice(...)` mapping: `y → PASS`, `n → FAIL`, `skip → SKIP`.
- Returns `(observation, verdict)`.

### `checkpoint_results`

- `checkpoint_results(res: Result, json_path: str = "results.json", html_path: str = "results.html") -> None`

Behavior
- Best-effort writes `res.to_json()` to `json_path` (UTF-8, `indent=2`, `ensure_ascii=False`).
- Best-effort calls `res.export_html(html_path)`.
- Never raises (intended to be safe inside `finally:`).

### `finalize_partial_results`

- `finalize_partial_results(res: Result, exc: BaseException | None = None, kind: str | None = None, missing_verdict: str = "SKIP") -> None`

Behavior
- Verdict keys are **criterion ids** (keys of `res.criteria`).
- If `exc` is not `None`, records execution state on the `Result`:
  - Default classification: `ABORTED` for `KeyboardInterrupt`/`SystemExit`/`EOFError`, otherwise `ERROR`.
  - The `kind` parameter may override classification (`"ABORTED"` or `"ERROR"`).
  - Sets `res.aborted` / `res.error` accordingly.
  - Sets `res.exception_type`, `res.exception_message`, `res.traceback_last`.
  - Appends two log entries: `ABORTED: ...` or `ERROR: ...` and `TRACEBACK: ...`.
- Ensures every criterion id in `res.criteria` has a verdict key without overwriting existing verdicts:
  - Any missing verdict becomes `missing_verdict` (default: `SKIP`).
  - Existing `PASS`/`FAIL`/`SKIP` tokens are normalized to uppercase.
- Never raises.


## Machine-Readable Method Table (JSON)


```json
{
  "methods": [
    {"name":"prompt","args":[["msg","str"],["log","list"]],"returns":"str"},
    {"name":"prompt_choice","args":[["msg","str"],["mapping","dict"],["log","list"]],"returns":"str"},
    {"name":"parse_quantity","args":[["s","str"],["default_unit","str","V"]],"returns":"float"},
    {"name":"read_measurement","args":[["msg","str"],["log","list"],["default_unit","str","V"]],"returns":"float"},
    {"name":"operator_judgment","args":[["meas_id","int"],["target","str"],["log","list"]],"returns":"tuple[str,str]"},
    {"name":"checkpoint_results","args":[["res","Result"],["json_path","str","results.json"],["html_path","str","results.html"]],"returns":"None"},
    {"name":"finalize_partial_results","args":[["res","Result"],["exc","BaseException|null",null],["kind","str|null",null],["missing_verdict","str","SKIP"]],"returns":"None"}

  ]
}
```
