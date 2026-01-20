---
doc_id: test-rules-llm-ready-v1
title: LLM-Ready Test Rules and Templates
version: v1.2.0
status: active
created: 2025-11-05
updated: 2026-01-06

maintainer: esd.dev-QA
audience: internal-test-automation
description: Canonical authoring rules, step syntax, IDs, and success-condition forms for LLM-generated tests.
related:
  - llm-test-codegen-gui-v1
  - scpi-psu-api-v1
  - scpi-oscilloscope-api-v1
  - scpi-eload-api-v1
  - controller-driver-pack

checksum: 
34945575319128ac1de3c558d6461f665e4abf1c3c4bafbb13965a15fca0919d
# General Rules for Writing Tests (LLM‑ready)

This document consolidates the canonical writing rules for test procedures that will be generated or edited by a language model. It also clarifies how external inputs (setup, preconditions, **requirements**, **post‑test actions**) relate to those rules, and includes a short worked example for human readers.


## 1) Scope and Audience
- These rules govern **how test documents are written** for consistent parsing by a model.
- They apply to **all test families**; each family may add **narrow overrides** (never contradictions).
- They are **format rules** only. Actual test parameters are provided by a human or by upstream systems.


## 2) Allowed Sections (and only these)
Use **only** the following section names. Sections may be omitted if not supplied by the human.

**Core (authored by the model):**
1. **Id**
2. **Title**
3. **Description**
4. **Test steps**
5. **Success conditions**

**External inputs (human‑provided, pass‑through only):**
- **Board** — identifies the target board/DUT for the test (e.g., `PPU-MAIN-REV2`). Do **not** invent; omit if not supplied.
- **Requirements** — supplied verbatim by a human. Do **not** synthesize or summarize.
- **Post‑test actions** — supplied verbatim by a human. Do **not** synthesize or summarize.

> Do **not** add “Preconditions” or “Setup” unless a **verbatim** “Preconditions” block is explicitly provided for that specific test. All PSU setup/config must appear **inside** *Test steps*.


## 3) Zero‑Invention Policy
- Never invent values, steps, nodes, tolerances, images, or reference pins.
- Do not populate **Requirements** or **Post-test actions** unless the human supplied them; if absent, simply omit these sections.
- If something else is missing, either (a) ask for it, or (b) use an explicit **placeholder** (see §5) if placeholders are acceptable for that usage.
- Do not silently “fix” typos or ambiguities—flag them or ask.
- If a human-supplied step is ambiguous, incomplete, or non-standard (e.g., “Connect EPO and SR power” without pin numbers or connection details), the model must **not invent or assume missing details**.  
  - The model must instead ask the user to clarify the missing information.  
  - If the user confirms that the step is correct as written and will be clear for the operator in context, then the step may be kept unchanged.  
  - The model must never “repair” such steps on its own or infer wiring, pinouts, or procedures that were not explicitly provided.  
  - **Ambiguous action steps never generate measurement IDs or success conditions.**


## 4) Setup & Preconditions (External Inputs)
- **Setup** and **Preconditions** are **external, human‑provided** and are **not part of the rules** themselves.
- They do **not** influence how rules are applied; they are placeholders for additional information supplied from outside the test text.
- If a “Preconditions” block is provided **verbatim**, include it unchanged; otherwise, do **not** create or infer one.
- **All PSU configuration and enabling** steps must still live under **Test steps**.



## 5) Placeholders and Measurement IDs

### Placeholders (parameters)
- Use placeholders for any unspecified value or resource as `{{NAME}}`, e.g. `{{VIN}}`, `{{ILIM}}`, `{{ENABLE_PIN}}`, `{{TP_VOUT}}`, `{{BAUD}}`, `{{BAUD_TOL}}`, `{{V_DIFF}}`, `{{V_TOL}}`, etc.
- Placeholder names must match `[A-Za-z_][A-Za-z0-9_]*` (case-sensitive).
- Legacy placeholder form `{NAME}` may appear in older procedures; it is tolerated but should be migrated to `{{NAME}}`.

### Measurement IDs
- Bind every recorded/measured value to a unique measurement ID written as `{ID_EXPR}` where `ID_EXPR` resolves at macro-compile time to a **non-negative integer** (0 allowed).
- When not using macros, prefer literal IDs `{0}`, `{1}`, `{2}`, … in increasing order of appearance.
- In **Test steps**, measurement IDs are introduced only by the explicit pattern: `... as {ID_EXPR}`.
- In **Success conditions**, `{ID_EXPR}` references measurement IDs and may appear in arithmetic expressions (e.g., `{1} - {2} > 400 mV`).
- **Success conditions** must reference measurement IDs only for measured values (not raw instrument names).

### Range shorthands (optional; expands before validation)
These are a compact alternative to `@FOR` for simple repetitive measurements.

- **Token range:** `TOKEN[A..B]` where `TOKEN` contains no spaces and `A` and `B` are non-negative integers.
  - Expands to `TOKENA`, `TOKEN(A+1)`, …, `TOKENB` (concatenation, no separator).
  - Example: `VMONI[1..3]` → `VMONI1`, `VMONI2`, `VMONI3`.

- **ID range:** `{A..B}` where `A` and `B` are non-negative integers.
  - Expands to `{A}`, `{A+1}`, …, `{B}`.

- **Zipped expansion (required when both are present):**
  - If a step contains one token range and one ID range (e.g., `Measure TP VMONI[1..3] as {1..3}.`), they must have the same length and expand 1:1 in order.

Constraints:
- Ranges are inclusive: `A..B` includes both endpoints.
- Reject if `A > B`.
- Allow at most one `TOKEN[A..B]` and at most one `{A..B}` per line; use the macro DSL for more complex repetition.


## 5A) Procedure Macro DSL (compile-time directives)

This macro layer allows loops, tables, and compile-time conditionals while preserving deterministic expansion and stable measurement ID meaning.

