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

checksum: 0fb76cfbd2ad9d4f9a58fa69b1103a6ad3acc9b6c1147db9efd67ebee91e9770
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

    @property
    def overall(self) -> str:
        vals = list(self.verdicts.values())
        if not vals: return "SKIP"
        if any(v == "FAIL" for v in vals): return "FAIL"
        if all(v == "SKIP" for v in vals): return "SKIP"
        if all(v == "PASS" for v in vals): return "PASS"
        return "PARTIAL"

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
        criteria: Dict[str, Any] = self.criteria or {}
        measurements: Dict[str, Any] = self.measurements or {}
        verdicts: Dict[str, Any] = self.verdicts or {}
        log_entries: List[Any] = self.log or []

        # Extract "Step ..." entries as procedure
        steps: List[str] = []
        for entry in log_entries:
            if isinstance(entry, str) and entry.startswith("Step"):
                steps.append(entry)

        # Build rows for the requirements table
        rows_html: list[str] = []
        for crit_id, crit in sorted(criteria.items(), key=lambda kv: kv[0]):
            expr = crit.get("expr", "")
            units = crit.get("units", "")

            # measurement id: use ref if present, else criterion id
            ref_id = crit.get("ref", crit_id)

            meas_val = measurements.get(ref_id, measurements.get(crit_id, ""))

            # verdict: prefer measurement-id verdict, else criterion-id verdict
            verdict = verdicts.get(ref_id, verdicts.get(crit_id, ""))

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
  </header>

  {steps_html}

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
        )

    @classmethod
    def from_json_file(cls, path: str) -> "Result":
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_json_dict(data)
