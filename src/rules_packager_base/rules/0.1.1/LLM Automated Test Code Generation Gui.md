---
doc_id: llm-test-codegen-gui-v1
title: LLM Automated Test Code Generation GUI
version: v1.0.0
status: active
created: 2025-11-05
updated: 2025-11-05
maintainer: esd.dev-QA
audience: internal-test-automation
description: Orchestrates preflight, code generation, and run; emits test.py, results.json, and artifacts.
related:
  - test-rules-llm-ready-v1
  - scpi-psu-api-v1
  - scpi-oscilloscope-api-v1
  - scpi-eload-api-v1
  - controller-driver-pack
checksum: e3bf0c94bc7717638bb4aaa93e52db4e3bae5bf0f7d8376d166a6728638587e5

## Purpose and Scope

These rules define exactly how a large-language-model (LLM) must translate a written hardware test procedure into an executable Python script. They are **mandatory**, not suggestions. The generated script must follow each directive precisely: use the exact sequence of steps given in the procedure, default instruments to manual unless remote automation was explicitly requested, handle microcontroller resources via the active **device profile’s controller interface**, enforce the single-probe-per-node rule, and never invent commands or make assumptions. If anything in the test procedure is missing or ambiguous, stop and ask the user to clarify before proceeding. Do not improvise or reorder steps.

## Procedure Macro DSL (directives in procedures)

Procedures may include compile-time macro directives (lines beginning with `@`) inside **Test steps** and **Success conditions**.

The code generator must:
- Parse and validate directives deterministically (0-based indices, insertion-order table iteration, `..` inclusive ranges, no shadowing, no empty tables).
- Treat `{{NAME}}` tokens as inert placeholders (parameters), not macro variables.
- Treat `{ID_EXPR}` as measurement ID expressions that must resolve at macro-compile time to non-negative integers (0 allowed).
- Treat range shorthands as compile-time expansion sugar:
  - `TOKEN[A..B]` expands to `TOKENA...TOKENB` (concatenation, no separator).
  - `{A..B}` expands to `{A}...{B}`.
  - If a step contains both a token range and an ID range (e.g., `Measure TP VMONI[1..3] as {1..3}.`), expand them 1:1 (zipped) and reject mismatched lengths.
- Compute an expanded step/expected stream internally for ID uniqueness checks, `RULES` mapping, and logging, even if the emitted Python uses loops/conditionals for efficiency.

If a procedure contains repeated patterns but no macros, the LLM may suggest a macro refactor (e.g., `@TABLE` + `@FOR`) but must request explicit user approval before rewriting the procedure into macro form.



## Worked examples

Use these as canonical patterns. Each example has three parts the LLM can follow:
1) Test procedure
2) Generated code