### Definitions
- **Authored procedure**: a human-written procedure that may contain normal lines plus macro directive lines.
- **Expanded procedure**: a linear list of steps/conditions with no directives and with all `{ID_EXPR}` resolved to concrete integers.
- **Compile-time determinism**: macro constructs must be evaluable without running the test.

Allowed compile-time inputs:
- constants from `@LET`
- loop indices
- table rows
- `COUNT(<table>)`

Forbidden in expressions:
- runtime measurements
- operator input
- external state

### Where directives are allowed
- Directive lines are allowed **only** inside **Test steps** and **Success conditions**.
- A directive line is any non-empty line whose first non-whitespace character is `@`.

### Directive syntax

`@LET`
- `@LET NAME = EXPR`

`@TABLE` / `@ROW` / `@ENDTABLE`
- `@TABLE NAME`
- `@ROW NAME key=value key=value ...`
- `@ENDTABLE`
- Row iteration order is the authored (insertion) order.
- Row keys must match `[A-Za-z_][A-Za-z0-9_]*`.
- Row values are either bare tokens (no spaces) or double-quoted strings (spaces allowed). Use `\"` to escape quotes inside quoted values.
- Row field access uses dot syntax in macro substitution: `${row.key}`.

`COUNT(TABLE)`
- Returns the number of `@ROW` entries in `TABLE`.
- Empty tables are invalid and must be rejected.

`@FOR` / `@ENDFOR`
- Table loop: `@FOR i, row IN TABLE` ... `@ENDFOR`
- Range loop: `@FOR i IN A..B` ... `@ENDFOR` where `..` is **inclusive**.
- Loop indices are **0-based**. For table loops, `i` starts at 0 for the first row.
- Name shadowing is forbidden: redefining a name already in scope is a compile-time error.

`@IF` / `@ELSE` / `@ENDIF`
- Compile-time conditional. The condition expression must be evaluable at compile time.

### Expressions
Supported operators: `+ - * / %`, comparisons, boolean `AND OR NOT`.
`ID_EXPR` must evaluate to a non-negative integer.

### Macro substitution
- Use `${...}` for macro substitution in normal (non-directive) lines, e.g. `${row.io}`, `${BASE + i}`.
- Placeholders `{{NAME}}` are inert tokens and are not evaluated by the macro engine.

### Allocation (`@ALLOC`) semantics (normative)

`@ALLOC` always performs two actions:
1) Binds a compile-time variable (the base) to the first measurement ID of an allocated block.
2) Reserves a contiguous range of measurement IDs so no other allocation or `{ID_EXPR}` may use them.

IDs are not created by `@ALLOC` itself. Measurement IDs are created only when used in step/expected lines (e.g., `as {BASE + i}`).

Let `G` be the global measurement-ID cursor (initial value: **0**). `G` advances monotonically and is affected only by `@ALLOC`.

- Auto allocation: `@ALLOC BASE = K`
  - `BASE := G`
  - Reserve IDs `[BASE .. BASE + K − 1]`
  - Set `G := BASE + K`

- Manual allocation: `@ALLOC BASE START=S COUNT=K`
  - `BASE := S`
  - Reserve IDs `[BASE .. BASE + K − 1]`
  - Set `G := BASE + K`

Constraints:
- `K` must be a positive compile-time integer (tables with `COUNT(...) = 0` are invalid).
- Allocated ID ranges must not overlap each other.
- All `{ID_EXPR}` in the procedure must resolve to unique IDs and must not fall inside a reserved range unless explicitly derived from its `BASE`.

### Expansion and validation
- Macros expand in authored order.
- The compiler must reject: unknown variables, non-deterministic expressions, duplicate IDs, overlapping allocations, orphan expected IDs, empty tables, and forbidden shadowing.


## 6) Step‑Writing Style (NRS: *No Rationale in Steps*)
- Write steps as imperative sentences, one action per step.  
- Always keep steps short and execution-oriented (no explanations, no rationale).  
- Never merge multiple actions into one step.  
- Use sequential ordering; the test must be executable top-to-bottom. 
- **Strict order preservation (no reordering).**
  The generated procedure and code must preserve the **relative order** of all actions exactly as written. 
  Do not move, merge, or interleave steps (e.g., do not arm/enable a PSU or assert an IO earlier or later for “safety” or “convenience”). 
  If the written order appears unsafe or inconsistent, **stop and ask the user to revise the text** rather than reordering. 
- Assign measurement IDs `{ID_EXPR}` in authored order. When using literal IDs, prefer `{0}`, `{1}`, `{2}`, … in increasing order.  
- IDs are unique and never reused inside a test.  
- Assign IDs only to measurable values.  
- Action-only steps (e.g., “Turn PSU output ON”) never get IDs.  
- Do not describe instruments, brands, or code in the steps; keep them operator-agnostic.  
- Refer to nodes exactly as given by the user; never rename or shorten them.  
- Always specify coupling (DC/AC) when applicable.  
- The model must scan for ambiguous action steps before rewriting; if found, stop and ask the user for clarification (see §3). Never proceed to rewrite until clarified.
- **Control actions on TPs (test points):** A TP is passive. Writing “Set TP <node> to ‘0/1/High/Low’” is **ambiguous** unless the **actuator** is specified.
  - If controlled by a controller driver: use that driver’s step syntax (see controller driver pack).
  - If by jumper/wiring: “Connect TP <node> to GND / 3.3 V (specify jumper/reference).”
  - If by external source: “Drive TP <node> to 0 V using source CH1, limit <Ilim>, for <duration>.”
  - A TP may be driven to a **voltage** (with actuator + limits), but assigning a **logic state** to a TP without context does **not** make sense.
  - If a human step says “Set TP <node> to ‘0/1/High/Low’” without actuator, **stop and ask for clarification** (see §3).


