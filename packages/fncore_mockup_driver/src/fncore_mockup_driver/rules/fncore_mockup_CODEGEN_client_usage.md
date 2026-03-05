---
doc_id: fncore-mockup-codegen-client-usage-v1
title: FNCORE Mockup Client — CODEGEN Usage (LLM)
type: usage_guide
domain: controller
language: en
version: 1.0.1
status: current
effective_date: 2025-11-04
audience: [llm, test, firmware]
product: FNCORE
class_name: FncoreMockupClient
facade_module: fncore_mockup_client
transports: [ASRL]
methods_index:
  - write_digital
  - read_digital
  - write_pwm
  - write_analog_volts
  - read_analog
  - uart_send
manual_override_prompt: true
logging_format: plain_strings
default_baud: 115200
timeout_s_default: 2.0
supports_manual_override: true
synonyms:
  controller: [mcu, dsc]
  manual_override: [dry_run, operator_mode]
related: [test-rules-llm-ready-v1]
checksum: e1be58cba7cbbcd442b006478bbea4d4769bd4a6aa78bdeae460aee69e4d9970
---


> **LOAD FOR:** TEST CODE GENERATION

> This is the authoritative FNCORE reference for code generation.

# FNCORE Mockup Client — LLM Usage Guide

## Goal
Control a FNCORE-based DUT via a simple serial line protocol while writing readable, auditable test code. This class wraps ASCII commands and keeps a structured log for each action.

## Import
```python
from fncore_mockup_driver import FncoreMockupClient as FncoreClient
```

## Lifecycle
1. Construct with connection parameters and a shared `controller_log` list.
2. Call command methods.
3. Call `close()` in `finally`.

```python
controller_log = []
fn = FncoreClient(port="COM7", baud=115200, timeout_s=2.0,
                  log_list=controller_log, manual_override=False)

try:
    fn.write_digital("DSC", "IO#DSC18", 1)
finally:
    fn.close()
```

## Constructor
```python
FncoreClient(port, baud, timeout_s, log_list, manual_override=False,
             max_retries=3, retry_delay_ms=50)
```
- `port`: e.g., `"COM7"`, `"/dev/ttyUSB0"`.
- `baud`: integer. Typical `115200`.
- `timeout_s`: float seconds for serial read.
- `log_list`: a Python list that collects plain string entries per command (e.g. `"CMD: readDigital DSC IO#DSC18 | RESP: 1"`, `"MANUAL: readDigital DSC IO#DSC18 -> 1"`, `"RETRY 1/3 [read_digital_input on channel IO#DSC18]: got None"`).
- `manual_override`: if `True`, no serial I/O; prints the exact line and waits for operator confirmation.
- `max_retries`: number of automatic retries on read failure (default `3`). Set `0` to disable.
- `retry_delay_ms`: delay in ms between retries (default `50`).

## Manual-override semantics
- Prints `MANUAL_EXEC: <command>` and prompts the operator to type it on the device console.
- For **writes** (`write_digital`, `write_pwm`, `write_analog_volts`), no response is requested; the method returns `"OK"`.
- For **digital reads**, the operator must enter a strict `0` or `1` (the prompt repeats until valid).
- For **analog reads**, the operator may enter SI-friendly values (e.g., `500mV`, `2.40V`).
- For `uart_send`, the operator pastes the device response line (may be empty) and the method returns that string.
- Use when hardware is unavailable or during dry runs.

## LLM codegen rule (mandatory): manual override is handled inside the driver

Generated tests MUST NOT implement a separate manual-mode branch for controller steps.

- Always call the client methods (`fn.write_digital`, `fn.read_digital`, `fn.write_analog_volts`, etc.) in the normal step flow.
- Set `manual_override=CONTROLLER_MANUAL_OVERRIDE` in the constructor.
- Do not print `MANUAL_EXEC:` yourself and do not wrap controller calls in extra `prompt()` logic; the driver prints/prompts/logs internally when `manual_override=True`.

Canonical pattern:
```python
controller_log = []
fn = FncoreClient(FNCORE_PORT, FNCORE_BAUD, FNCORE_TIMEOUT, controller_log,
                  manual_override=CONTROLLER_MANUAL_OVERRIDE)

# Always call driver methods; manual_override changes behavior internally.
fn.write_digital("DSC", "IO#DSC41", 1)
```


## Commands
All commands include a `TARGET` namespace (e.g., `"DSC"`).

### `write_digital(TARGET, io_id, val01)`
Set a digital output.
```python
fn.write_digital("DSC", "IO#DSC41", 1)   # drive high
```

### `read_digital(TARGET, io_id) -> int`
Read a digital input. Returns `0` or `1`. Raises `RuntimeError` if the response
cannot be parsed after all retries.
```python
state = fn.read_digital("DSC", "IO#DSC5")  # raises on failure
```

### `write_pwm(TARGET, pwm_id, duty8bit)`
Set an 8-bit PWM duty (0–255).
```python
fn.write_pwm("DSC", "PWM#DSC0", 128)     # ≈50% duty
```

### `write_analog_volts(TARGET, dac_id, volts) -> dict`
Write a DAC voltage. `0.0…3.3 V` maps to `0…4095`.
```python
rec = fn.write_analog_volts("DSC", "DAC#DSC0", 3.3)
```

### `read_analog(TARGET, adc_id) -> float`
Read an analog input. Returns voltage in volts. Raises `RuntimeError` if the
response cannot be parsed after all retries.
```python
v = fn.read_analog("DSC", "ADC#DSC2")  # raises on failure
```

### `uart_send(TARGET, uart_id, payload)`
Send a UART frame.
```python
fn.uart_send("DSC", "UART#0", "HELLO")
```

## Logging
Each method appends a plain string to `controller_log`. Examples:
```
CMD: writeDigital DSC IO#DSC41 1 | RESP: OK
CMD: readDigital DSC IO#DSC5 | RESP: 1
MANUAL: readDigital DSC IO#DSC5 -> 1
[analog_write] 3.3V -> code 4095
RETRY 1/3 [read_analog_input on channel ADC#DSC2]: got None
```

## Patterns for LLM-generated tests

## Minimal example
```python
from fncore_mockup_driver import FncoreMockupClient as FncoreClient
controller_log = []
fn = FncoreClient("COM7", 115200, 2.0, controller_log, manual_override=False)

try:
    # Step 1 — Enable charger control so PPU path is active
    fn.write_digital("DSC", "IO#DSC41", 1)
    # Step 2 — Drive DAC to nominal command
    fn.write_analog_volts("DSC", "DAC#DSC0", 3.3)
    # Step 3 — Verify status input (raises RuntimeError on parse failure)
    raw_state = fn.read_digital("DSC", "IO#DSC12")
    ok = raw_state == 1
    # Step 4 — Sample a feedback node (raises RuntimeError on parse failure)
    fb_v = fn.read_analog("DSC", "ADC#DSC3")
    # Step 5 — Send a diagnostic string over UART
    fn.uart_send("DSC", "UART#0", "PING")
finally:
    fn.close()
print(controller_log)
```

## Error handling rules
- Always `close()` in `finally`.
- `read_digital` and `read_analog` raise `RuntimeError` on parse failure after all retries — do **not** check for `None`.
- Retries 3× by default (50 ms between). Tune with `max_retries` and `retry_delay_ms` constructor params.
- Clip inputs: PWM 0–255, DAC 0.0–3.3 V, digital 0/1.
- Never assume default `TARGET`.
- In manual mode, reads prompt the operator for values; the script may validate them normally.