### Index
- [Example 1: EPO and Load Regulation](#example-1-epo-and-load-regulation)
- [Example 2: Oscilloscope configuration and voltage sweep measuring current](#example-2-oscilloscope-configuration-and-voltage-sweep-measuring-current)


#### Example 1: EPO and Load Regulation

This test defaults all instruments to manual mode (`*_REMOTE = False`, `*_VISA = None`). Remote automation, if desired, is enabled only by editing the generated parameter block.

##### 1) Test procedure

Test steps

Connect PSU1 + to P4 (+SR_28V) and – to P5 (GND), output OFF.

Configure PSU1 to 28 V / {ILIM}, output still OFF.

Tie P6 pin 2 (IF_SAFETY#PPU.EPO) to P4 (+SR_28V).

Connect electronic load between P1 (+PPU_28V) and P2 (GND), output OFF.

Configure the load to constant-current mode, 15 A, output still OFF.

Probe setup: connect oscilloscope CH1 → TP45 (reference to GND), CH2 → TP44 (reference to GND).

Scope setup (DC coupling):

    CH1: 1 V/div, offset = 0 V

    CH2: 1 V/div, offset = 0 V

    Timebase = 1 ms/div

    Trigger source = CH1, slope = rising, level = 1 V

    Define MATH = CH1 − CH2

Turn PSU1 output ON.

Set DSC IO#DSC18 (EPO_FNCORE) = ‘1’.

Set DSC IO#DSC41 (CHG_NCTRL) = ‘1’.

Set DSC DAC#DSC0 = 3.3 V.

Measure DC voltage between P1 (+PPU_28V) and P2 (GND) as {1}.

Turn electronic load ON (15 A CC).

Measure DC voltage between P1 (+PPU_28V) and P2 (GND) as {2}.

Set DSC DAC#DSC0 = 1.0 V.

Measure DC voltage between P1 (+PPU_28V) and P2 (GND) as {3}.

Set oscilloscope to Single acquisition mode.

Acquire waveform on MATH; record visual SI result as {4}. Save screenshot

Measure rise time on CH1 as {5}.

Measure mean voltage on CH2 as {6}.

Success conditions

{1} = 2.40 V ± 5%

{2} = 1.73 V ± 5%

{1} − {2} > 400 mV

0.95 V < {3} < 1.05 V

{4} = Ok with margin

{5} < 10 ns

{6} < 10 V

##### 2) Generated code (1:1 with steps, resilient input)

```python
# Test: PPU-EPO-LOAD-OSC-001 — EPO, Load, and Scope Verification
# Success targets:
#   {1}=2.40V±5%, {2}=1.73V±5%, ({1}-{2})>0.4V, 0.95V<{3}<1.05V, {4}=operator decision, {5}<10ns, {6}<10V

# ------------ Parameters ------------

TEST_NAME = "PPU-EPO-LOAD-OSC-001"

DEVICE_PROFILE = "FNCORE_MOCK"

# Controller
CONTROLLER_MANUAL_OVERRIDE = True
FNCORE_PORT = "COM7"
FNCORE_BAUD = 115200
FNCORE_TIMEOUT = 5.0  # s

# PSU
PSU_REMOTE = False
PSU_VISA = None
PSU_CHANNEL = None
PSU_TIMEOUT_MS = 5000
PSU_SET_VOLT = 28.0
ILIM_AMPS = None  # None => set MAX via raw SCPI

# Electronic load
ELOAD_REMOTE = False
ELOAD_VISA = None
ELOAD_CHANNEL = None
ELOAD_TIMEOUT_MS = 5000
ELOAD_CC_AMPS = 15.0

# Oscilloscope
SCOPE_REMOTE = False
SCOPE_VISA = None
SCOPE_TIMEOUT_MS = 5000
SCOPE_TDIV_S = 1e-3            # 1 ms/div
CH1_VDIV = 1.0                  # V/div
CH1_OFFS = 0.0
CH2_VDIV = 1.0
CH2_OFFS = 0.0
TRIG_SRC = "CHAN1"
TRIG_LEVEL_V = 1.0
TRIG_SLOPE = "POS"

# Success rules (rule ids 1..N; measurement ids appear in ref/refs)
RULES = {
    1: {"type": "within_pct", "ref": 1, "target": 2.40, "tol_pct": 5, "units": "V", "expr": "{1} = 2.40 V ± 5%"},
    2: {"type": "within_pct", "ref": 2, "target": 1.73, "tol_pct": 5, "units": "V", "expr": "{2} = 1.73 V ± 5%"},
    3: {"type": "gt_abs_expr", "refs": [1, 2], "limit": 0.4, "units": "V", "expr": "{1} - {2} > 400mV"},
    4: {"type": "range_abs", "ref": 3, "lower": 0.95, "upper": 1.05, "units": "V", "expr": "0.95V < {3} < 1.05V"},
    5: {"type": "operator_decision", "ref": 4, "expr": "{4} = Ok with margin"},
    6: {"type": "lt_abs", "ref": 5, "limit": 10e-9, "units": "s", "expr": "{5} < 10ns"},
    7: {"type": "lt_abs", "ref": 6, "limit": 10.0, "units": "V", "expr": "{6} < 10V"},
}

# ------------ End parameters ------------

import json, re
from dataclasses import dataclass, field
import traceback
from typing import Any, Dict, List, Optional

# Contract facades
from labscpi.psu_scpi import PowerSupply
from labscpi.eload_scpi import ElectronicLoad
from labscpi.oscilloscope_scpi import Oscilloscope, Measure, ChannelUnit, TriggerSweepMode, MathOperator  # facade enums

from fncore_mockup_driver import FncoreMockupClient as FncoreClient
from rules_packager_base import (
    Result,
    prompt,
    prompt_choice,
    read_measurement,
    operator_judgment,
)

def _require_filled():
    missing = []
    if DEVICE_PROFILE == "FNCORE_MOCK" and not CONTROLLER_MANUAL_OVERRIDE:
        if not FNCORE_PORT: missing.append("FNCORE_PORT")
        if FNCORE_BAUD is None: missing.append("FNCORE_BAUD")
        if FNCORE_TIMEOUT is None: missing.append("FNCORE_TIMEOUT")
    if PSU_REMOTE:
        if not PSU_VISA: missing.append("PSU_VISA")
        if not PSU_CHANNEL: missing.append("PSU_CHANNEL")
    if ELOAD_REMOTE:
        if not ELOAD_VISA: missing.append("ELOAD_VISA")
        if not ELOAD_CHANNEL: missing.append("ELOAD_CHANNEL")
    if SCOPE_REMOTE and not SCOPE_VISA:
        missing.append("SCOPE_VISA")
    if missing:
        raise RuntimeError("Startup parameters missing: " + ", ".join(missing))

def build_criteria(rules: dict) -> dict:
    crit = {}
    for rid, r in rules.items():
        t = r["type"]
        if t == "within_pct":
            tgt = float(r["target"]); p = float(r["tol_pct"]) / 100.0; tol = abs(tgt) * p
            crit[rid] = {"type": t, "expr": r["expr"], "ref": r["ref"],
                         "target": tgt, "tolerance_pct": r["tol_pct"],
                         "lower": tgt - tol, "upper": tgt + tol, "units": r.get("units","")}
        elif t == "range_abs":
            crit[rid] = {"type": t, "expr": r["expr"], "ref": r["ref"],
                         "lower": float(r["lower"]), "upper": float(r["upper"]), "units": r.get("units","")}
        elif t in ("lt_abs","le_abs","gt_abs","ge_abs","eq_abs"):
            crit[rid] = {"type": t, "expr": r["expr"], "ref": r["ref"],
                         "limit": float(r["limit"]), "units": r.get("units","")}
        elif t in ("lt_abs_expr","le_abs_expr","gt_abs_expr","ge_abs_expr","eq_abs_expr"):
            i, j = r["refs"]
            crit[rid] = {"type": t, "expr": r["expr"], "refs": [i, j],
                         "limit": float(r["limit"]), "units": r.get("units","")}
        elif t == "operator_decision":
            crit[rid] = {"type": t, "expr": r["expr"]}
        else:
            raise NotImplementedError(f"Unsupported rule type: {t}")
    return crit

def eval_verdicts(meas, crit, opdec=None):
    opdec = opdec or {}
    v = {}
    for rid, c in crit.items():
        t = c["type"]
        if t == "operator_decision":
            continue

        # Single-measurement comparators
        if t in ("within_pct","range_abs","lt_abs","le_abs","gt_abs","ge_abs","eq_abs"):
            mid = c.get("ref")
            if mid not in meas: v[rid] = "FAIL"; continue
            m = float(meas[mid])
            if t == "within_pct":
                v[rid] = "PASS" if c["lower"] <= m <= c["upper"] else "FAIL"
            elif t == "range_abs":
                v[rid] = "PASS" if c["lower"] < m < c["upper"] else "FAIL"
            elif t == "lt_abs":
                v[rid] = "PASS" if m <  c["limit"] else "FAIL"
            elif t == "le_abs":
                v[rid] = "PASS" if m <= c["limit"] else "FAIL"
            elif t == "gt_abs":
                v[rid] = "PASS" if m >  c["limit"] else "FAIL"
            elif t == "ge_abs":
                v[rid] = "PASS" if m >= c["limit"] else "FAIL"
            elif t == "eq_abs":
                v[rid] = "PASS" if m == c["limit"] else "FAIL"
            continue

        # Expression comparators: (mi - mj) ∘ limit
        if t in ("lt_abs_expr","le_abs_expr","gt_abs_expr","ge_abs_expr","eq_abs_expr"):
            i, j = c["refs"]
            if i not in meas or j not in meas: v[rid] = "FAIL"; continue
            lhs = float(meas[i]) - float(meas[j])
            if   t == "lt_abs_expr": v[rid] = "PASS" if lhs <  c["limit"] else "FAIL"
            elif t == "le_abs_expr": v[rid] = "PASS" if lhs <= c["limit"] else "FAIL"
            elif t == "gt_abs_expr": v[rid] = "PASS" if lhs >  c["limit"] else "FAIL"
            elif t == "ge_abs_expr": v[rid] = "PASS" if lhs >= c["limit"] else "FAIL"
            elif t == "eq_abs_expr": v[rid] = "PASS" if lhs == c["limit"] else "FAIL"
            continue

        v[rid] = "FAIL"
    return v

def step_progress(n: int, desc: str, log: list) -> None:
    msg = f"STEP {n} - {desc}"
    print(msg, flush=True)
    log.append(msg)

def run_test():
    _require_filled()
    res = Result()
    res.test_name = TEST_NAME
    res.criteria = build_criteria(RULES)

    # Bring up instruments
    psu = el = scope = None
    if PSU_REMOTE:
        psu = PowerSupply(PSU_VISA, timeout_ms=PSU_TIMEOUT_MS)
        psu.connect(); psu.initialize()
    if ELOAD_REMOTE:
        el = ElectronicLoad(ELOAD_VISA, timeout_ms=ELOAD_TIMEOUT_MS)
        el.connect(); el.initialize()
    if SCOPE_REMOTE:
        scope = Oscilloscope(SCOPE_VISA, timeout_ms=SCOPE_TIMEOUT_MS)
        scope.connect(); scope.initialize(); scope.reset()

    fn = None
    if DEVICE_PROFILE == "FNCORE_MOCK":
        fn = FncoreClient(FNCORE_PORT, FNCORE_BAUD, FNCORE_TIMEOUT, res.log, CONTROLLER_MANUAL_OVERRIDE)

    try:
        # Steps

        # Step 1 - Wire PSU1 to P4(+SR_28V)/P5(GND) with output OFF to prepare power input
        step_progress(1, "Wire PSU1 to P4(+SR_28V)/P5(GND) with output OFF to prepare power input", res.log)
        prompt("Connect PSU1 + to P4 (+SR_28V) and − to P5 (GND). Leave output OFF. Type 'ok' when done.", res.log)

        # Step 2 - Configure PSU1 to 28 V / ILIM with output OFF to set stimulus limits
        step_progress(2, "Configure PSU1 to 28 V / ILIM with output OFF to set stimulus limits", res.log)
        if PSU_REMOTE:
            psu.set_voltage(PSU_CHANNEL, PSU_SET_VOLT)
            if ILIM_AMPS is None:
                psu.set_max_current(PSU_CHANNEL)
            else:
                psu.set_current(PSU_CHANNEL, float(ILIM_AMPS))
        else:
            prompt(f"Set PSU to {PSU_SET_VOLT} V and ILIM={'MAX' if ILIM_AMPS is None else f'{ILIM_AMPS} A'}. Keep OFF. Type 'ok'.", res.log)

        # Step 3 - Tie P6.2 (IF_SAFETY#PPU.EPO) to P4(+SR_28V) to apply the required safety condition
        step_progress(3, "Tie P6.2 (IF_SAFETY#PPU.EPO) to P4(+SR_28V) to apply the required safety condition", res.log)
        prompt("Tie P6 pin 2 (IF_SAFETY#PPU.EPO) to P4 (+SR_28V). Type 'ok' when done.", res.log)

        # Step 4 - Wire electronic load to P1(+PPU_28V)/P2(GND) with output OFF to prepare load stimulus
        step_progress(4, "Wire electronic load to P1(+PPU_28V)/P2(GND) with output OFF to prepare load stimulus", res.log)
        prompt("Connect electronic load to P1(+PPU_28V)/P2(GND). Keep OFF. Type 'ok'.", res.log)

        # Step 5 - Configure e-load constant-current 15 A with output OFF to define the load condition
        step_progress(5, "Configure e-load constant-current 15 A with output OFF to define the load condition", res.log)
        if ELOAD_REMOTE: el.set_current(ELOAD_CHANNEL, float(ELOAD_CC_AMPS))
        else: prompt(f"Set e-load CC {ELOAD_CC_AMPS} A. Keep OFF. Type 'ok'.", res.log)

        # Step 6 - Connect oscilloscope CH1 probe to TP45 (ref GND) to observe the target node
        step_progress(6, "Connect oscilloscope CH1 probe to TP45 (ref GND) to observe the target node", res.log)
        prompt("Connect scope CH1 probe to TP45, ref GND. Type 'ok'.", res.log)

        # Step 7 - Connect oscilloscope CH2 probe to TP44 (ref GND) to observe the reference node
        step_progress(7, "Connect oscilloscope CH2 probe to TP44 (ref GND) to observe the reference node", res.log)
        prompt("Connect scope CH2 probe to TP44, ref GND. Type 'ok'.", res.log)

        # Step 8 - Enable scope CH1/CH2 and set DC coupling to match the procedure setup
        step_progress(8, "Enable scope CH1/CH2 and set DC coupling to match the procedure setup", res.log)
        if SCOPE_REMOTE:
            scope.set_channel_enabled(1, True); scope.set_channel_enabled(2, True)
            scope.set_channel_coupling(1, "DC"); scope.set_channel_coupling(2, "DC")
        else:
            prompt("On scope: enable CH1 and CH2; set both to DC coupling. Type 'ok'.", res.log)

        # Step 9 - Set scope CH1 to 1 V/div, offset 0 V to scale the waveform correctly
        step_progress(9, "Set scope CH1 to 1 V/div, offset 0 V to scale the waveform correctly", res.log)
        if SCOPE_REMOTE:
            scope.set_channel_scale(1, CH1_VDIV); scope.set_channel_offset(1, CH1_OFFS)
        else:
            prompt("On scope: set CH1 1 V/div, offset 0 V. Type 'ok'.", res.log)

        # Step 10 - Set scope CH2 to 1 V/div, offset 0 V to scale the waveform correctly
        step_progress(10, "Set scope CH2 to 1 V/div, offset 0 V to scale the waveform correctly", res.log)
        if SCOPE_REMOTE:
            scope.set_channel_scale(2, CH2_VDIV); scope.set_channel_offset(2, CH2_OFFS)
        else:
            prompt("On scope: set CH2 1 V/div, offset 0 V. Type 'ok'.", res.log)

        # Step 11 - Set timebase/trigger and define MATH=CH1-CH2 to enable the required delta capture
        step_progress(11, "Set timebase/trigger and define MATH=CH1-CH2 to enable the required delta capture", res.log)
        if SCOPE_REMOTE:
            scope.set_time_scale(SCOPE_TDIV_S)
            scope.set_trigger(edge_src=TRIG_SRC, level=TRIG_LEVEL_V, slope=TRIG_SLOPE)
            scope.set_math_source(1, 1, "CHAN1")
            scope.set_math_source(1, 1, "CHAN2")
            scope.enable_math(1, True, op=MathOperator.SUBTRACT)
        else:
            prompt("Configure scope: time=1ms/div, trigger CH1 rising @1V, MATH=CH1-CH2. Type 'ok'.", res.log)

        # Step 12 - Turn PSU1 output ON to apply power to the DUT
        step_progress(12, "Turn PSU1 output ON to apply power to the DUT", res.log)
        if PSU_REMOTE: psu.output(PSU_CHANNEL, True)
        else: prompt("Turn PSU1 ON. Type 'ok'.", res.log)


        # Step 13 - Set DSC IO#DSC18 (EPO_FNCORE) = 1 to enable the EPO function
        step_progress(13, "Set DSC IO#DSC18 (EPO_FNCORE) = 1 to enable the EPO function", res.log)
        fn.write_digital("DSC", "IO#DSC18", 1)

        # Step 14 - Set DSC IO#DSC41 (CHG_NCTRL) = 1 to enable charge control
        step_progress(14, "Set DSC IO#DSC41 (CHG_NCTRL) = 1 to enable charge control", res.log)
        fn.write_digital("DSC", "IO#DSC41", 1)

        # Step 15 - Set DSC DAC#DSC0 = 3.3 V to drive the control input high
        step_progress(15, "Set DSC DAC#DSC0 = 3.3 V to drive the control input high", res.log)
        fn.write_analog_volts("DSC", "DAC#DSC0", 3.3)

        # Step 16 - Measure DC voltage P1(+PPU_28V) to P2(GND) as {1} to capture the baseline value
        step_progress(16, "Measure DC voltage P1(+PPU_28V) to P2(GND) as {1} to capture the baseline value", res.log)
        v1 = read_measurement("Measure P1(+PPU_28V)-P2(GND) (e.g., 2.40V):", res.log)
        res.measurements[1] = v1

        # Step 17 - Turn electronic load ON (15 A CC) to apply the load condition
        step_progress(17, "Turn electronic load ON (15 A CC) to apply the load condition", res.log)
        if ELOAD_REMOTE: el.set_output(ELOAD_CHANNEL, True)
        else: prompt("Turn e-load ON (15 A CC). Type 'ok'.", res.log)

        # Step 18 - Measure DC voltage P1(+PPU_28V) to P2(GND) as {2} to capture the loaded value
        step_progress(18, "Measure DC voltage P1(+PPU_28V) to P2(GND) as {2} to capture the loaded value", res.log)
        v2 = read_measurement("Measure P1(+PPU_28V)-P2(GND) (e.g., 2.40V):", res.log)
        res.measurements[2] = v2

        # Step 19 - Set DSC DAC#DSC0 = 1.0 V to change the control input level
        step_progress(19, "Set DSC DAC#DSC0 = 1.0 V to change the control input level", res.log)
        fn.write_analog_volts("DSC", "DAC#DSC0", 1.0)

        # Step 20 - Measure DC voltage P1(+PPU_28V) to P2(GND) as {3} to capture the new regulated value
        step_progress(20, "Measure DC voltage P1(+PPU_28V) to P2(GND) as {3} to capture the new regulated value", res.log)
        v3 = read_measurement("Measure P1(+PPU_28V)-P2(GND) (e.g., 2.40V):", res.log)
        res.measurements[3] = v3

        # Step 21 - Arm oscilloscope Single acquisition to capture one event
        step_progress(21, "Arm oscilloscope Single acquisition to capture one event", res.log)
        if SCOPE_REMOTE:
            scope.single()
        else:
            prompt("Put scope in Single mode. Type 'ok' when armed.", res.log)


        # Step 22 - Capture MATH waveform; record visual SI as {4}; save screenshot for evidence
        step_progress(22, "Capture MATH waveform; record visual SI as {4}; save screenshot for evidence", res.log)
        fname = "scope_math_single.png"
        if SCOPE_REMOTE:
            ok = scope.wait_for_single_acq_complete(timeout_ms=10000)
            
            if(not ok):
                #Leaving scope in single may cause issues, force trigger and wait again
                scope.force_trigger()
                scope.wait_for_single_acq_complete(timeout_ms=10000)
            scope.menu_off()
            img = scope.screenshot_png()
            with open(fname, "wb") as f: f.write(img)
        else:
            prompt(f"Capture one waveform on the math channel and save it under {fname}.", res.log)
            
        res.add_evidence("Scope math CH1-CH2 single", fname, meas_id=4)

        # {4} subjective string target: {4} = Ok with margin
        si_text, si_verdict = operator_judgment(4, "Ok with margin", res.log)
        res.measurements[4] = si_text
        res.verdicts[4] = si_verdict

        # Step 23 - Measure rise time on CH1 as {5} to quantify edge speed
        step_progress(23, "Measure rise time on CH1 as {5} to quantify edge speed", res.log)
        if SCOPE_REMOTE:
            scope.enable_measure(Measure.RISE, src="CHAN1")
            trise = float(scope.get_measure(Measure.RISE, src="CHAN1"))
        else:
            trise = read_measurement("Enter {5} rise time on CH1 (e.g., 8ns):", res.log, default_unit="s")
        res.measurements[5] = trise

        # Step 24 - Measure mean voltage on CH2 as {6} to quantify the reference level
        step_progress(24, "Measure mean voltage on CH2 as {6} to quantify the reference level", res.log)
        if SCOPE_REMOTE:
            scope.enable_measure(Measure.AVG, src="CHAN2")
            ch2avg = float(scope.get_measure(Measure.AVG, src="CHAN2"))
        else:
            ch2avg = read_measurement("Enter {6} mean voltage on CH2 (e.g., 3.3V):", res.log, default_unit="V")
        res.measurements[6] = ch2avg

        # Evaluate (preserve operator verdicts for subjective checks)
        res.verdicts = eval_verdicts(res.measurements, res.criteria)
        res.verdicts[4] = si_verdict

        # Safe state
        try:
            if ELOAD_REMOTE: el.set_output(ELOAD_CHANNEL, False)
        except Exception: pass
        try:
            if PSU_REMOTE: psu.output(PSU_CHANNEL, False)
        except Exception: pass

        res.print_json()
        return res

    except Exception as e:
        # --- mandatory exception handling ---
        tb = traceback.format_exc().strip().splitlines()[-1]  # last line summary
        res.log.append(f"EXCEPTION: {e}")
        res.log.append(f"TRACEBACK: {tb}")
        res.verdicts[0] = "FAIL"      # reserved synthetic verdict to force overall=FAIL
        res.print_json()
        return res

    finally:
        try:
            if fn and not CONTROLLER_MANUAL_OVERRIDE: fn.close()
        except Exception: pass
        try:
            if SCOPE_REMOTE and scope: scope.close()
        except Exception: pass
        try:
            if ELOAD_REMOTE and el: el.close()
        except Exception: pass
        try:
            if PSU_REMOTE and psu: psu.close()
        except Exception: pass

if __name__ == "__main__":
    res = run_test()
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(res.to_json(), f, indent=2, ensure_ascii=False)

```

#### Example 2: Oscilloscope configuration and voltage sweep measuring current

##### 1) Test procedure

Configure the programmable power supply to 28 V / 1 A (current limit), output OFF.

Connect the oscilloscope current probe to the input conductor at P4, to CH3, DC coupling.

Verify that the channel 3 is configured to measure amps correctly

Connect CH1 to D1.Anode and CH2 to R3.1. 

Configure CH1 with 10V/div, offset of 0V Configure Ch2 with 10V/div, offset of 0V Configure MATH = CH1 – CH2 to measure Q2 VGS, coupling DC.

Configure MATH to 10V/div, offset of 0V Configure the oscilloscope for sequence 1 (current threshold): Set the A/div to 50mA, offset to 0A , Auto mode.

Reverse the power supply polarity at P4.

Turn the power supply ON, start at 1 V and ramp slowly up to 28 V while monitoring current.

Record the input voltage at which the current exceeds 100 mA (if 100 mA is never reached up to 28 V, enter 0 V) → {0}.

Save a screenshot of the waveform. Restore a safe state: power supply OFF and normal polarity at P4. 

Expected results 

{1} = 0V

##### 2) Generated code (1:1 with steps, resilient input)

```python
# Test: REVERSE-POLARITY-INPUT-THRESHOLD - Reverse polarity current threshold
# Implements the latest single-sequence procedure. Remote/manual branching. Evidence saved.

# -------- Parameters --------
TEST_NAME = "REVERSE-POLARITY-INPUT-THRESHOLD"

# Control modes
PSU_REMOTE = False
SCOPE_REMOTE = False

# PSU
PSU_VISA = None
PSU_CHANNEL = None
PSU_TIMEOUT_MS = 5000
PSU_SET_VOLT = 28.0
ILIM_AMPS = 1.0  # 1 A limit

# Scope
SCOPE_VISA = None
SCOPE_TIMEOUT_MS = 5000

# Nodes
IN_CONN = "P4"
R3_PIN = "1"

# Ramp parameters
CURRENT_THRESHOLD_A = 0.100  # 100 mA
RAMP_START_V = 1.0
RAMP_STOP_V  = 28.0
RAMP_STEP_V  = 1.0
RAMP_DWELL_S = 0.20  # s

# Current probe sensitivity (CH3). Set to your probe value in V/A (e.g., 1.0, 10.0).
CURRENT_PROBE_SENS_V_PER_A = 1.0

# ---- Success rule ----
RULES = {
    1: {"type":"eq_abs", "ref": 0, "limit": 0.0, "units":"V", "expr":"{0} == 0 V"}
}
# -------- End parameters --------

import time, traceback
from rules_packager_base import Result, prompt, read_measurement
from labscpi.psu_scpi import PowerSupply
from labscpi.oscilloscope_scpi import Oscilloscope, Measure, ChannelUnit, TriggerSweepMode, MathOperator  # facade enums

def step_progress(n: int, desc: str, log: list) -> None:
    msg = f"STEP {n} - {desc}"
    print(msg, flush=True)
    log.append(msg)

def _require_filled():
    missing = []
    if PSU_REMOTE and not PSU_VISA: missing.append("PSU_VISA")
    if PSU_REMOTE and not PSU_CHANNEL: missing.append("PSU_CHANNEL")
    if SCOPE_REMOTE and not SCOPE_VISA: missing.append("SCOPE_VISA")
    if missing:
        raise RuntimeError("Startup parameters missing: " + ", ".join(missing))

def _eval_rule(rule, meas):
    x = float(meas.get(rule["ref"], float("nan")))
    t = float(rule["limit"])
    typ = rule["type"]
    if typ == "eq_abs": return x == t
    if typ == "le_abs": return x <= t
    if typ == "ge_abs": return x >= t
    if typ == "lt_abs": return x <  t
    if typ == "gt_abs": return x >  t
    raise ValueError(f"Unsupported rule type: {typ}")

def ramp_until_current_threshold(res, psu=None, scope=None) -> float:
    if PSU_REMOTE and SCOPE_REMOTE and psu and scope:
        scope.clear_measures()
        scope.enable_measure(Measure.AVG, src="CHAN3")  # CH3 mean in A
        psu.output(PSU_CHANNEL, True)

        trip_v = 0.0
        v = int(RAMP_START_V)
        while v <= int(RAMP_STOP_V):
            psu.set_voltage(PSU_CHANNEL, float(v))
            time.sleep(RAMP_DWELL_S)
            i_mean = float(scope.get_measure(Measure.AVG, src="CHAN3"))
            if i_mean > CURRENT_THRESHOLD_A:
                trip_v = float(v)
                break
            v += int(RAMP_STEP_V)

        return trip_v

    # Manual
    prompt("Turn PSU OUTPUT ON.", res.log)
    prompt("Ramp 1 V -> 28 V in 1 V steps. At each step read CH3 mean current. Stop at first step where I > 100 mA.", res.log)
    vth = read_measurement("Enter {0}: first voltage where I > 100 mA (0 V if never):", res.log, default_unit="V")
    return float(vth)

def run_test():
    _require_filled()
    res = Result()
    res.test_name = TEST_NAME
    res.criteria = RULES

    psu = scope = None
    try:
        # Sessions
        if PSU_REMOTE:
            psu = PowerSupply(PSU_VISA, timeout_ms=PSU_TIMEOUT_MS)
            psu.connect(); psu.initialize()
        if SCOPE_REMOTE:
            scope = Oscilloscope(SCOPE_VISA, timeout_ms=SCOPE_TIMEOUT_MS)
            scope.connect(); scope.initialize(); scope.reset()

        # Step 1 - Configure PSU to 28 V / 1 A (current limit) with output OFF to set stimulus limits
        step_progress(1, "Configure PSU to 28 V / 1 A (current limit) with output OFF to set stimulus limits", res.log)
        if PSU_REMOTE:
            psu.set_voltage(PSU_CHANNEL, float(PSU_SET_VOLT))
            psu.set_current(PSU_CHANNEL, float(ILIM_AMPS))
            psu.output(PSU_CHANNEL, False)
        else:
            prompt(f"Set PSU to {PSU_SET_VOLT} V, current limit {ILIM_AMPS} A, OUTPUT OFF. Type 'ok'.", res.log)

        # Step 2 - Connect current probe at P4 to scope CH3 (DC coupling) to measure input current
        step_progress(2, "Connect current probe at P4 to scope CH3 (DC coupling) to measure input current", res.log)
        prompt(f"Connect current probe to input conductor at {IN_CONN} → scope CH3, DC coupling. Type 'ok'.", res.log)

        # Step 3 - Configure scope CH3 to measure amps correctly to ensure current readings are valid
        step_progress(3, "Configure scope CH3 to measure amps correctly to ensure current readings are valid", res.log)
        if SCOPE_REMOTE:
            scope.set_channel_enabled(3, True)
            scope.set_channel_coupling(3, "DC")
            scope.set_channel_units(3, ChannelUnit.AMP)
            scope.set_probe_sensitivity(3, float(CURRENT_PROBE_SENS_V_PER_A))  # V/A
            scope.set_channel_scale(3, 0.05)   # 50 mA/div
            scope.set_channel_offset(3, 0.0)
        else:
            prompt("Verify CH3 measures Amps with correct probe factor; set DC coupling, 50 mA/div, offset 0 A.", res.log)

        # Step 4 - Connect CH1 to D1.Anode and CH2 to R3.1 (ref GND) to measure Q2 VGS
        step_progress(4, "Connect CH1 to D1.Anode and CH2 to R3.1 (ref GND) to measure Q2 VGS", res.log)
        prompt(f"Connect CH1 → D1.Anode (GND ref) and CH2 → R3.{R3_PIN} (GND ref). Type 'ok'.", res.log)

        # Step 5 - Configure CH1/CH2 and MATH=CH1-CH2 (DC coupling) to derive VGS
        step_progress(5, "Configure CH1/CH2 and MATH=CH1-CH2 (DC coupling) to derive VGS", res.log)
        if SCOPE_REMOTE:
            scope.set_channel_enabled(1, True); scope.set_channel_coupling(1, "DC")
            scope.set_channel_scale(1, 10.0);  scope.set_channel_offset(1, 0.0)
            scope.set_channel_enabled(2, True); scope.set_channel_coupling(2, "DC")
            scope.set_channel_scale(2, 10.0);  scope.set_channel_offset(2, 0.0)
            scope.enable_math(True, op=MathOperator.SUBTRACT, src1="CHAN1", src2="CHAN2")
        else:
            prompt("On scope: CH1=10 V/div, off=0 V; CH2=10 V/div, off=0 V; MATH=CH1-CH2, DC coupling. Type 'ok'.", res.log)

        # Step 6 - Configure MATH scaling and scope AUTO/RUN to prepare the sequence capture
        step_progress(6, "Configure MATH scaling and scope AUTO/RUN to prepare the sequence capture", res.log)
        if SCOPE_REMOTE:
            scope.set_math_scale(10.0)
            scope.set_math_offset(0.0)
            scope.set_trigger_sweep(TriggerSweepMode.AUTO)
            scope.run()
        else:
            prompt("On scope: set MATH to 10 V/div, offset 0 V; set mode AUTO/RUN; verify CH3 at 50 mA/div, offset 0 A. Type 'ok'.", res.log)

        # Step 7 - Reverse PSU polarity at P4 to execute the reverse-polarity condition
        step_progress(7, "Reverse PSU polarity at P4 to execute the reverse-polarity condition", res.log)
        prompt(f"Reverse PSU polarity at {IN_CONN}. Verify wiring. Type 'ok'.", res.log)

        # Step 8 - Turn PSU ON and ramp 1 V -> 28 V while monitoring current to find the threshold
        step_progress(8, "Turn PSU ON and ramp 1 V -> 28 V while monitoring current to find the threshold", res.log)
        trip_v = ramp_until_current_threshold(res, psu if PSU_REMOTE else None, scope if SCOPE_REMOTE else None)

        # Step 9 - Record the first voltage where current exceeds 100 mA as {0} for evaluation
        step_progress(9, "Record the first voltage where current exceeds 100 mA as {0} for evaluation", res.log)
        res.measurements[0] = trip_v

        # Step 10 - Save screenshot; restore safe state (PSU OFF, normal polarity) to leave hardware safe
        step_progress(10, "Save screenshot; restore safe state (PSU OFF, normal polarity) to leave hardware safe", res.log)
        fname = "seq1_current_threshold.png"
        if PSU_REMOTE and SCOPE_REMOTE:
            with open(fname, "wb") as f:
                f.write(scope.screenshot_png())
        else:
            prompt(f"Save a scope screenshot named exactly '{fname}'. Type 'ok' after saving.", res.log)
        res.add_evidence("Current threshold waveform", fname, meas_id=0)

        # Safe state: PSU OFF and normal polarity
        if PSU_REMOTE:
            psu.output(PSU_CHANNEL, False)
        else:
            prompt("Turn PSU OUTPUT OFF.", res.log)
        prompt(f"Restore normal polarity at {IN_CONN}. Type 'ok' when safe.", res.log)

        # Verdicts from rule
        res.verdicts[1] = "PASS" if _eval_rule(RULES[1], res.measurements) else "FAIL"

        res.print_json()
        return res

    except Exception as e:
        res.log.append(f"EXCEPTION: {e}")
        res.log.append(f"TRACEBACK: {traceback.format_exc().splitlines()[-1]}")
        res.verdicts[1] = "FAIL"
        res.print_json()
        return res

    finally:
        try:
            if PSU_REMOTE and psu: psu.output(PSU_CHANNEL, False)
        except Exception: pass
        try:
            if scope: scope.close()
        except Exception: pass
        try:
            if psu: psu.close()
        except Exception: pass

if __name__ == "__main__":
    run_test()

```

### Profiles
This guide is device‑agnostic. Device‑specific behaviors are defined in external **Device Profile** documents. The active profile is selected during preflight via `{DEVICE_PROFILE}` and applied at code‑emission time. Do not guess defaults; if unspecified, ask the user. 

## Preflight and Per‑Device Declarations

1. **Remote/manual defaults (mandatory)** – Do not ask the user to choose remote vs manual. If the user did not explicitly request remote automation for a device, treat it as **manual** by default.
   - Set all `<DEVICE>_REMOTE = False` by default.
   - Set all `<DEVICE>_VISA = None` by default.
   - Do not emit any meta‑remarks or warnings in the generation response about missing remote/manual declarations.
   - If the user explicitly requests remote automation for a device, set `<DEVICE>_REMOTE = True` but still do not ask for connection details. Keep `<DEVICE>_VISA = None` and rely on the startup check to force the user to fill it before remote control can run.

**Device profile selection (mandatory).** Collect `{DEVICE_PROFILE}` (e.g., `"NONE"`, `"DRIVER_X"`). The executor must apply the selected profile’s argument semantics, connection defaults, required parameters, and logging rules.

2. **No equipment interrogation (mandatory)** – Do not ask for vendor/model/connection/protocol/VISA details in chat. Remote automation, if enabled, must be achieved by the user editing the generated script parameter block.

   For the controller interface, collect the link parameters required by the **active device profile** (e.g., port, baud, timeout) and whether microcontroller commands will be executed automatically or manually.

3. **Missing parameters** – All required parameters (instrument addresses, channel numbers, timeouts, target values, etc.) must be stored as variables in the generated script. If any remain `None` after generation, the script shall run a startup check and raise an error listing the missing values. Include any **profile‑required** parameters declared by the active `{DEVICE_PROFILE}`.
   - **Timeout default:** If a timeout parameter is required, default it to **5 seconds** (e.g., `*_TIMEOUT_MS = 5000` or `*_TIMEOUT_S = 5.0`).

4. **No runtime prompts for equipment details** – Once the script is generated, it must **never** prompt the operator for connection details.  Only prompts for measurements or manual actions are permitted at runtime.


## Single‑Probe‑Per‑Node (SPPN)

When multiple measurements must be taken on the same physical node using different oscilloscope settings, **reuse the same probe and channel**.  Adjust coupling (DC→AC→DC), vertical scale, or bandwidth settings between measurements rather than placing multiple probes on the same node.  Use additional channels on the same node **only** if the test explicitly requires simultaneous observations.  This rule prevents unnecessary probe loading and ensures consistent results.

## Mapping Test Steps to Code

- If a step is not executed by a declared remote instrument or the controller interface, the script must emit a `prompt()` with explicit instructions and require operator confirmation. Silent logging of manual steps is not allowed.

- Physical-action prompts are unconditional. Any wiring, probe move, thermocouple placement, or DMM step must emit a prompt("… Type 'ok'.", log) in all modes. SCPI configuration for a remote instrument does not remove the wiring prompt. The manual branch contains only prompts; the remote branch contains SCPI and the same wiring prompt.

- **1:1 mapping (expanded semantics)** – The script must behave as if it executed each step from the fully expanded procedure in order. When the authored procedure contains macro directives, the generated Python may use loops/conditionals for efficiency, but it must not reorder, merge, omit, or interleave actions relative to the expanded step stream.

- **Step markers (mandatory)** – For every numbered test step, emit a preceding inline comment in the form `# Step N - <what & why>` directly above the code or prompt that performs the step.
  - **Exact prefix (ASCII):** the marker line must start with `# Step ` + integer `N` + ` - ` (space-hyphen-space). Use the keyboard hyphen `-`.
  - **Single-line description:** `<what & why>` is a single sentence summarizing the operator action and engineering intent; it must not contain newlines.
  - **No duplicate markers:** do not additionally emit a bare `# Step N` line. The descriptive marker line is the canonical step marker.

- **Runtime step progress (mandatory)** – Immediately after each step-marker comment (`# Step N - ...`), emit a runtime progress banner so the operator can see which step is executing.
  - **Placement:** it must be the first executable statement for that step (before any prompt/SCPI/controller action).
  - **Console + log:** it must print to stdout and append the same string to `res.log`.
  - **Format (exact prefix):** `STEP N - <what & why>` using the ASCII keyboard hyphen `-`.
  - **Description binding:** the `<what & why>` string must match the step-marker comment text after `# Step N - ` exactly.
  - **Macro/loop semantics:** if the generator uses loops/conditionals, the progress banner still must be emitted once per expanded step number `N` in authored order.
  - **Canonical helper (recommended):**
    ```python
    def step_progress(n: int, desc: str, log: list) -> None:
        msg = f"STEP {n} - {desc}"
        print(msg, flush=True)
        log.append(msg)
    ```

- **No silent channel mapping**:
   - The generator must never infer that a board connector (Pnn, Jnn, etc.) is driven by a
      particular PSU channel unless the procedure explicitly instructs to connect it.
   - If a voltage change is ordered on a connector with no actuator previously declared,
      stop and mark the step AMBIGUOUS. Ask the user which supply or source is intended and
      where it is wired before generating any code.

- **No measurement without declared driver**:
   - Before generating code for any measurement on a node that requires a stimulus (e.g., “Measure … on P21”,
      “Measure … on TP_x” where TP_x is expected to be powered), the generator must confirm that a prior step
      explicitly wired and configured the actuator (PSU/AWG/jumper/microcontroller) for that node.
   - If no such step exists, mark the measurement AMBIGUOUS and prompt the user to specify the actuator and wiring.

- **Ban on name-based actuator inference**:
   - The generator must never decide that a TP belongs to the controller or a PSU because of its label.

   - The decision of which actuator drives a node must come only from an explicit step
      in the procedure, not from guessing based on naming conventions.
   - If no actuator is specified, stop and return the step as AMBIGUOUS.


- **Remote vs manual** – For instruments declared **remote**, translate configuration, stimulus, and measurement steps into SCPI commands.  For instruments declared **manual**, insert clear prompts telling the operator what to do (connect a probe, set a voltage, measure a value).  Do not generate SCPI commands for manual devices.

- **Probe connection requirement**:
   - For every oscilloscope measurement step, the script must first emit a manual operator prompt
      instructing where to connect the oscilloscope probe (positive lead to TP/node, reference to GND).
    - The script must never assume probes are already connected.
    - Example:
      prompt("Connect oscilloscope CH1 probe to TP VCONTROL, reference to GND, then type 'ok'")

- **Operator prompts for remote actions** 
   - Prompts for manual actions must restate the full instruction, including node names, polarity, mode, setpoints, and do-not-do notes. Use an imperative line list and require an explicit acknowledgement (e.g., type ‘ok’).
- **Ambiguous actions don’t create IDs.** Action-only steps that are ambiguous (missing actuator, pins, or required coupling) must **not** generate measurement IDs or success conditions. Prompt the user for clarification, or keep the step as a plain instruction if the user explicitly confirms it is clear.

- **Preconditions** – Only actions listed in the procedure’s “Preconditions” section should run before the test function.  All other narrative instructions belong in the test steps.  Do not treat descriptive text as preconditions.


## Microcontroller & Controller Interface (device‑agnostic)

### Default automation vs manual override

- By default, microcontroller resources (digital I/O, ADC, DAC, PWM, UART, etc.) are controlled via the **active device profile’s controller interface**. The script opens the connection, sends commands, reads responses, and proceeds without prompting the operator.
- **Controller API selection (subtype).** When `procedure.json` declares a controller in `equipment`, the controller `subtype` selects which controller driver pack/device profile to use (e.g., `subtype: "<driver-subtype>"`). If `subtype` is missing or ambiguous, stop and ask the user which controller driver/subtype applies.
- **Power-good modality preflight.** During preflight, the user must declare whether power-good (PG) is a **test point** (scope CH2) or a **controller I/O** (read via the profile’s digital-input command). Do not proceed until this is declared.

**Manual override visibility.** When CONTROLLER_MANUAL_OVERRIDE = True, the operator must see the exact command to type and be prompted to type that exact line. The run log must capture a line prefixed with MANUAL_EXEC: plus the command. This can be implemented either in the generated script or inside the driver, but it must be user-visible and auditable in the script’s result log.

**Canonical prompt semantics.** The operator prompt must include the exact command and an explicit acknowledgement step. If implemented in the driver, it must behave equivalently to the canonical template shown in the rules. 

 
**Manual‑override prompt content (mandatory).**  
When manual override is active, every operator prompt for a controller action must:
1) Print the exact command line to execute, and  
2) Instruct the operator to type **that exact line** on the device console, then acknowledge.  
Canonical template:
```
print(f"MANUAL_EXEC: {cmd}")
prompt("On the device console, type exactly:\\n  " + cmd + "\\nPress Enter here when done (type 'ok').")
```
Do not use vague text; show the exact line to type.

### Controller interface connection
Open the controller connection using parameters from preflight **or** the active device profile. A profile may override link parameters; if none are provided, use the preflight values.

### Controller command semantics (from driver packs)

The base rules do **not** define controller step syntax (tokens like `IO#...`, `ADC#...`, target naming, etc.) or how to map controller steps to code.

All controller actions must follow the enabled controller driver pack(s), selected by the controller entry in `procedure.json` (type=`controller`, `subtype`=`<driver-subtype>`).

- **No matching driver**: If controller-like tokens appear in the procedure but no enabled controller driver pack matches them, stop and ask the user which controller/driver applies.
- **Driver-required parameters**: If the selected driver pack requires link parameters (port/baud/timeout/etc.), include them as generated-script variables and enforce them via the startup check.
- **Logging**: The driver pack defines what must be logged for controller commands and responses.

### Device‑specific behaviors
All device‑specific behaviors (command protocol, scaling, defaults, required parameters) are defined **only** in the selected controller driver pack / device profile documents.

## Trigger, Capture and Channel Visibility Policies




 - **Single-shot handling (canonical, non-reordering)**:

   - `single()` both selects *Single* sweep and arms the acquisition. Do **not** call `set_trigger_sweep(SINGLE)` in the same sequence.

   - This rule does **not** supersede or reorder the procedure steps. It only defines how to handle trigger events when the test specifies *Single*.

   - **Arm early, wait late.**  
     Call `single()` at the step where the test arms the scope. Perform all intermediate actions exactly as written.  
     Wait only when the first *frame-dependent* operation occurs (e.g. `measure`, `screenshot`, `waveform read`).

   - **Deferred-wait sequence** (applied only once per armed single):
     1) `ok = scope.wait_for_single_acq_complete(timeout_ms)`  
     2) If not ok: `scope.force_trigger()` once, then `wait_for_single_acq_complete(timeout_ms)` again.  
     3) Proceed with the frame-dependent operation.

   - Never insert `set_trigger_sweep(SINGLE)` before or after `single()`.  
     Use `set_trigger_sweep(AUTO|NORM)` only when the test explicitly calls for continuous or normal sweep.

   - **Single mode, manual path** — When the test specifies SINGLE and the scope is manual:
    instruct the operator to arm SINGLE at the authored step, perform any intervening actions exactly
    as written, then at the first frame-dependent operation instruct the operator to capture the frame
    and save the screenshot using the canonical filename. Do not reorder steps. (API constraint: operations
    that consume a frame require a completed acquisition).