### Wiring vs. Power-On (mandatory separation)
- Every actuator must be introduced in **two or more explicit steps**:
  1. **Connect** — declare wiring to the node(s) with the actuator output **OFF**.
  2. **Configure** — set voltage/current/duty/limits while output remains **OFF**.
  3. **Apply/Enable** — explicitly turn the actuator output **ON** or assert the IO/DAC after wiring/configuration.
- **Forbidden shorthand**: Steps like “Apply 28 V between P5 and P4” are invalid.  
  They must be split into:
    - “Connect PSU to P4 (+SR_28V) and P5 (GND), output OFF.”
    - “Configure PSU to 28 V / {ILIM}.”
    - “Turn PSU output ON.”
- **Loads** follow the same pattern: “Connect load … OFF” → “Configure load …” → “Enable load …”.
- **Ties** must be explicit: e.g. “Tie TP EPO_SR to +SR_28V (from Step N).”
- The generator must never delay, merge, or silently reorder “Apply” steps to satisfy safety; if missing Connect/Configure, the step is **non-compliant** and must be flagged for user revision.

- **Manual vs remote is a code-generation concern.**  
  Do not insert `[MANUAL]` or `[REMOTE]` tags in the written test unless the human text already contains them.  
  Keep steps actuator-agnostic. At **code generation time**, the executor decides per step:  
    • If a declared remote instrument can perform the action, emit SCPI.  
    • Otherwise emit a blocking `prompt()` for the operator. Logging alone is non-compliant.

- **Actuator inference:**
  - Explicit SCPI instruments ⇒ REMOTE
  - Bare TP/P/J/U/IC/R/C/L nodes ⇒ MANUAL
  - **Controller resources** (e.g., tokens like `IO#...`, `ADC#...`, `DAC#...`, `PWM...`, `UART...`) ⇒ interpret only using the selected controller driver pack(s).
If a step appears to mix a TP and a controller resource for the same control, mark it AMBIGUOUS and stop. Do not generate code or IDs until clarified.

- **Controller driver packs (mandatory)**
  - The base rules do **not** define controller syntax.
  - Each enabled controller driver pack defines:
    - Accepted step syntax and token grammar
    - How to extract controller identity and target (if applicable)
    - How to map steps to generated code
  - If a controller-like token is present but no enabled controller driver pack matches it, stop and ask the user which controller/driver applies.


- **Actuator mapping:**
  - Never assume which PSU channel or source drives a connector pin (e.g. "P21"), a TP, a pad of a component, etc... .
  - **No implicit actuator introduction.**
  Do not introduce a second supply or source on a node that already has a declared actuator unless the step **explicitly** commands it.
  Prefer **reconfiguring the existing actuator** over adding a new one.
  - If the procedure does not explicitly state "Connect PSU CHx to Pnn", treat any later
    instruction like "Set Pnn to <voltage>" as AMBIGUOUS.
  - Do not generate code or IDs for such steps until the user specifies the actuator and wiring.
  - **Single active actuator per node (PSU/AWG/controller).**
  At any moment, a given node (TP/connector/pin) may have **at most one driving actuator** connected and enabled.
  The generator must **reuse the same declared actuator** to change a setpoint (e.g., 32 V → 9 V) unless the test explicitly orders a different actuator.

  - **Actuator handover protocol (when the text explicitly switches sources).**
    If the procedure instructs changing which actuator drives a node, insert **manual prompts** that enforce this sequence:
    1) Turn the existing actuator **output OFF**.  
    2) **Disconnect** its leads from the node.  
    3) Connect the new actuator (output **OFF**).  
    4) Configure the new setpoint/current limit.  
    5) Turn the new actuator **output ON**.
    Never allow two supplies to remain connected to the same node simultaneously with outputs ON.

- **Measurement access path:**
  - Never measure on a connector or node whose potential depends on an undeclared actuator.
  - If the procedure has not previously declared the actuator and wiring that establish the node’s level
    (e.g., a PSU channel tied to Pnn, an AWG driving TP_x, a jumper to +SR_28V), any step like
    “Measure … on <connector/node>” is AMBIGUOUS.
  - Do not assign an ID or success condition to such a step. Ask the user to specify the actuator and wiring,
    then insert the wiring steps (outputs OFF → configure → outputs ON) before the measurement.

- **No inference from naming**:
  - Do not assume an actuator (PSU, controller IO, jumper, AWG, etc.) based on the node name
    or alias (e.g., "EPO_CTRL", "VBAT_PSU").
  - If the procedure says “Apply/Set X on TP/Pin <name>” but does not specify the actuator,
    mark the step AMBIGUOUS.
  - Only proceed once the user has explicitly identified the actuator and wiring.




## 7) Measurement Wording (Critical)
- **Single‑point measurement (implicit reference):**  
  *“Measure voltage on/at `<node>` as `{n}`.”*  
  Do **not** name a reference node unless the user provided one.
  - If no subtype is given, interpret the measurement as **mean voltage (DC-coupled)**.  
  - If the measurement is RMS, pk, pk-pk, or amplitude, the subtype must be explicitly stated in both the step and the success condition.
- **Two‑point (differential) measurement:**  
  *“Measure voltage **between** `<point A>` and `<point B>` as `{n}`.”* with the **sub-type of voltage** (mean, RMS, pk-pk, amplitude) always stated.
  Always use **between**, never “from … to …”.
- Do **not** convert single‑point ↔ two‑point unless explicitly requested.
- **Default for DC voltage**:
  - If a step says “Measure DC voltage on TP <node>” with no further qualifier, interpret this as
    a manual DMM measurement by default, not an oscilloscope measurement.
  - If oscilloscope usage is intended, the step must explicitly say so (and include screenshot
    or waveform requirements).

- **Wiring prerequisite for driven nodes**:
  - If a measurement targets a node that is expected to be driven (connector pins P#, J#, powered nets, or TPs
    that are not self-biased), the test must include prior steps that declare the driving source and its wiring.
  - Without those prior steps, treat the measurement as AMBIGUOUS and halt rewriting until clarified.


