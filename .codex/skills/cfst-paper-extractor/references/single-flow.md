# Single-Paper Worker Flow V2

Use this file as the worker execution contract for one paper.

Section map:

- `## 1-3`: enforce worker scope, required inputs, and execution order.
- `## 4-5`: apply validity and ordinary-CFST gates.
- `## 6-9`: resolve setup figures, recover corrupted tables, and preserve numeric and evidence traces.
- `## 10-11`: enforce validation expectations and final output goals.

## 1. Worker Contract

- process exactly one paper folder
- run only inside `worker_sandbox.py` runtime
- assert `CFST_SANDBOX=1`; if missing, fail fast with sandbox-required error
- read only the owned paper folder, the skill references, and the skill scripts
- write only to the worker-local temp directory
- never write directly to final published output
- treat repository as non-exclusive runtime; other workers may change unrelated files concurrently
- do not edit, revert, or publish outside declared worker ownership

## 2. Required Input Layout

The worker input folder must contain:

- `<paper_token>.md`
- `<paper_token>_content_list_v2.json`
- `images/`
- `table/`

If any required path is missing, fail fast and report the missing path.

## 3. Mandatory Execution Order

1. Read `references/extraction-rules.md`.
2. Verify required input files exist.
3. Read markdown first for global context.
4. Run the validity gate.
5. Run the ordinary-CFST gate.
6. Resolve the setup figure from markdown-linked image evidence.
7. Detect table corruption and switch to `table/` images when needed.
8. Extract specimen rows.
9. Normalize units and derived values with `scripts/safe_calc.py`.
10. Build schema v2 JSON.
11. Validate with `scripts/validate_single_output.py`.
12. Write only to worker-local JSON path.

## 4. Validity Gate

Stop as invalid when the paper is:

- FE-only
- theory-only or review-only
- non-column CFST study without recoverable specimen data
- no usable ultimate experimental load data

For invalid papers:

- `is_valid=false`
- `is_ordinary_cfst=false`
- empty specimen groups
- non-empty single-line `reason`

## 5. Ordinary-CFST Gate

Even when `is_valid=true`, decide whether the paper belongs in the ordinary-CFST dataset.

This gate is intentionally paper-level. If a valid paper mixes ordinary and special specimens, keep the whole paper non-ordinary instead of selecting a specimen subset.

Allow ordinary inclusion only when all hold:

- shape is circular, square, rectangular, or round-ended
- steel is carbon steel
- test is ambient-temperature, static, monotonic compression
- eccentric compression is single-direction when present
- concrete is normal, high-strength, or recycled aggregate concrete
- recycled aggregate replacement ratio `R%` is explicitly extractable when recycled concrete is used

Typical exclusion or special-tag cases:

- stainless steel
- lightweight concrete
- SCC
- UHPC / RPC
- strengthened or specially confined sections
- fire, corrosion, or durability-conditioned specimens
- nonstandard shapes such as elliptical or obround

Record these findings in:

- `is_ordinary_cfst`
- `ordinary_filter.include_in_dataset`
- `ordinary_filter.special_factors`
- `ordinary_filter.exclusion_reasons`

## 6. Setup Figure Resolution

- prefer markdown mentions like `Fig.`, `Figure`, `加载装置`, `试验装置`
- locate the exact markdown image reference
- open that referenced image under `images/`
- determine loading mode from visual evidence when possible
- do not decide loading mode from text alone when setup image evidence exists

Store the resolved setup trace in:

- `paper_level.loading_mode`
- `paper_level.setup_figure`
- specimen `loading_mode`
- specimen `evidence.setup_image`

## 7. Table Recovery Rules

Treat markdown table text as untrusted when it shows:

- merged labels
- one cell with multiple scalar values
- shifted columns
- broken load columns
- broken source/reference columns
- decimal fragments or merged tokens that make scalar assignment ambiguous

Then:

- use `table/` image as primary evidence
- rebuild row alignment from visual evidence
- keep eccentricity signs exactly as source evidence shows them
- mark `quality_flags` such as `ocr_recovered`

## 8. Numeric Rules

- every conversion or derivation must use `scripts/safe_calc.py`
- store published JSON numbers in canonical `MPa / mm / kN / %` units
- round to `0.001`
- keep the `fcy150` key present; it may stay `null` when project-level strength normalization is deferred
- `boundary_condition` may be `unknown` or `null` when the paper does not define it defensibly
- `L` means project geometric specimen length, not effective length
- keep eccentricity signs as source evidence shows them
- do not use the sign pattern of `e1` and `e2` alone to exclude a specimen from the ordinary dataset
- recycled concrete rows must preserve `R%` in `r_ratio`
- when the paper does not define `L`, use steel-tube net height only when the figure evidence makes that geometry explicit, and record the derivation
- never infer `L` from boundary-condition assumptions or effective-length formulas

## 9. Evidence Rules

Every specimen row must preserve:

- concise `source_evidence`
- structured `evidence.page`
- `evidence.table_id`
- `evidence.figure_id`
- `evidence.table_image`
- `evidence.setup_image`
- `evidence.value_origin`

When a stored value is converted to canonical units, keep the original raw unit/value trace in `evidence.value_origin` and preserve `quality_flags` such as `unit_converted`.

When a value is derived, the field-level evidence must record:

- formula
- raw text
- raw unit if any
- source location

## 10. Validation Expectations

Validation must reject:

- missing or blank `specimen_label`
- invalid `fc_basis`
- impossible dimensions or strengths
- `is_valid=false` with non-empty specimen groups
- axial rows with nonzero eccentricity
- eccentric rows with both eccentricities zero
- non-null `fcy150` values that are non-numeric or non-positive
- ordinary rows with shapes outside circular / square / rectangular / round-ended
- ordinary rows with non-carbon steel
- ordinary rows with concrete types outside normal / high-strength / recycled
- duplicate specimen labels

## 11. Final Output Goal

The single-paper JSON should be:

- traceable
- physically plausible
- ordinary-filter aware
- canonical for downstream project-specific processing