- **Acquisition semantics (explicit, mode-honoring)**:

	- Mode is literal. If a step says SINGLE, arm with single(). If it says NORM, do not call single(). If it says AUTO, do not wait for a trigger.

	- When to wait. Only wait for a fresh acquisition when the step text includes any of: capture, acquire, save screenshot, freeze, measure from frozen frame. Otherwise do not wait.

	- Defer waits. After arming SINGLE or setting NORM, execute all intervening actions exactly as written (e.g., IO toggles, PSU changes, probe moves). Call wait_for_single_acq_complete(...) only at the first step that says to capture/acquire/save/measure-from-frozen.

	- Force policy. Call force_trigger() only if the step text permits manual/forced capture (e.g., “trigger manually if it didn’t,” “force trigger”). If not permitted, do not force; log timeout and proceed per step.

	- No status polling. Do not call get_trigger_status(); the driver clears latched status internally on set_trigger_sweep(...) and single().

	- Do not upconvert. If a step set NORM, never insert single(). If a step set AUTO, never insert waits or forces.

- **Serial/bus capture ordering.** For serial or bus‑interface tests (e.g., UART, RS422, SPI, I²C), configure and arm the oscilloscope **before** enabling or transmitting interface traffic. Order: scope setup → trigger arm → controller/SCPI stimulus.