- **Non-voltage metrics (time, frequency, etc.):**
  These are self-describing (rise time, delay, frequency, duty cycle, …) but must still be written explicitly.

When a step configures the oscilloscope, include coupling, V/div, offset, timebase, trigger source, and slope. Each measurement must name the channel or MATH source.

---

## 8) Instrumentation Policy
- **SPPN — Single Probe Per Node (required):** One scope probe per physical node for the whole test. For multiple metrics on the same node, **re‑use the same channel** and reconfigure it.

- **Oscilloscope probe setup**:
  - Every oscilloscope measurement must be preceded by an explicit manual operator step
    to connect the probe to the specified TP/node and reference to GND.
  - This probe connection step must be included in the written test and must generate
    a prompt() in code.
  - The oscilloscope SCPI configuration and measurement steps come only after the probe
    connection is confirmed.

- **Coupling:**  
  - **DC (default if omitted):** mean, amplitude, rise-time, PG, delays, baud/bit timing.  
  - **AC (must be explicit):** ripple/noise (switch to AC before autoscale).  
  - Any valid combination is allowed if both the **coupling** and the **voltage subtype** are explicitly stated in the step.
- **Autoscale:** **vertical only**, allowed only in steady state (never on one‑shot events).
- **Differential math:** If a difference is required, define **MATH = CH1 − CH2** and measure on **MATH** inside the scope.
- **Timebase default:** Use **5 ms/div** when a timebase is needed and none is provided (unless a family override applies).
- Save **screenshots** after scope measurements if screenshots are part of your project’s evidence policy.


### “Vertical scale and offset (mandatory)”

- For every scope setup step, specify V/div and offset for each visible channel.

- **Derivation rule (DC‑coupled levels)**:

  - Let V_TARGET be the expected DC level for that channel (e.g., {VOUT_NOM}, {PG_LEVEL}).
  - Set V_DIV = nice125(V_TARGET / 3) so the level sits ≈ three divisions above 0 V.
  - Set OFFSET = 0 V when within instrument range; if not possible, set offset so the mean of the trace is centered.
  - Examples: PGOOD = 3.3 V → 1 V/div; VOUT = 28 V → 10 V/div.

- Ripple/noise at steady state: AC‑coupled with vertical‑only autoscale. If autoscale is unavailable, choose V_DIV so ripple spans 60–80% screen height.

Keep existing constraints: explicit coupling; autoscale only in steady state; SPPN applies.


---

## 9) Ordering & Sequencing

- **IO timing follows the text.**
  Assertions/deassertions of controller I/Os must occur exactly where written relative to PSU enables/disables and measurements.
  Do not pull IO steps earlier or later to “prepare” a condition; ask the user to change the step order if needed.

- Typical order:  
  1) Connect wiring with PSU OFF.  
  2) Configure PSU setpoints (still OFF).  
  3) Turn PSU ON.  
  4) Configure and arm instruments.  
  5) Assert `{ENABLE_PIN}` or other I/Os via the selected controller driver.  
Never instruct wiring while a rail is energized.
- For serial/bus tests: always configure and arm the oscilloscope before sending or enabling interface traffic. The canonical order is: scope setup → trigger arm → controller/SCPI stimulus. This guarantees that the first frame or edge is captured.


---

## 10) Power‑Good (PG) Declaration
- The human must specify whether PG is a **test point for the scope** or a **controller I/O** (read via the selected controller driver).
  - If PG is an **I/O**, **do not** create a TP/CH2 step; write steps as “via pin IO#…”.

---

## 11) Defaults (only when unspecified)
- **UART:** `{BAUD}` 8N1, no flow control.  
- **Differential amplitude:** `{V_TOL} = ±5%` of `{V_DIFF}` (if `{V_DIFF}` is a placeholder, keep the tolerance as a percentage).  
- **Baud tolerance:** `{BAUD_TOL} = ±5%` of `{BAUD}`.  
- **Temperature (when applicable):** measure `{AMBIENT_TEMP}` and `{DUT_TEMP}` at steady state; default limit **ΔT ≤ 30 °C**.  
- **PSU current limit:** if `{ILIM}` is not provided, use the PSU’s **maximum** (no current limit).
- {CH1_VDIV} = nice125({VOUT_NOM} / 3)
- {CH1_OFFS} = 0 V (use centered offset if 0 V not possible)
- If {TP_PGOOD} present:
  - {CH2_VDIV} = nice125({PG_LEVEL} / 3)
  - {CH2_OFFS} = 0 V
- If {PG_LEVEL} not provided, use {CH2_VDIV} = 1 V/div and {CH2_OFFS} = 0 V and mark as a placeholder to confirm.
- Ripple steps: AC‑coupled + vertical‑only autoscale by default.


---

## 12) Success Conditions (Strict Format)
Each line uses an **ID** plus a comparator and value/tolerance (IDs may start at `{0}`), e.g.:
- `{1} = 3.30 V ± 50 mV`
- `{2} < 50 mV pk-pk`
- `{3} = 500 kHz ± 10 kHz`

If the human supplied values, write them **directly** in the success conditions (no placeholders there).

- If a success condition uses `V` with no subtype, it shall be interpreted as **mean voltage (DC-coupled)**.  
- For RMS, pk, pk-pk, or amplitude, the subtype must always be explicitly written (e.g., `Vrms`, `Vpk`, `Vpk-pk`).
- Range shorthand is allowed at the start of a line as `{A..B} <expr>` and expands to one line per ID with identical RHS, e.g. `{1..3} = 2.15V±2%` → `{1} = 2.15V±2%`, `{2} = 2.15V±2%`, `{3} = 2.15V±2%`.
- **String equality success conditions:** A success condition may be authored as `{n} = <TEXT>`.
  - **Subjective (operator observation):** If `{n}` is entered by an operator as an observation (free text, may be empty), then `{n} = <TEXT>` is validated by an operator decision (PASS/FAIL/SKIP), not by string equality.
    - Collect a free-text operator observation for measurement `{n}` (may be empty), and include the target text in the prompt.
    - Ask the operator: `Is the result for {n} "<TEXT>"? [y/n/skip]:`
    - Store the operator decision as `PASS`/`FAIL`/`SKIP` under `verdicts[{n}]`.
    - Use `operator_judgment(meas_id, target, log)` from `rules_packager` when available.
  - **Deterministic (machine-collected string):** If `{n}` is read automatically (e.g., from UART/CAN/I2C/SPI/driver API), then `{n} = <TEXT>` is evaluated in code:
    - Compare `measured.strip()` to `expected.strip()` for exact matches.
    - Treat `<TEXT>` as a regex only when authored as `/.../`; evaluate with `re.search(pattern, measured.strip())`.
  - **Empty/timeout:** For `{n} = empty or timeout`, PASS if a timeout occurs OR `measured.strip() == ""`; otherwise FAIL.
