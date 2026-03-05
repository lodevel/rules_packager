"""
---
doc_id: test-helpers-v1
title: Operator Prompt and Measurement Helpers
version: v1.0.0
status: active
audience: internal-test-automation
description: prompt(), prompt_choice(), parse_quantity(), read_measurement(); operator I/O and unit parsing.
related:
  - result-module-v1
  - test-rules-llm-ready-v1
related_files:
  - Result.py
  - rules/0.1.0/test_rules_llm_ready.md
checksum: 1b63e302f310c764032ab2b7cd1b643ef9824ad10d2fb694b9dd8a7e79f95602
---
"""
"""
test_helpers.py

This module provides utility functions and helpers to support automated test code generation and execution.
It includes routines for prompting operator input, parsing measurement values, handling manual verifications,
and collecting results in a consistent format. These helpers are designed to be used by generated test scripts
and test frameworks to ensure reliable data collection, operator interaction, and result logging for both
automated and manual test steps.
"""

import json
import re
import signal
import traceback

from .Result import Result

# On Windows, CTRL_BREAK_EVENT → SIGBREAK terminates the process by default
# (no Python exception, no finally).  Re-route it through default_int_handler
# so it raises KeyboardInterrupt instead — catchable by the test script's
# except BaseException handler, letting finalize_partial_results /
# checkpoint_results save partial results before exit.
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, signal.default_int_handler)


def prompt(msg: str, log:list) -> str:
    print("\n" + msg.strip())
    log.append(msg.strip())
    ret = input("> ").strip()
    log.append(ret)
    return ret

def prompt_choice(msg: str, mapping: dict, log:list) -> str:
    while True:
        ans = prompt(msg, log).strip().lower()
        if ans in mapping:
            ret = mapping[ans]
            return ret if isinstance(ret, str) else str(ret)
        msg2 = "Enter one of: " + ", ".join(mapping.keys())
        print(msg2)
        log.append(msg2)


def read_logic_01(msg: str, log: list) -> int:
    """Prompt until the operator enters a strict 0/1 value."""
    return int(prompt_choice(msg, {"0": "0", "1": "1"}, log))


_SI = {"y":1e-24,"z":1e-21,"a":1e-18,"f":1e-15,"p":1e-12,"n":1e-9,"u":1e-6,"µ":1e-6,"m":1e-3,
       "":1.0,"k":1e3,"K":1e3,"M":1e6,"G":1e9,"T":1e12,"P":1e15,"E":1e18,"Z":1e21,"Y":1e24}

def parse_quantity(s: str, default_unit: str = "V") -> float:
    s = s.strip().replace(",", ".")
    m = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-ZµΩOhms]*)\s*", s)
    if not m:
        raise ValueError("Invalid numeric input")
    val = float(m.group(1))
    unit = (m.group(2) or "").replace("Ohms","Ω").replace("ohms","Ω").replace("Ohm","Ω").replace("ohm","Ω")

    # Returns float only; unit semantics are not preserved.
    # Scaling rule:
    # - If suffix is exactly a supported SI prefix (e.g., "m", "k"), apply it.
    # - Else if suffix starts with a supported 1-char prefix (e.g., "mV", "ms", "kHz", "MΩ"), apply it and ignore the rest.
    # - Else return numeric part unchanged.
    if unit in _SI:
        return val * _SI[unit]

    if unit:
        pre = unit[:1]
        if pre in _SI and pre != "":
            return val * _SI[pre]

    return val

def read_measurement(msg: str, log: list, default_unit: str = "V") -> float:
    while True:
        try: return parse_quantity(prompt(msg, log), default_unit)
        except Exception as e: 
            msg2 = f"Invalid input: {e}. Use SI units (e.g., 2.40V)."
            print(msg2)
            log.append(msg2)


def operator_judgment(meas_id: int, target: str, log: list) -> tuple[str, str]:
    observation = prompt(
        f'Observation for {{{meas_id}}} (target: "{target}"). Free text (may be empty):',
        log,
    )
    verdict = prompt_choice(
        f'Is the result for {{{meas_id}}} "{target}"? [y/n/skip]: ',
        {"y": "PASS", "n": "FAIL", "skip": "SKIP"},
        log,
    )
    return observation, verdict


def checkpoint_results(res: Result, json_path: str = "results.json", html_path: str = "results.html") -> None:
    """Best-effort persistence of partial results; never raises."""
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(res.to_json(), f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        res.export_html(html_path)
    except Exception:
        pass


def finalize_partial_results(
    res: Result,
    exc: BaseException | None = None,
    *,
    kind: str | None = None,
    missing_verdict: str = "SKIP",
) -> None:
    """Finalize Result without constraining criterion logic.

    This helper exists to enforce durable partial reporting behavior without
    assuming any specific criterion types.

    - If exc is provided, marks execution state (ABORTED or ERROR) and records
      exception metadata on the Result.
    - Ensures every criterion id in res.criteria has a verdict key. Missing
      verdicts become missing_verdict (default: SKIP).
    - Never raises.
    """
    try:
        mv = str(missing_verdict or "SKIP").strip().upper()
        if mv not in ("PASS", "FAIL", "SKIP"):
            mv = "SKIP"

        if exc is not None:
            try:
                inferred = "ABORTED" if isinstance(exc, (KeyboardInterrupt, EOFError, SystemExit)) else "ERROR"
                k = str(kind or inferred).strip().upper()
                if k not in ("ABORTED", "ERROR"):
                    k = "ERROR"

                res.aborted = (k == "ABORTED")
                res.error = (k == "ERROR")
            except Exception:
                pass

            try:
                res.exception_type = type(exc).__name__
                res.exception_message = str(exc)
            except Exception:
                pass

            try:
                tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
                res.traceback_last = tb_lines[-1].strip() if tb_lines else ""
            except Exception:
                pass

            try:
                prefix = "ABORTED" if getattr(res, "aborted", False) else "ERROR"
                res.log.append(f"{prefix}: {type(exc).__name__}: {exc}")
                if getattr(res, "traceback_last", ""):
                    res.log.append(f"TRACEBACK: {res.traceback_last}")
            except Exception:
                pass

        # Normalize existing verdict tokens; fill missing verdicts with mv.
        try:
            for k, v in list((res.verdicts or {}).items()):
                if isinstance(v, str):
                    v_up = v.strip().upper()
                    if v_up in ("PASS", "FAIL", "SKIP"):
                        res.verdicts[k] = v_up
        except Exception:
            pass

        try:
            for crit_id in (res.criteria or {}).keys():
                if crit_id not in res.verdicts:
                    res.verdicts[crit_id] = mv
        except Exception:
            pass

    except Exception:
        pass
