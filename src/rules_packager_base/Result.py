"""
---
doc_id: result-module-v1
title: Result Object for Test Runs
version: v1.0.0
status: active
audience: internal-test-automation
description: Canonical schema for verdicts, measurements, evidence, and JSON serialization.
related:
  - test-rules-llm-ready-v1
  - scpi-psu-api-v1
  - scpi-oscilloscope-api-v2
  - scpi-eload-api-v1
related_files:
  - rules/0.1.0/test_rules_llm_ready.md
  - rules/0.1.0/Result_API_Contract_v1.md
  - rules/0.1.0/Test_Helpers_API_Contract_v1.md
  - rules/0.1.0/LLM Automated Test Code Generation Gui.md

checksum: 5d2e2bcf6b21794fc661573db700294b307e1c132ee7f97e74e5afff21879c4a
---
"""

"""
Result.py

Defines the data structures and classes used to collect, store, and manage test results for automated and manual test procedures.
This module provides a standardized format for recording measurement values, operator verifications, verdicts, logs, and metadata.
It is intended to be used by test scripts and frameworks to ensure consistent result handling, reporting, and traceability across all test executions.
"""


from dataclasses import dataclass, field

import json
from typing import Any, List, Optional, Dict
from pathlib import Path
from html import escape


@dataclass
class Result:
    test_name: str = ""
    measurements: Dict[int, Any] = field(default_factory=dict)
    verdicts: Dict[int, str] = field(default_factory=dict)
    criteria: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)  # unified

    # Execution state (independent of pass/fail criteria)
    aborted: bool = False
    error: bool = False
    exception_type: str = ""
    exception_message: str = ""
    traceback_last: str = ""

    @property
    def criteria_overall(self) -> str:
        vals_any = list(self.verdicts.values())
        if not vals_any:
            return "SKIP"

        vals: list[str] = []
        unknown = False
        for v in vals_any:
            if not isinstance(v, str):
                unknown = True
                continue
            vals.append(v.strip().upper())

        if not vals:
            return "PARTIAL" if unknown else "SKIP"

        if any(v == "FAIL" for v in vals):
            return "FAIL"
        if all(v == "SKIP" for v in vals):
            return "SKIP"
        if all(v == "PASS" for v in vals):
            return "PASS"
        if all(v in ("PASS", "SKIP") for v in vals):
            return "PARTIAL"
        return "PARTIAL"

    @property
    def overall(self) -> str:
        # Execution status overrides criteria aggregation.
        if self.aborted:
            return "ABORTED"
        if self.error:
            return "ERROR"
        return self.criteria_overall

    def add_evidence(self, label: str, path: str, meas_id: Optional[int] = None):
        self.evidence.append({"label": label, "file": path, "meas_id": meas_id})

    def to_json(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "measurements": self.measurements,
            "verdicts": self.verdicts,
            "criteria": self.criteria,
            "evidence": self.evidence,
            "log": self.log,
            "aborted": self.aborted,
            "error": self.error,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "traceback_last": self.traceback_last,
            "criteria_overall": self.criteria_overall,
            "overall": self.overall,
        }

    def print_json(self) -> None:
        print("\nRESULTS:")
        print(json.dumps(self.to_json(), indent=2))


    def export_html(self, output: Optional[str | Path] = None) -> Path:
        """
        Export this Result as an HTML report.

        If 'output' is None, a file name is generated from test_name.
        Returns the Path to the written HTML file.
        """
        # Build file name if none is given
        if output is None:
            base = (self.test_name or "result").strip().replace(" ", "_")
            output_path = Path(f"{base}.html")
        else:
            output_path = Path(output)
            if output_path.suffix == "":
                output_path = output_path.with_suffix(".html")

        # Convenience aliases
        test_name = self.test_name or "Unnamed test"
        overall = self.overall or "UNKNOWN"
        criteria_overall = self.criteria_overall or "UNKNOWN"
        criteria: Dict[int, Dict[str, Any]] = self.criteria
        measurements: Dict[int, Any] = self.measurements
        verdicts: Dict[int, str] = self.verdicts
        log_entries: List[Any] = self.log

        exec_details_html = ""
        if self.aborted or self.error:
            details = "\n".join(
                [
                    f"exception_type: {self.exception_type}" if self.exception_type else "",
                    f"exception_message: {self.exception_message}" if self.exception_message else "",
                    f"traceback_last: {self.traceback_last}" if self.traceback_last else "",
                ]
            ).strip()
            if details:
                exec_details_html = f"""
  <section>
    <h2>Execution Details</h2>
    <pre>{escape(details)}</pre>
  </section>
"""

        # Extract "Step ..." entries as procedure
        steps: List[str] = []
        for entry in log_entries:
            if isinstance(entry, str) and (entry.startswith("STEP ") or entry.startswith("Step ")):
                steps.append(entry)

        # Build rows for the requirements table
        rows_html: list[str] = []
        for crit_id, crit in sorted(criteria.items(), key=lambda kv: kv[0]):
            expr = crit.get("expr", "")
            units = crit.get("units", "")

            # Measurement display (criterion id and measurement id are independent)
            meas_val: Any = ""
            if "ref" in crit:
                ref_raw = crit.get("ref")
                ref_id: int | None = None
                if ref_raw is not None:
                    try:
                        ref_id = int(ref_raw)
                    except Exception:
                        ref_id = None
                meas_val = measurements.get(ref_id, "") if isinstance(ref_id, int) else ""
            elif "refs" in crit:
                refs = crit.get("refs") or []
                try:
                    parts: list[str] = []
                    for mid_raw in refs:
                        try:
                            mid = int(mid_raw)
                        except Exception:
                            parts.append(f"{{{mid_raw}}}=")
                            continue
                        parts.append(f"{{{mid}}}={measurements.get(mid, '')}")
                    meas_val = ", ".join(parts)
                except Exception:
                    meas_val = ""
            else:
                # Fallback for legacy/simple criteria shapes
                meas_val = measurements.get(crit_id, "")

            # Verdicts are keyed by criterion id (no measurement-id fallback)
            verdict = verdicts.get(crit_id, "")

            verdict_class = ""
            if isinstance(verdict, str):
                v = verdict.upper()
                if v == "PASS":
                    verdict_class = "pass"
                elif v == "FAIL":
                    verdict_class = "fail"
                elif v == "SKIP":
                    verdict_class = "skip"

            rows_html.append(
                f"<tr>"
                f"<td class='id'>{escape(str(crit_id))}</td>"
                f"<td class='expr'>{escape(expr)}</td>"
                f"<td class='meas'>{escape(str(meas_val))}</td>"
                f"<td class='units'>{escape(units)}</td>"
                f"<td class='verdict {verdict_class}'>{escape(str(verdict))}</td>"
                f"</tr>"
            )

        # Procedure section (from "Step ..." lines)
        steps_html = ""
        if steps:
            steps_items = "\n".join(f"<li>{escape(step)}</li>" for step in steps)
            steps_html = f"""
        <section>
          <h2>Procedure</h2>
          <ol>
            {steps_items}
          </ol>
        </section>
        """

        # Full logs section
        logs_html = ""
        if log_entries:
            log_text = "\n".join(escape(str(entry)) for entry in log_entries)
            logs_html = f"""
        <section>
          <h2>Logs</h2>
          <pre>{log_text}</pre>
        </section>
        """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(test_name)} - Test Report</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 1.5rem;
      background: #f7f7f7;
    }}
    h1 {{
      margin-bottom: 0.2rem;
    }}
    .overall {{
      font-weight: bold;
      padding: 0.3rem 0.6rem;
      border-radius: 4px;
      display: inline-block;
    }}
    .overall.PASS {{
      background: #e4f7e4;
      color: #146314;
    }}
    .overall.FAIL {{
      background: #fde2e2;
      color: #8c1111;
    }}
    .overall.SKIP {{
      background: #eee;
      color: #555;
    }}
    .overall.PARTIAL {{
      background: #fff3cd;
      color: #6b4c00;
    }}
    .overall.ERROR {{
      background: #ffe5d0;
      color: #7a3b00;
    }}
    .overall.ABORTED {{
      background: #e6f0ff;
      color: #003a7a;
    }}
    .overall.UNKNOWN {{
      background: #eee;
      color: #555;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin-top: 1rem;
      background: white;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 0.4rem 0.6rem;
      font-size: 0.9rem;
    }}
    th {{
      background: #f0f0f0;
      text-align: left;
    }}
    tr:nth-child(even) {{
      background: #fafafa;
    }}
    td.id {{
      text-align: right;
      width: 3rem;
      white-space: nowrap;
    }}
    td.meas {{
      text-align: right;
      width: 8rem;
      white-space: nowrap;
    }}
    td.units {{
      text-align: left;
      width: 4rem;
      white-space: nowrap;
    }}
    td.verdict {{
      text-align: center;
      width: 6rem;
      font-weight: bold;
    }}
    td.verdict.pass {{
      color: #146314;
    }}
    td.verdict.fail {{
      color: #8c1111;
    }}
    td.verdict.skip {{
      color: #555555;
    }}
    section {{
      margin-top: 1.5rem;
    }}
    pre {{
      background: #222;
      color: #eee;
      padding: 0.8rem;
      border-radius: 4px;
      overflow-x: auto;
      font-size: 0.8rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(test_name)}</h1>
    <div class="overall {escape(overall)}">Overall: {escape(overall)}</div>
    <div class="overall {escape(criteria_overall)}">Criteria: {escape(criteria_overall)}</div>
  </header>

  {steps_html}

  {exec_details_html}

  <section>
    <h2>Requirements and Results</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Requirement</th>
          <th>Measurement</th>
          <th>Units</th>
          <th>Verdict</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </section>

  {logs_html}
</body>
</html>
"""

        output_path.write_text(html, encoding="utf-8")
        return output_path


    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> "Result":
        # JSON keys are strings → convert to ints for our Dict[int, ...] fields
        raw_meas = data.get("measurements", {}) or {}
        raw_verdicts = data.get("verdicts", {}) or {}
        raw_criteria = data.get("criteria", {}) or {}

        measurements: Dict[int, Any] = {int(k): v for k, v in raw_meas.items()}
        verdicts: Dict[int, str] = {int(k): v for k, v in raw_verdicts.items()}
        criteria: Dict[int, Dict[str, Any]] = {int(k): v for k, v in raw_criteria.items()}

        return cls(
            test_name=data.get("test_name", ""),
            measurements=measurements,
            verdicts=verdicts,
            criteria=criteria,
            evidence=data.get("evidence", []) or [],
            log=data.get("log", []) or [],
            aborted=bool(data.get("aborted", False)),
            error=bool(data.get("error", False)),
            exception_type=str(data.get("exception_type", "") or ""),
            exception_message=str(data.get("exception_message", "") or ""),
            traceback_last=str(data.get("traceback_last", "") or ""),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "Result":
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_json_dict(data)