- **Timebase fallback.** When a timebase is required and not specified in the test procedure, set the oscilloscope to **5 ms/div** by default, unless a family-specific override applies.

- **Timeout policy:** Each wait-for-trigger or condition wait may define its own behavior. Default: log timeout and continue (non-fatal). If the specification marks the event as mandatory (e.g., safety or key-stimulus), the test must record "FAIL" or abort gracefully. The script must still restore AUTO/RUN and leave the instruments in a known state. Never assume all waits share one global policy; define the expected behavior inline at each step.

- **Channel visibility** – The test procedure defines which oscilloscope channels are visible. Do not auto-hide channels unless the procedure explicitly instructs it.
The script must automatically enable any channel referenced by a step (including MATH and its source channels).
If a referenced channel is undefined or unavailable, mark the step AMBIGUOUS.
- **SPPN channel tracking.** Maintain a consistent map of **node → scope channel** throughout the test. Re-use the same channel for all measurements on the same node; do not reassign unless the test explicitly requires simultaneous multi-channel observation.

- **Autoscaling** – When capturing steady‑state signals (not single‑shot events), the code may perform vertical autoscaling: adjust V/div until the waveform amplitude spans 20–90 % of the screen height, without changing timebase, coupling, trigger level, or measurement settings.  Do not autoscale for single‑shot captures.