- **If the Success conditions section is empty or incomplete, treat this as ambiguous. The model must stop and ask the user for clarification before generating the test.**
- **Spacing between numbers and units is optional; both `3.3V` and `3.3 V` are valid.**


---

## JSON output (single-object, structured steps with media references)

**Trigger:** When the user asks for “json” output of a test.

**Macro handling:**
- By default, JSON `steps`/`expected` preserve the authored lines verbatim, including any macro directives (`@...`) and any `{ID_EXPR}` expressions.
- If the user asks for **expanded JSON**, first expand macros to a linear list (no directives) and resolve all `{ID_EXPR}` to concrete integers, then emit JSON from the expanded form.

**Shape:**
```json
{
  "name": "<string>",
  "description": "<string>",
  "board": "<string>",
  "equipment": [
    {
      "id": "PSU1",
      "type": "psu",
      "channels": [
        { "channel": 1, "voltage_max": "<string | null>", "current_max": "<string | null>" }
      ]
    },
    {
      "id": "ELOAD",
      "type": "eload",
      "channels": [
        { "channel": 1, "voltage_max": "<string | null>", "current_max": "<string | null>" }
      ]
    },
    { "id": "SCOPE", "type": "scope", "channels": [1] },
    { "id": "DMM", "type": "dmm" },
    { "id": "<string>", "type": "controller", "subtype": "<string>" }
  ],
  "steps": [
    {
      "text": "<string>",
      "media": [
        {
          "type": "image",
          "ref": {
            "component": "<string>",
            "pin": "<number | null>"
          },
          "caption": "<string>"
        }
      ]
    }
  ],
  "expected": [
    {
      "text": "<string>",
      "media": [
        {
          "type": "image",
          "ref": {
            "component": "<string>",
            "pin": "<number | null>"
          },
          "caption": "<string>"
        }
      ]
    }
  ]
}
```

**Field rules:**
- `name`: use **Id** if present; else **Title**. If both exist, prefer **Id**.
- `description`: if a **Description** section exists, copy it verbatim (preserve newlines). Otherwise use an empty string `""`.
- `board`: if a **Board** section exists, copy it verbatim. Otherwise use an empty string `""`.
- `equipment`: **mandatory** array of equipment requirement objects (see “Equipment extraction rules” below).
- `steps`: array of step objects. Each object has:
  - `text`: copy the step line verbatim. Preserve punctuation, quotes, units, and glyphs.
  - `media`: array of media references (may be empty `[]`). Each media object has:
    - `type`: always `"image"`.
    - `ref`: object with `component` (string, e.g., `"P4"`, `"J1"`, `"TP_VOUT"`) and `pin` (number or `null` for entire component).
    - `caption`: brief description of what the image shows.
- `expected`: array of expected condition objects. Each object has:
  - `text`: copy the condition line verbatim.
  - `media`: array of media references (may be empty `[]`). Same structure as steps.
- Only allowed top-level keys: `name`, `description`, `board`, `equipment`, `steps`, `expected`. No other keys.
- Do not normalize spaces or units. Do not rewrite curly quotes.
- If **Success conditions** missing or incomplete, do not emit JSON; ask for clarification.
- If any step is ambiguous per rules, do not emit JSON; ask to revise.

**Equipment extraction rules (mandatory):**
- JSON `equipment` is derived from the authored procedure text (not from generated code).
- Emit equipment entries in a stable order: `PSU1`, `PSU2`, `ELOAD`, `SCOPE`, `DMM`, then any `controller` entries (sorted by controller `id`).
- Allowed `id` values:
  - For standard instruments, prefer: `PSU1`, `PSU2`, `ELOAD`, `SCOPE`, `DMM`.
  - For controllers, `id` is a free-form string derived from how the controller is referenced in the procedure.
- Allowed `type` values: `psu`, `eload`, `scope`, `dmm`, `controller`.
- Equipment object fields depend on `type`:
  - `psu` / `eload`: `channels` is required and is an array of channel objects: `{ "channel": <int>, "voltage_max": <string|null>, "current_max": <string|null> }`.
  - `scope`: `channels` is required and is an array of integers (e.g., `[1, 2]`).
  - `dmm`: omit `channels`.
  - `controller`: omit `channels` and include `subtype`.
- Controller subtype:
  - If `type` is `controller`, `subtype` is required.
  - `subtype` selects which controller driver pack to apply.
  - If the controller is referenced in the procedure but the driver/subtype is unclear, stop and ask the user to clarify.
- Limit formatting:
  - Procedure JSON must not contain non-measurement placeholders (e.g. `{ILIM1}`, `{VSET}`, `{CURRENT}`) in either `steps[].text` or `equipment`.
  - Fill limits whenever the procedure specifies them.
  - Values are strings including units (e.g., `"28 V"`, `"15 A"`).
  - If a required limit cannot be deduced as a concrete numeric value, set it to `null` and stop to ask the user for the missing numeric limit before emitting final JSON.
