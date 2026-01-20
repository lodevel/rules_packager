---
doc_id: test-helpers-v1
title: Test Helpers — Public API Contract
type: api_contract
domain: internal-test-automation
language: en
version: 1.1.0
status: current
effective_date: 2026-01-06

audience: [llm, test]
product: TEST_HELPERS
module_name: test_helpers

methods_index:
  - prompt
  - prompt_choice
  - parse_quantity
  - read_measurement
  - operator_judgment


exceptions: [ValueError, EOFError, KeyboardInterrupt]

related:
  - result-module-v1
  - test-rules-llm-ready-v1

checksum: d723ccfeb270ec8b6adfabdb5be30df2b5588fbdc25cfe9e482090a07a08c210
---

# Test Helpers — Public API Contract v1

This document defines the public helper functions used by generated tests to interact with an operator and parse typed measurements.

Scope
- Operator prompts (`prompt`, `prompt_choice`)
- Manual measurement input parsing (`parse_quantity`, `read_measurement`)


## Usage

```python
from rules_packager_base import prompt, read_measurement

log = []
serial = prompt("Enter serial number:", log)
v = read_measurement("Measure TP VOUT and enter value:", log, default_unit="V")
```


## API Reference

### `prompt`

- `prompt(msg: str, log: list) -> str`

Behavior
- Prints `msg.strip()` (preceded by a blank line).
- Appends the stripped message to `log`.
- Reads a line from stdin (prompt `"> "`), strips it, appends it to `log`, and returns it.

### `prompt_choice`

- `prompt_choice(msg: str, mapping: dict, log: list) -> str`

Behavior
- Re-prompts until the user enters a valid choice.
- The user response is normalized by `strip().lower()` before lookup.
- Returns `mapping[ans]`.

Notes
- Mapping keys must match the normalized form (lowercase) of the intended user input.
- On invalid input, the current implementation prints a tuple like `("Enter one of:", "y,n,skip")` and appends that tuple to `log` (so `log` may contain non-string entries).

### `parse_quantity`

- `parse_quantity(s: str, default_unit: str = "V") -> float`

Parses a numeric input string with an optional suffix.

Accepted numeric formats
- Integer or decimal, optional sign.
- Scientific notation (e.g., `1e-3`).
- Decimal comma is accepted and converted to a decimal point.

Supported unit handling (current implementation)
- Prefix-only suffix (e.g., `10m`, `47u`) applies the SI prefix multiplier and returns the scaled number.
- Voltage with optional SI prefix (e.g., `3.3V`, `10mV`) returns volts as a float.
- Bare seconds unit `s` or `S` returns seconds as a float.
- Anything else parses but is not converted; the numeric part is returned unchanged.

Notable limitations
- Prefix+seconds is not converted (e.g., `10ms` returns `10.0`, not `0.010`).
- Prefix+other units is not converted (e.g., `10mA` returns `10.0`; `5kΩ` returns `5.0`).
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


## Machine-Readable Method Table (JSON)


```json
{
  "methods": [
    {"name":"prompt","args":[["msg","str"],["log","list"]],"returns":"str"},
    {"name":"prompt_choice","args":[["msg","str"],["mapping","dict"],["log","list"]],"returns":"str"},
    {"name":"parse_quantity","args":[["s","str"],["default_unit","str","V"]],"returns":"float"},
    {"name":"read_measurement","args":[["msg","str"],["log","list"],["default_unit","str","V"]],"returns":"float"},
    {"name":"operator_judgment","args":[["meas_id","int"],["target","str"],["log","list"]],"returns":"tuple[str,str]"}

  ]
}
```