- **Baseline restore:** After temporary changes for ripple/noise (e.g., CH2 AC coupling or vertical autoscale), restore channel to DC, specified V/div, offset=0, wait 1 s before timing measurements.

## SCPI and Equipment API Guidelines

- **APIs**: Use instrument APIs/SCPI only when remote automation is explicitly enabled for that device (`<DEVICE>_REMOTE = True`). Naming an instrument in the procedure does not imply remote control.

- **Raw pyVISA** – Use the `pyvisa` library and raw SCPI commands to control instruments.  Do not wrap these calls in custom helper classes.  Each SCPI snippet must perform a single atomic action: connect, configure, arm, poll, measure scalar, capture screenshot, set voltage/current, toggle output, etc.

- **No instrument detail questions** – Do not ask the user for vendor/model/connection/protocol/VISA details. Leave connection variables (e.g., `*_VISA`) as `None` unless the user already provided values.

- **Cheat‑sheets** – When possible, refer to vendor‑specific cheat‑sheets for common instruments (e.g. Rigol DS/MSO scopes, Keysight InfiniiVision scopes, Rigol or Keysight PSUs) to determine the correct SCPI commands.  If the necessary commands are unknown, ask the user or use general SCPI (IEEE 488.2) where applicable.

- **Instrument isolation** – SCPI snippets must not start or stop other instruments unless explicitly requested in the procedure.  For example, do not switch the PSU on/off except when instructed.  Focus each snippet on the instrument in question.
- **PSU current-limit default.** If `{ILIM}` is not provided in the test procedure, configure the supply to its **maximum current limit** (e.g., `SOUR:CURR MAX`). Do not fail startup on a missing `{ILIM}`.