- Inclusion rules (scan all `steps[].text`):
  - **PSU**: include `PSU1`/`PSU2` if referenced by name in any step.
  - **ELOAD**: include `ELOAD` if any step mentions `electronic load`, `e-load`, or `ELOAD`.
  - **SCOPE**: include `SCOPE` if any step mentions `oscilloscope`, `scope`, a channel token like `CH1`, `CH2`, or scope-specific operations (trigger, probe, waveform, screenshots).
  - **Controller(s)**: controller inclusion is driven by the enabled controller driver pack(s). If the procedure contains controller-like tokens but no enabled driver pack matches, stop and ask which controller/driver applies.
  - **DMM**: include `DMM` if any step asks to measure a scalar value (e.g. voltage) without explicitly naming a scope/PSU/e-load as the measurement instrument.
- Channel + limit rules:
  - **PSU/ELOAD channels:** if channels are not explicitly given in the procedure, use `channel: 1`.
  - For each PSU id, set `voltage_max`/`current_max` to the maximum values requested anywhere for that PSU.
  - For `ELOAD`, set `current_max` to the maximum value requested anywhere.
- Scope channels:
  - `channels` is an array of integers. Include every distinct `CHn` referenced.
  - If a scope is required but no channels are explicitly referenced, use `channels: []`.

