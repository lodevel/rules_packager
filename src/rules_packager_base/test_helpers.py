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
checksum: 16e7afb75bca1c6f36b9d589d7d17a92a7f1cf6e5959e1e335eb6fc47a5973bd
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

import re


def prompt(msg: str, log:list) -> str:
    print("\n" + msg.strip())
    log.append(msg.strip())
    ret = input("> ").strip()
    log.append(ret)
    return ret

def prompt_choice(msg: str, mapping: dict, log:list) -> str:
    while True:
        ans = prompt(msg, log).strip().lower()
        if ans in mapping: return mapping[ans]
        str = "Enter one of:", ", ".join(mapping.keys())
        print(str)
        log.append(str)


def read_logic_01(msg: str, log: list) -> int:
    """Prompt until the operator enters a strict 0/1 value."""
    return int(prompt_choice(msg, {"0": 0, "1": 1}, log))


_SI = {"y":1e-24,"z":1e-21,"a":1e-18,"f":1e-15,"p":1e-12,"n":1e-9,"u":1e-6,"µ":1e-6,"m":1e-3,
       "":1.0,"k":1e3,"K":1e3,"M":1e6,"G":1e9,"T":1e12,"P":1e15,"E":1e18,"Z":1e21,"Y":1e24}

def parse_quantity(s: str, default_unit: str = "V") -> float:
    s = s.strip().replace(",", ".")
    m = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-ZµΩOhms]*)\s*", s)
    if not m:
        raise ValueError("Invalid numeric input")
    val = float(m.group(1))
    unit = (m.group(2) or "").replace("Ohms","Ω").replace("ohms","Ω").replace("Ohm","Ω").replace("ohm","Ω")

    # If only a prefix was given (e.g., "10n"), apply it to the default unit.
    if unit in _SI:
        return val * _SI[unit]

    # If a base unit with optional prefix was given.
    if unit.endswith("V"):
        pre = unit[:-1]
        if pre in _SI:
            val *= _SI[pre]
        return val

    if unit.endswith("A"):
        pre = unit[:-1]
        if pre in _SI:
            val *= _SI[pre]
        return val

    # Time unit with optional SI prefix (ms, us, ns, s)
    if unit.endswith("s") or unit.endswith("S"):
        pre = unit[:-1]
        if pre == "":
            return val
        if pre in _SI:
            return val * _SI[pre]
        raise ValueError("Unrecognized time unit")

    # Fallback: unrecognized unit, return numeric part unchanged.
    return val

def read_measurement(msg: str, log: list, default_unit: str = "V") -> float:
    while True:
        try: return parse_quantity(prompt(msg, log), default_unit)
        except Exception as e: 
            str = f"Invalid input: {e}. Use SI units (e.g., 2.40V)."
            print(str)
            log.append(str)


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