## Measurement Methods and Screenshots

- **Built‑in measurements** – Use the oscilloscope’s built-in measurement functions for mean, RMS, RMS noise, rise time, and fall time. Capture a screenshot only when the test step explicitly requests one (for example, “Save screenshot”)

- **Voltage wording defaults.** If a step says *“Measure voltage on/at `<node>`”* with no subtype, interpret it as **mean DC voltage**. 

- **Measurement default rule.** If a step does not name an instrument and does not require oscilloscope-specific features, treat it as a manual measurement and prompt for the value. Naming an instrument does not imply remote automation. Emit façade/SCPI only when that device is explicitly enabled as remote (`<DEVICE>_REMOTE = True`).

- **Manual evidence:** After a screenshot, manual or not, always call add_evidence() with the same label and meas_id.

- **Explicit coupling for ripple/noise.** Ripple/noise measurements require **AC coupling**. If a ripple/noise step does not explicitly state AC coupling, treat it as ambiguous and prompt the user to specify.

- **Operator measurements** – If an instrument is declared manual, prompt the operator to measure the value using their equipment and input it.  Use the `read_measurement()` helper to interpret numeric strings with units, and store the parsed value.

- **Parity rule:** If the remote branch saves X.png, the manual branch must instruct the operator to save the same filename and call add_evidence("<label> (manual)", "X.png", meas_id=<ID>). Evidence labels and filenames are identical across branches.

- **Decision proximity**: Operator decisions (e.g., waveform acceptability for {4}, SOA check {6}) are collected immediately after the related measurement and screenshot, not at the end of the test.

## Node and Pin Handling

### Board nodes (device-agnostic)

Treat these as **physical nodes** on the DUT. They require an explicit measurement/stimulus access path (remote instrument explicitly wired to them, or an operator prompt).

- Test points: `TP ...`
- Component pins: `U#.#`, `R#.#`, `C#.#`
- Connector pins: `P#.#`, `J#.#`

If a reference does not match a board-node pattern, do **not** assume it is a controller resource. Stop and ask the user whether it is a board node or belongs to a controller driver.

### Actuator inference and ambiguity

- **No name-based actuator inference.** Do not decide which actuator drives a node from its label or pattern. A name does not imply MANUAL, REMOTE, or CONTROLLER. The driving actuator must come from an explicit step in the procedure. If missing, mark the step **AMBIGUOUS** and ask.

- **Explicit wiring prerequisite.** Never generate code to measure or drive a node that depends on an undeclared actuator. Require prior steps that wire and configure the source, then apply/enable it. Otherwise return **AMBIGUOUS**.

- **Controller semantics come from driver packs.** Any controller-like tokens and any controller target inference rules are defined only by the selected controller driver pack(s).

- **Mixed references are AMBIGUOUS.** If a step names both a board node (e.g., TP/connector) and a controller resource for the same signal, stop and ask before generating code or IDs.

### Connector polarity and two‑node measurements

- When specifying a pair of connector pins or test points (e.g. `P7/P8`), interpret the first node as the positive (+) connection and the second node as the negative (−) connection.  All stimulus and measurement calls should respect this polarity.

- For two‑node measurements written as “between NODE1 and NODE2,” interpret the measured value as **NODE1 minus NODE2**.  For example, if measuring V_GS between Gate and Source, compute V(Gate) − V(Source).  The code or instructions should clarify where to connect the leads.

### Descriptive IO naming

If the test procedure provides a descriptive alias for an I/O pin (e.g. `PWM_EN` for `IO#23`), include the alias in comments or prompts to improve clarity.  Always use the canonical identifier in the command, but annotate as `# IO#23 ("PWM_EN")` when sending commands or prompting the operator.

### Power‑good signals and microcontroller IO

When a status signal such as power good (PG) is declared as a microcontroller IO, you **must** read it via the controller interface using the profile’s digital-input command on that IO pin.  Do not use an oscilloscope or ask the operator to observe an LED for this signal.  If the procedure does not explicitly state that a microcontroller IO is available, treat it as an external test point and measure it accordingly.

## Units and Input Parsing

Use a robust unit‑parsing mechanism for operator inputs:

- Accept SI prefixes (y, z, a, f, p, n, µ/u, m, k, M, G, T, P, E, Z, Y) in either uppercase or lowercase.  
- Accept unit symbols like V, A, Ω/ohm, W, s (seconds), Hz, etc.  Variants such as “Ohm”, “ohms”, and plural forms are also valid.  
- If the user enters a number without units and the context implies the unit (e.g. time for a rise‑time measurement), interpret the number in that unit.  
- Accept scientific notation (e.g. “1.23e‑3”) and European decimal comma (e.g. “1,23e‑3”).  
- Store all values internally in base SI units (e.g. volts, amperes) and display them in engineering notation with three significant digits by default.  
- If the input is invalid, prompt the operator again rather than aborting the test.  Use prompt() and read_measurement() that retries until the input parses successfully. Invalid entries are not accepted.


## Tests Common Checklist

- **Per‑device remote/manual default**: – Do not ask the user to choose remote vs manual. If not explicitly requested, default to manual (`<DEVICE>_REMOTE = False`) and do not emit any warnings/remarks about missing declarations.

- **Default to manual measurements**: – If no instrument is declared for a required measurement, the script must prompt the operator to measure manually.  Do not attempt to guess instrument parameters.

- **SI unit handling**: – For operator inputs, use `read_measurement()` with the robust units rules above.  Always normalise units and apply SI prefixes correctly.