**Media extraction rules:**
- Parse each step for component references (P#, J#, TP#, U#, IC#, R#, C#, L#, etc.).
- **Reference boundary:** Do not include procedural binders like `as {ID_EXPR}` in any media reference. `as {…}` is never part of a physical name.
- For wiring/connection steps, extract all referenced connectors/TPs as separate media entries.
- If a specific pin is mentioned (e.g., "P6 pin 2", "P6#2"), set `pin` to that number; otherwise use `null`.
- For measurement steps on a node, include a media reference to help the operator locate it.
- **TP naming:** If the text contains `TP <NAME>`, treat the physical reference name as `<NAME>` (do **not** include the `TP ` prefix in `ref.component`). The TP name may include characters like `+`, `_`, digits, and `.`. Strip any trailing clause such as `as {…}`. Use a human-friendly caption like `"TP <NAME>"`.
- **Range expansion:** If the text matches `TP <PREFIX>.[<a>..<b>]`, expand to components `"<PREFIX>.<a>" ... "<PREFIX>.<b>"` and do not also add a `"TP <PREFIX>"` entry.
- For configuration-only steps (e.g., "Configure PSU to 28 V"), `media` may be empty.
- For expected conditions, include media only if a reference image is relevant (e.g., reference waveforms).

**Temporary backward-compatibility rule:**
- Code generation may ignore the `media` field until view generator integration is complete.

**Mapping logic:**
- Keep authored order. No invention or reordering.
- Measurement IDs `{ID_EXPR}` (including `{0}`) must appear in `steps` in authored order and only be referenced in `expected`.

**Example (source):**
```
name: CAP-CHARGE-HOLD-001
board: PPU-MAIN-REV2
steps:
  - Connect PSU1 + to P4 (+SR_28V) and – to P5 (GND), output OFF.
  - Configure PSU1 to 28 V / 20 A, output still OFF.
  - Tie P6 pin 2 (IF_SAFETY#PPU.EPO) to P4 (+SR_28V).
  - Connect electronic load between P21 (+CAP_30V) and P22 (GND), output OFF.
  - Configure the load to constant-current mode, 15 A, output still OFF.
  - Turn PSU1 output ON.
  - Set DSC IO#DSC18 (EPO_FNCORE) = ‘1’.
  - Set DSC IO#DSC41 (CHG_NCTRL) = ‘1’.
  - Set DSC DAC#DSC0 = 0.5 V.
  - Turn load ON.
  - Set DSC IO#DSC41 (CHG_NCTRL) = ‘0’.
  - Measure load current as {1}.
  - Wait 10 s.
  - Measure load current as {2}.
expected:
  - {1} = 10 A ± 5%
  - {2} = 10 A ± 5%
```

**Example (JSON output):**
```json
{
  "name": "CAP-CHARGE-HOLD-001",
  "description": "",
  "board": "PPU-MAIN-REV2",
  "equipment": [
    {
      "id": "PSU1",
      "type": "psu",
      "channels": [
        { "channel": 1, "voltage_max": "28 V", "current_max": "20 A" }
      ]
    },
    {
      "id": "ELOAD",
      "type": "eload",
      "channels": [
        { "channel": 1, "voltage_max": null, "current_max": "15 A" }
      ]
    },
    {
      "id": "fncore-mockup",
      "type": "controller",
      "subtype": "fncore-mockup"
    }
  ],
  "steps": [
    {
      "text": "Connect PSU1 + to P4 (+SR_28V) and – to P5 (GND), output OFF.",
      "media": [
        {
          "type": "image",
          "ref": { "component": "P4", "pin": null },
          "caption": "Connector P4 (+SR_28V)"
        },
        {
          "type": "image",
          "ref": { "component": "P5", "pin": null },
          "caption": "Connector P5 (GND)"
        }
      ]
    },
    {
      "text": "Configure PSU1 to 28 V / 20 A, output still OFF.",
      "media": []
    },
    {
      "text": "Tie P6 pin 2 (IF_SAFETY#PPU.EPO) to P4 (+SR_28V).",
      "media": [
        {
          "type": "image",
          "ref": { "component": "P6", "pin": 2 },
          "caption": "P6 pin 2 (IF_SAFETY#PPU.EPO)"
        },
        {
          "type": "image",
          "ref": { "component": "P4", "pin": null },
          "caption": "Connector P4 (+SR_28V)"
        }
      ]
    },
    {
      "text": "Connect electronic load between P21 (+CAP_30V) and P22 (GND), output OFF.",
      "media": [
        {
          "type": "image",
          "ref": { "component": "P21", "pin": null },
          "caption": "Connector P21 (+CAP_30V)"
        },
        {
          "type": "image",
          "ref": { "component": "P22", "pin": null },
          "caption": "Connector P22 (GND)"
        }
      ]
    },
    {
      "text": "Configure the load to constant-current mode, 15 A, output still OFF.",
      "media": []
    },
    {
      "text": "Turn PSU1 output ON.",
      "media": []
    },
    {
      "text": "Set DSC IO#DSC18 (EPO_FNCORE) = '1'.",
      "media": []
    },
    {
      "text": "Set DSC IO#DSC41 (CHG_NCTRL) = '1'.",
      "media": []
    },
    {
      "text": "Set DSC DAC#DSC0 = 0.5 V.",
      "media": []
    },
    {
      "text": "Turn load ON.",
      "media": []
    },
    {
      "text": "Set DSC IO#DSC41 (CHG_NCTRL) = '0'.",
      "media": []
    },
    {
      "text": "Measure load current as {1}.",
      "media": []
    },
    {
      "text": "Wait 10 s.",
      "media": []
    },
    {
      "text": "Measure load current as {2}.",
      "media": []
    }
  ],
  "expected": [
    {
      "text": "{1} = 10 A ± 5%",
      "media": []
    },
    {
      "text": "{2} = 10 A ± 5%",
      "media": []
    }
  ]
}
```


## Annex — Worked Example (placeholders only; Requirements/Post‑test omitted on purpose)

**Id**  
PRJ-POWER-TP-PS-001

**Title**  
Output rail bring‑up

**Description**  
Verify that the output rail reaches its nominal value and meets ripple and timing requirements.

**Test steps**  
- Configure the programmable PSU to `{VIN}` / `{ILIM}`, output OFF.  
- Probe setup: connect CH1 → `{TP_VOUT}`.  
- Scope setup for startup capture: 
  - CH1: V/div = {CH1_VDIV}, offset = {CH1_OFFS}
  - Trigger CH1 rising, Normal
  - Timebase per rise-time rule
- Turn PSU output ON; measure rise time on CH1 as `{1}`; save screenshot.
- Measure **mean voltage** on `{TP_VOUT}` on CH1 as `{2}`; save screenshot.
- Switch CH1 to **AC coupling**; set timebase so it fits around 10 periods of switching, set voltage scale for a good read (autoscale or manual).
- Measure ripple (pk‑pk) on CH1 as `{3}`; save screenshot.
- Measure switching frequency on CH1 as `{4}`; save screenshot.
- **Connect EPO and SR power.** ← *Ambiguous action step*  
  - At this point, the model must **not** rewrite further.  
  - The model must **ask the user** whether details (e.g., pins, connectors) are required or if the step can remain as written.  
  - Only after user confirmation can the test be finalized; if the user approves it as-is, it stays a plain action step with no ID and no success condition.

**Success conditions**  
- `{1} = {TRISE_TARGET} ± {TRISE_TOL}`  
- `{2} = {VOUT_NOM} ± {VOUT_TOL}`  
- `{3} < {RIPPLE_LIMIT}`  
- `{4} = {F_SW} ± {F_TOL}`

---

## Rules for common tests

- All oscilloscope measurements shall include a screencapture.

### Always ask the user for parameters first
- Generate the procedure only after parameters are provided.
- If parameters are missing, use placeholders {…}, but never invent values.
- Templates are available — use them and their syntax if deviation is needed.

---

### DCDC Power supply

**Placeholders to set:**  
{VIN}, {ILIM}, {TP_VOUT}, {TP_PGOOD} (optional), {ENABLE_PIN} (optional), {TRISE_TARGET}, {TRISE_TOL}, {RIPPLE_LIMIT} (pk-pk), {VOUT_NOM}, {VOUT_TOL}, {F_SW}, {F_TOL}, {PG_LEVEL}, {PG_TOL}, {PG_DELAY}, {PG_DELAY_TOL}

**Defaults (if unspecified):**
- {VOUT_TOL} = ±2% of {VOUT_NOM}
- {RIPPLE_LIMIT} = 5% of {VOUT_NOM} (pk-pk)
- Temperature limit = ΔT ≤ 30 °C (rise above ambient)
- If no rise time is provided: omit the rise-time step; use 5 ms/div timebase for other measurements
- Enable is asserted after PSU ON; if pin unknown, use {ENABLE_PIN} placeholder

**Test steps**
1. Configure the programmable PSU to {VIN} / {ILIM}, output OFF.
2. Probe setup: connect CH1 → {TP_VOUT}; if power-good is present, connect CH2 → {TP_PGOOD}.
3. Startup scope setup (DC):
  - CH1: V/div = {CH1_VDIV}, offset = {CH1_OFFS}
  - If CH2 present: V/div = {CH2_VDIV}, offset = {CH2_OFFS}
  - Trigger CH1 rising, Normal
  - If {TRISE_TARGET} provided: timebase = {TRISE_TARGET} / 2 per div; else 5 ms/div
4. Turn the PSU ON.
5. If an enable exists: Set {ENABLE_PIN} to ‘1’.
6. (Include only if rise time is specified) Measure rise time on CH1 as {1}; save screenshot.
7. (If PG present) Measure PG level on CH2 (DC coupling, mean) → {5}; save screenshot.
8. (If PG timing required) Measure delay between CH1 ({TP_VOUT}) crossing threshold and CH2 ({TP_PGOOD}) assertion → {6}; save screenshot.
9. Go into RUN mode to get the steady state signal
10. Measure DC voltage (mean) at steady state on CH1 → {4}: switch CH1 back to DC coupling; save screenshot (or DMM reading).
11. Measure ripple (pk-pk) at steady state on CH1 as {2}: switch CH1 to AC coupling, then perform vertical-only autoscaling (or manual if not available),  set timescale to around 1 period of estimated switching frequency; save screenshot.
12. Measure switching frequency on CH1 as {3}; save screenshot

13. Measure DUT temperature at steady state → {7} and ambient temperature → {8}.

**Success conditions**
- (Include only if {1} measured) {1} = {TRISE_TARGET} ± {TRISE_TOL}
- {2} < {RIPPLE_LIMIT} (pk-pk)
- {3} = {F_SW} ± {F_TOL}
- {4} = {VOUT_NOM} ± {VOUT_TOL}
- (If PG present) {5} = {PG_LEVEL} ± {PG_TOL}
- (If PG timing required) {6} = {PG_DELAY} ± {PG_DELAY_TOL}
- {7} - {8} ≤ 30°C

---

### RS422 test template (plain steps + success conditions)

**Placeholders to set:**  
{VIN}, {ILIM}, {UART_ID}, {BAUD}, {BAUD_TOL}, {ENABLE_PIN}, {CONN_LOOPBACK}, {RX_P}, {RX_N}, {V_DIFF}, {V_TOL}, {EYE_CRITERION}, {EN_LOOPBACK_POLARITY}

- {TP_RX_P}, {TP_RX_N} are the places where waveform measurements will be done
- {LOOPBACK_POLARITY} = positive or negative logic, enabled with '1' if positive logic, '0' if not

**Defaults (if unspecified):**
- {BAUD_TOL} = ±5% of {BAUD} (Expected Baud rate)
- {V_TOL} = ±5% of {V_DIFF}
- {EYE_CRITERION} = Ok with margin



**Test steps**
1. Configure the programmable PSU to {VIN} / {ILIM}, output OFF.
2. Probe setup (DC coupling): connect CH1 → {RX_P}, CH2 → {RX_N}; define and enable MATH = CH1 − CH2 (differential).
3. Set the oscilloscope timebase so one full frame of "test message" at {BAUD} fits on screen (~10 div).
4. Turn the PSU ON.
5. Configure UART {UART_ID} to {BAUD} 8N1, no flow control.
6. Set {ENABLE_PIN} per {EN_LOOPBACK_POLARITY} (assert internal loopback).
7. Send "test message" as {1} on {UART_ID}; record received data as {2}.
8. Acquire scope on MATH and measure: amplitude → {3}; bit frequency → {4}; perform visual SI check → {5}; save screenshot(s).
9. Set {ENABLE_PIN} per {EN_LOOPBACK_POLARITY} (disable internal loopback).
10. Send "test message" as {6} on {UART_ID} with no external loopback; record received data as {7}.
11. Install external loopback at {CONN_LOOPBACK}
12. Send "test message" as {8} on {UART_ID}; record received data as {9}.
13. Acquire scope on MATH and measure: amplitude → {10}; bit frequency → {11}; perform visual SI check → {12}; save screenshot(s).
14. Remove external jumpers and restore the DUT to nominal state.

**Success conditions**
- {1} = {2}
- {3} = {V_DIFF} ± {V_TOL} (default {V_TOL} = ±5% of {V_DIFF})
- {4} = {BAUD} ± {BAUD_TOL} (default {BAUD_TOL} = ±5% of {BAUD})
- {5} = {EYE_CRITERION} (default: Ok with margin)
- {7} = empty or timeout
- {8} = {9}
- {10} = {V_DIFF} ± {V_TOL} (default {V_TOL} = ±5% of {V_DIFF})
- {11} = {BAUD} ± {BAUD_TOL} (default {BAUD_TOL} = ±5% of {BAUD})
- {12} = {EYE_CRITERION} (default: Ok with margin)

String comparisons (machine-collected)
- ID-to-ID string equality is written without quotes, e.g. `{1} = {2}`. Evaluate as `lhs.strip() == rhs.strip()`.
- ID-to-literal string equality uses double quotes, e.g. `{1} = "ALO"`. Evaluate as `lhs.strip() == "ALO"`.
- Regex match is written as `/.../`, e.g. `{1} = /ALO\d+/`. Evaluate with `re.search(pattern, lhs.strip())`.
- `{n} = empty or timeout` passes if timeout OR `lhs.strip() == ""`; otherwise fails.


### Example — correcting unsafe wiring and actuator ambiguity

**Original (unsafe / ambiguous):**
- Apply 28 V between P5 (GND) and P4 (+SR_28V)   ← mixes wiring and ON
- Apply 28 V on TP EPO_SR (IF_SAFETY#PPU.EPO)  
- Apply 3V3 on TP EPO_FNCORE (IF_SAFETY.EPO_FNCORE) IO#DSC18  
- Apply 0 V on TP CHG_NCTRL (RBBA3000-50 nCTRL) IO#DSC41 VERIFY DISCHARGE!!!  
- Apply 2 V on TP CHG_ISET (RBBA3000-50 ISET)  
- Measure P21 {1}  
- Measure TP VMONI.1 {2}  
- Measure TP VMONI.5 {3}  

**Corrected (safe, LLM-ready with wiring vs. power-on separation):**
1. Connect PSU to P4 (+SR_28V) and P5 (GND), output OFF.  
2. Configure PSU to 28 V / 10 A, output still OFF.  
3. Tie TP EPO_SR to +SR_28V (same rail as Step 1).  
4. Turn PSU output ON.  
5. Set IO#DSC18 = ‘1’ (EPO_FNCORE asserted).  
6. “CHG_NCTRL” is referenced both as TP and IO#DSC41 → **ambiguous**. Ask which one is the control point before proceeding.  
7. VERIFY DISCHARGE!!! Ambiguous manual instruction → ask for clarification.  
8. “CHG_ISET 2 V” is referenced both as TP and possibly as a DAC output → **ambiguous**. Ask whether this should be driven by a DAC or an external source.  
9. Measure voltage at P21 {1}.  
10. Measure voltage at TP VMONI.1 {2}.  
11. Measure voltage at TP VMONI.5 {3}.  

**Key corrections:**  
- Explicit separation of *Connect*, *Configure*, and *Apply* for the PSU (Wiring vs. Power-On).  
- Ties declared explicitly instead of “Apply … on TP”.  
- Ambiguities flagged instead of silently fixed.  
- Measurement steps written as “Measure voltage …” with IDs only.