- **Success criteria**: – Evaluate success conditions using the IDs specified in the test (e.g. `{1}`, `{2}`) and the tolerances or comparison operators given.  Support inclusive ranges (target ± tolerance), less‑than (<), greater‑than (>), and other simple comparisons.  Record PASS or FAIL for each ID.
- **Success-condition engine.**: Evaluate numerics exactly as written. Support arithmetic on IDs (e.g., {i}-{j}, {i}/{j}). Conditions that cannot be evaluated in code must be represented as operator_decision and resolved by an operator prompt.
- **Success-condition completeness.**: Every referenced ID must map to either (a) a machine-evaluated numeric rule or (b) an operator_decision. If any ID lacks one of these, stop code generation and prompt to complete the criteria.


- **Dual-branch emission (mandatory)**: — For every instrument action guarded by a runtime flag
   (`SCOPE_REMOTE`, `PSU_REMOTE`, `ELOAD_REMOTE`, …), the generator MUST emit:
   - a remote branch (SCPI/driver calls), and
   - an explicit manual branch with `prompt()` that covers configuration, arming/capture if applicable,
     measurement entry via `read_measurement()` when numeric, screenshot saving instructions when visual,
     and restoration to baseline.
   Missing a manual branch is a **generation error**.

- **Evidence parity**: — Any screenshot or file captured in the remote branch must have an identical filename
   and `add_evidence(...)` call in the manual branch. No remote-only evidence. (See also “Manual steps must
   always generate a prompt()”).

- **Manual safe-state**: — In `finally:` if a device is manual (flag is False), emit prompts to return it to a
   known safe state (e.g., PSU OUTPUT OFF, E-load OFF). Mirrors the remote safe-state calls.

- **Import policy (mandatory)**:
   - For any driver/helper provided by the `labscpi` package, imports MUST use the `labscpi.*` namespace.
   - Forbidden imports (generation error): `from psu_scpi import ...`, `from eload_scpi import ...`, `from oscilloscope_scpi import ...`, `from <controller_driver_package> import ...`, `from labscpi.Result import ...`, `from labscpi.test_helpers import ...`, `from Result import ...`, `from test_helpers import ...`.
   - Do not use import fallbacks (no `try/except ImportError`) for these modules.
   - Do not modify `sys.path` or rely on machine-specific filesystem paths in generated tests.


### Tolerance parsing: percent vs absolute

- **Accepted forms**:
  - `{n} = <value> ± <percent>%`   → percent tolerance
  - `{n} = <value> ± <abs>`        → absolute tolerance (units match `<value>`)
  - `{n} < <limit>` / `{n} ≤ <limit>` / `{n} > <limit>` / `{n} ≥ <limit>`

- **Evaluation rules**:
  - Percent tolerance: compute `tol = abs(value) * (percent / 100.0)`, then pass if `value - tol ≤ meas ≤ value + tol`.
  - Absolute tolerance: pass if `value - abs_tol ≤ meas ≤ value + abs_tol`.
  - Comparators: evaluate numerically with the same unit and coupling implied by the step.

- **Parsing notes**:
  - Allow optional spaces: `2.40 V`, `2.40V`, `±5 %`, `±5%` are equivalent.
  - Accept decimal comma in authored values (e.g., `2,40 V` → `2.40 V`) for evaluation.
  - Units must be consistent with the step’s measurement type; do not coerce units.

- **Errors**:
  - If both percent **and** absolute tolerance appear on the same line, abort code generation with an error:
    `ERROR: Conflicting tolerance formats in success condition for {n}.`

- **Operator decisions.**: Some success conditions cannot be automatically evaluated — for example, signal-integrity checks or visual assessments such as “is the waveform shape correct” or “does the screen image match the reference.”
These conditions must use operator_decision for PASS/FAIL entry.
Manual numeric readings (e.g., DMM values) remain evaluable and are not considered operator decisions.

- **Derived defaults.** When placeholders lack explicit tolerances, compute defaults defined by the test rules, e.g., `{BAUD_TOL} = ±5% of {BAUD}`, `{V_TOL} = ±5% of {V_DIFF}`; apply similar family-specific defaults as provided.

- **Exact controller command syntax** – Use the exact command syntax and protocol defined by the **active device profile** for all microcontroller operations. Do not invent new commands or sequences. Record the command sent and the response received.
- Manual steps are allowed but must always generate a `prompt()`. 
- No silent manual actions. Every manual step produces a prompt(); StepRecord logging alone is insufficient.

- **Precheck: driver present**
   - For each measurement, verify the access path exists:
      (a) Manual probe/lead connection for DMM/scope, and
      (b) Declared actuator+wiring if the node’s potential is driven.
   - Missing (b) ⇒ AMBIGUOUS; do not emit IDs or code.



## Script Structure and Helpers

The generated script must adhere to the following structure:

**Evidence constants:** Define all screenshot filenames once at the top and reuse verbatim in both branches:
stim1_waveform.png, ripple_ch2_steady.png, stim2_ripple.png, stim2_rise.png, q26_rising.png, bleed_trigger.png.

  - **Static linter (generation-time)** — Reject code if any `if <DEVICE>_REMOTE:` block lacks a matching
    `else:` with `prompt()` for the manual path. Also reject if a remote branch calls `screenshot_png()` or
    stores evidence without a same-name manual `add_evidence(...)`.

  - **Static validation (generation-time)** — The generator MUST NOT execute the generated test (no `run_test()`, no importing drivers to “verify imports”).
    Allowed validation is syntax-only compilation/parsing (e.g., `compile(source, "<generated>", "exec")` or `ast.parse(source)`) to catch syntax errors without running code.


1. **Parameter definitions** – At the top of the file (outside the main function), define variables for all required parameters: instrument addresses, channel numbers, timeouts, target values, tolerances, etc. Initialise them with the values provided by the user or `None` if missing.

2. **Startup check** – Inside the main test function, call a helper to verify that all required parameters are defined. If any parameter is `None`, raise an error instructing the user to edit the script and provide the missing values. Do not proceed with undefined parameters.

3. **Opening controller connection** – Open the controller per the selected controller driver pack / `{DEVICE_PROFILE}`. If any link parameters required by the driver pack are missing, fail the startup check and stop.

4. **Canonical sequence** – Perform the test steps in order: ensure the PSU is off, instruct the operator to connect probes/instruments, turn the PSU on, enable signals, inject stimuli, perform measurements, etc. Use SCPI for remote instruments and operator prompts for manual actions. For controller actions, use the selected controller driver pack rules. If controller parameters are missing, fail startup. After each oscilloscope measurement, take a screenshot.

5. **Evaluating results** – For each measurement ID, compare the measured value to its target and tolerance to determine PASS or FAIL. Store each verdict, measured value, and screenshot filename in the result object.

6. **Logging and return** – Maintain a log of every controller command and response. At the end of the test, return a result structure that includes:
- The sequence of actions and prompts executed.
- Each measurement value keyed by its ID.
- The PASS/FAIL/SKIPPED verdict for each ID.
- The log of controller commands and responses.

### 6.1) Exception handling (mandatory)
- Any unhandled exception during the test body **must**:
  1. Append two log entries: `EXCEPTION: <message>` and `TRACEBACK: <last traceback line>`.
  2. Force failure by inserting `verdicts[0] = "FAIL"` (reserved synthetic rule id `0`).
  3. Print results using the standard block (`RESULTS:` then `json.dumps(res.to_json(), indent=2)`) and exit the test function.
- This guarantees `overall = "FAIL"` under error conditions. A test that raised an exception **must not** report `PASS`.
- Resource shutdown still executes in `finally` and must not `return`.

> Implementation note: the JSON schema and dual-output contract remain unchanged; exceptions are recorded only in `log`, and the synthetic verdict enforces failure aggregation.

### 6.2) Resource cleanup (mandatory)
- Wrap the main test body in `try: … finally: …`. The `finally` block **must** run even if the function executes `return` earlier.
- Required actions in `finally`:
  1) Put instruments in a safe state (outputs OFF) if they were enabled.  
  2) Close controller and all remote instruments that were opened.  
  3) Guard each shutdown with `try/except` to avoid masking prior results.
- Do not `return` from `finally`.

**Template:**
```python
res.print_json()
return res
finally:
    try:
        if ELOAD_REMOTE: el.set_output(ELOAD_CHANNEL, False)
    except Exception: pass
    try:
        if PSU_REMOTE: psu.output(PSU_CHANNEL, False)
    except Exception: pass
    try:
        if fn and not CONTROLLER_MANUAL_OVERRIDE: fn.close()
    except Exception: pass
    try:
        if SCOPE_REMOTE and scope: scope.close()
    except Exception: pass
    try:
        if ELOAD_REMOTE and el: el.close()
    except Exception: pass
    try:
        if PSU_REMOTE and psu: psu.close()
    except Exception: pass
```


7. **Requirements and Post-test actions.** Treat these sections as **verbatim operator information**. Do not synthesize or convert them into SCPI/controller commands unless the contents are also present as explicit **Test steps**. Otherwise, display or log them unchanged.

### Façade first, raw SCPI only as fallback

- **Default:** Use the instrument façades for all actions:
  - `PowerSupply` for PSU
  - `ElectronicLoad` for e-load
  - `Oscilloscope` for scope
- **Fallback rule:** Use raw SCPI (`write_raw` / `query_raw`) only when the façade lacks the required method for a step written in the test.
- **Do not mix for one action:** For any single step, choose façade **or** raw. Never both.
- **Atomicity**: Do not chain multiple instrument actions on a single line. One call per line to improve auditability and diffs.
- **Order preservation:** Raw SCPI must keep the exact step order. No reordering to “prepare” or “optimize.”
- **Error handling:** Wrap raw SCPI in try/except; on error, fail the test with the command string included in the message.
- **Logging:** Log each raw command and response in `controller_log`/instrument log so evidence shows what ran.
- **Surface new needs:** If a raw command is used, add a `# TODO: add façade method <name>(...)` comment right above it.

#### Code mapping template

```python
# Preferred: façade
psu.set_voltage(CH, volts)
psu.set_current(CH, amps)
psu.output(CH, True)

# Fallback: raw SCPI (only if façade method missing)
try:
    psu.write_raw(f"SOUR{CH}:VOLT {volts}")
    psu.write_raw(f"SOUR{CH}:CURR {amps}")
    psu.write_raw(f"OUTP{CH} ON")
    instrument_log.append({"dev":"psu","cmds":[f"SOUR{CH}:VOLT {volts}", f"SOUR{CH}:CURR {amps}", f"OUTP{CH} ON"]})
except Exception as e:
    raise RuntimeError(f"PSU raw SCPI failed: {e}")
```

### Verification View (step ↔ code mapping)
Emit the **verification view** only when the user explicitly asks for it (e.g., they request "verification view", "step ↔ code mapping", or "per-step mapping output"). By default, do not emit the verification view.

Requirements (only when requested):
- **Request gate:** If the user did not ask for the verification view, do not output it (no placeholder section).
- **Step markers:** The generated code must include a step-marker comment line for every expanded procedure step `N` in authored order.
  - **Extractor matching:** A step marker is identified by the exact prefix `# Step N` (with `N` as a base-10 integer). The extractor may ignore any suffix text after `# Step N`.
  - **Canonical form:** Use `# Step N - <what & why>` as the step-marker line.
- **Per-step mapping output:** After code generation, output a per-step view where each section contains:
  - `STEP N: <verbatim step text>`
  - the code block associated with the step-marker line whose prefix matches `# Step N` (from that marker line up to, but not including, the next step-marker line whose prefix matches `# Step (N+1)`)
  - source line numbers for the code block
- **Macro handling:** If macros/directives exist, the verification view must be based on the **expanded procedure** (linear steps, no directives, all `{ID_EXPR}` resolved).
- **No execution:** The verification view is a review artifact; do not run hardware actions or import instrument drivers to produce it.
- **Output-only artifact:** Do not embed this view into the test procedure text. Do not add it as a runtime test step. It is emitted alongside the generated code for review.

### Output Contract (mandatory)

The executor must both **return** a `Result` object **and** print a canonical JSON block. The JSON is the source of truth for external harnesses.

#### What to emit
1. Call `res.print_json()` which prints a line `RESULTS:` followed by `json.dumps(res.to_json(), indent=2)`.
2. Then `return res`.

#### JSON schema (exact)
```json
{
  "test_name": "<string>",
  "measurements": { "<id>": <number|string> },
  "verdicts": { "<id>": "PASS" | "FAIL" | "SKIP" },
  "criteria": { "<rule_id>": { /* expanded rule */ } },
  "evidence": [ { "label": "<name>", "file": "<path>", "meas_id": <int|null> } ],
  "log": [ "<ordered messages>" ],
  "overall": "PASS" | "FAIL" | "SKIP" | "PARTIAL"
}
```

##### Rules
- **Dual output.** Both the `return`ed `Result` and the printed JSON are required. Any divergence from the schema is a violation.
- **Measurements.** Numeric values are in base SI units; strings may be used for free-text notes and for machine-collected message payloads (UART/CAN/etc.).
- **Verdicts.** Only `PASS`, `FAIL`, `SKIP`.
- **Criteria.** Expanded form produced by the rules engine.
- **Evidence.** Each item links a file to a label, with optional `meas_id` to bind it to a measurement. For scope measurements, include at least one evidence item (screenshot) and set `meas_id` to the corresponding ID.
- **Log.** Chronological operator prompts, inputs, controller commands, and responses.
- **Overall aggregation.**
  1) Any `FAIL` → `overall = "FAIL"`
  2) All `SKIP` → `overall = "SKIP"`
  3) All `PASS` → `overall = "PASS"`
  4) Mix of `PASS` and `SKIP` → `overall = "PARTIAL"`

#### Minimal code obligations
- `Result` implements:
  - `overall` as a computed property (no manual setting)
  - `to_json()` that emits the exact schema above
  - `print_json()` that prints the canonical JSON block
  - `add_evidence(label: str, path: str, meas_id: int | None = None)` to append one evidence item
- The main test function calls `res.print_json()` immediately before `return res`.



### Authoring `RULES` (LLM-safe)

Define success criteria in a single `RULES` dict. Each entry targets one measurement ID or an expression of IDs. The engine must evaluate these without ambiguity.

#### Rule types and fields
- `within_pct` — numeric target with ±% tolerance  
  - `{ "type":"within_pct", "ref": <id>, "target": <float>, "tol_pct": <float>, "units":"<str>", "expr":"<verbatim spec>" }`
- `range_abs` — open interval (lower < x < upper)  
  - `{ "type":"range_abs", "ref": <id>, "lower": <float>, "upper": <float>, "units":"<str>", "expr":"..." }`
- Comparators — `<`, `<=`, `>`, `>=`, `==` on a single ID  
  - `{ "type":"lt_abs"|"le_abs"|"gt_abs"|"ge_abs"|"eq_abs", "ref": <id>, "limit": <float>, "units":"<str>", "expr":"..." }`
- Binary expression vs limit — e.g., `{1}-{2} > 0.4`  
  - `{ "type":"lt_abs_expr"|"le_abs_expr"|"gt_abs_expr"|"ge_abs_expr"|"eq_abs_expr", "refs":[<id_i>, <id_j>], "limit": <float>, "units":"<str>", "expr":"..." }`
- Operator decision — qualitative checks (SI/visual)  
  - `{ "type":"operator_decision", "expr":"<what the operator judges>" }`

**String success conditions: subjective vs deterministic**
- **Subjective (operator observation):** If the success condition is `{n} = <TEXT>` and `{n}` is entered by an operator as an observation (free text, may be empty), then the script must ask the operator to validate the target text:
  - Collect observation (free text) for `{n}` (may be empty).
  - Ask: `Is the result for {n} "<TEXT>"? [y/n/skip]:`.
  - Use `operator_judgment(n, "<TEXT>", log)` when available.
  - Store the operator verdict under `verdicts[{n}]` (measurement-linked), even if the `RULES` entry uses a different rule id with `ref: n`.
- **Deterministic (machine-collected string):** If `{n}` is read automatically (driver/bus/UART/CAN/etc.), then `{n} = <TEXT>` is evaluated in code, not by operator judgment:
  - Compare `measured.strip()` to `expected.strip()` for exact matches.
  - Treat `<TEXT>` as a regex only when authored as `/.../`; evaluate with `re.search(pattern, measured.strip())`.
- **Empty/timeout:** For `{n} = empty or timeout`, PASS if a timeout occurs OR `measured.strip() == ""`; otherwise FAIL.

> Use `operator_decision` for non-quantifiable checks only. Numeric readings from manual instruments remain numeric rules.

#### Dynamic criteria resolution
Some limits depend on earlier measurements or ambient conditions. Encode them as *deferred* rules and resolve them before verdicts.

- **Relative to another measurement:**  
  Example `{5} = {1} ±5 %` →  
  ```json
  {"type":"defer_relative_pct","ref":5,"relative_to":1,"tol_pct":5}
Expanded at runtime into an absolute range_abs using measured {1}.

Relative to ambient:
Example {7},{8},{9} < limits °C above ambient {700} →

{"type":"lt_abs_expr","refs":[7,700],"limit":60.0}
Expansion occurs once before verdicts.
Missing prerequisites → mark that rule FAIL and log cause.

#### ID mapping
- Every measurement placeholder `{n}` in the procedure must map to exactly one rule entry (numeric or `operator_decision`).
- No orphan IDs. If any `{n}` lacks a rule, stop and request completion.

#### Numeric forms the LLM may encounter
- Target ± percent: `{n} = 2.40 V ± 5%` → `within_pct`
- Open range: `0.95 V < {n} < 1.05 V` → `range_abs`
- Comparator: `{n} < 10 ns` → `lt_abs`
- Difference vs limit: `{i} − {j} > 0.4 V` → `gt_abs_expr`

#### Units
- Preserve units in `expr` and `units`. Engine compares numerically in base SI. Do not coerce mismatched units.

#### Reserved, completeness, and failure forcing
- Reserve rule id `0` for synthetic FAIL on exceptions. The runner sets `verdicts[0]="FAIL"` when an error occurs.
- Before execution, expand `RULES` to internal `criteria` and fail fast if any required field is missing.

#### Example
```python
RULES = {
    1: {"type":"within_pct", "ref":1, "target":2.40, "tol_pct":5, "units":"V",
        "expr":"{1} = 2.40 V ± 5%"},
    2: {"type":"within_pct", "ref":2, "target":1.73, "tol_pct":5, "units":"V",
        "expr":"{2} = 1.73 V ± 5%"},
    3: {"type":"gt_abs_expr", "refs":[1,2], "limit":0.4, "units":"V",
        "expr":"{1} - {2} > 400 mV"},
    4: {"type":"range_abs", "ref":3, "lower":0.95, "upper":1.05, "units":"V",
        "expr":"0.95 V < {3} < 1.05 V"},
    5: {"type":"operator_decision", "ref": 4,
        "expr":"{4} = Ok with margin"}
}




## Additional Conventions and Rules

- **Connector polarity** – When connecting equipment to a pair of pins written as `P<x>/P<y>`, treat the first pin as positive (+) and the second as negative (−).

- **Two‑node measurements** – For instructions like “measure between NODE1 and NODE2,” interpret the measured value as NODE1 minus NODE2.  Place the positive lead on NODE1 and the negative lead on NODE2.

- **Descriptive IO naming** – Include any descriptive alias provided (e.g. `"PWM_EN"` or `"PGOOD"`) in comments or prompts alongside the canonical resource ID.  Use the canonical ID in commands.

- **Power‑good signals** – If a status signal (e.g. power good) is available as a microcontroller IO, always read it via the controller's interface that IO.  Do not measure it with a scope or ask the operator to observe it.

- **Ask when in doubt** – These rules are strict.  If the test procedure is unclear or missing information, pause and ask the user for clarification.  Never guess or make assumptions.  If instrument commands, connection details, or target values are unknown, you must obtain them before generating or executing code.
