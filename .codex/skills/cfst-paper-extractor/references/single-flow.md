# Single-Paper Worker Flow V2.1

Use this file as the worker execution contract for one paper.

Section map:

- `## 1-3`: enforce worker scope, required inputs, and execution order.
- `## 4-5`: apply validity and ordinary-CFST gates.
- `## 6-10`: resolve setup figures, recover corrupted tables, resolve concrete-strength basis, and preserve numeric and evidence traces.
- `## 11-12`: enforce validation expectations and final output goals.

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
4. Resolve concrete-strength basis evidence from `Materials`, `Specimens`, `Concrete properties`, notation sections, and table footnotes before assigning `fc_basis`.
5. Run the validity gate.
6. Run the ordinary-CFST Tier 1 paper-level preconditions.
7. Resolve the setup figure from markdown-linked image evidence.
8. Detect table corruption and switch to `table/` images when needed.
9. Extract specimen rows.
10. Normalize units and derived values with `scripts/safe_calc.py`.
11. Run the ordinary-CFST Tier 2 per-specimen evaluation and tag each specimen with `is_ordinary` and `ordinary_exclusion_reasons`.
12. Derive paper-level `is_ordinary_cfst` and `ordinary_filter` summary from specimen flags.
13. Build schema v2.1 JSON.
14. Validate with `scripts/validate_single_output.py`.
15. Write only to worker-local JSON path.

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

## 5. Ordinary-CFST Gate (Two-Tier, Specimen-Level)

Even when `is_valid=true`, evaluate each specimen individually for ordinary-CFST inclusion using the two-tier model defined in `references/extraction-rules.md` §2.

### Tier 1 — Paper-Level Preconditions

Check once for the whole paper. If any fails, set all specimens to `is_ordinary=false` with the paper-level reason in each specimen's `ordinary_exclusion_reasons`.

- `test_temperature = ambient`
- `loading_regime = static`
- no paper-wide durability conditioning (fire, corrosion, freeze-thaw)

### Tier 2 — Per-Specimen Evaluation

When Tier 1 passes, check each specimen individually:

- `section_shape in {circular, square, rectangular, round-ended}`
- `steel_type = carbon_steel`
- `concrete_type in {normal, high_strength, recycled}`
- `loading_pattern = monotonic`
- eccentric compression is single-direction when present
- no strengthening or special confinement
- recycled aggregate `R%` is explicitly extractable when `concrete_type = recycled`

Tag each specimen:

- `is_ordinary = true` with `ordinary_exclusion_reasons = []` when all conditions pass
- `is_ordinary = false` with non-empty `ordinary_exclusion_reasons` listing each failing condition

### Paper-Level Derivation

After all specimens are tagged, derive paper-level fields:

- `is_ordinary_cfst` = true when at least one specimen has `is_ordinary=true`
- `ordinary_filter.include_in_dataset` = `is_ordinary_cfst`
- `ordinary_filter.ordinary_count` = count of ordinary specimens
- `ordinary_filter.total_count` = total specimen count
- `ordinary_filter.special_factors`: paper-level special tags
- `ordinary_filter.exclusion_reasons`: paper-level exclusion summaries

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

## 8. Concrete-Strength Basis Rules

- treat explicit material/property evidence as first priority: `Materials`, `Specimens`, `Concrete properties`, notation sections, table headers, and table footnotes outrank shorthand labels such as `C60`
- resolve `fc_basis` before doing any normalization or downstream interpretation of `fc_value`
- map explicit `150 mm cube` or equivalent standard-cube wording to `fc_basis = cube`
- map explicit cylinder wording, cylinder dimensions, `ASTM C39`, `JIS A 1108`, `JIS A 1132`, or equivalent cylinder-test descriptions to `fc_basis = cylinder`
- map explicit prism-strength / axial-compressive-strength wording to `fc_basis = prism`
- in Chinese GB/T 50010-type context, treat bare `C60`, `C70`, and similar `C` grades as cube-strength grades unless the paper itself contradicts that reading
- in the same Chinese GB/T 50010-type context, treat `fck` and `fc` as prism/axial-system values, not cylinder strengths
- in Eurocode / EN 206 context, read `Cx/y` as `x = cylinder`, `y = cube`; do not collapse it to a single-basis guess
- in Eurocode / EN 206 context, treat `fck` as the characteristic cylinder compressive strength; when a European paper writes `fck` without a `Cx/y` grade, use `fc_basis = cylinder`
- in United States ACI / ASTM C39 context, treat `f'c` as cylinder-based specified compressive strength
- in Japanese `Fc` / JIS A 1108 / JIS A 1132 context, treat `Fc` as cylinder-based unless the paper explicitly defines another basis
- treat a bare single-value `C60` outside explicit Chinese cube context as ambiguous; inspect the cited code and the material/property section before choosing `cube` or `cylinder`
- the same symbol means different things across codes: China `fck` (axial/prism, e.g., C60 → 38.5 MPa) is NOT Eurocode `fck` (cylinder, e.g., C60/75 → 60 MPa); China `fc` (axial design value) is NOT US `f'c` (specified cylinder strength); Japan `Fc` (JIS cylinder-based design standard strength) is NOT interchangeable with Chinese `fc` or US `f'c`; always check which code governs the specimen before interpreting these symbols
- when both cube and cylinder values are reported, prefer the value the authors explicitly use in the specimen-property table, material parameters, constitutive model, or design/check calculations
- if the paper still does not identify the basis defensibly, set `fc_basis = unknown` and keep `fcy150 = null`
- when the basis is inferred from code/notation context rather than an explicit specimen description, mark `quality_flags` with `context_inferred_fc_basis`

## 9. Numeric Rules

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

## 10. Evidence Rules

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

For `fc_basis` decisions:

- cite the exact `Materials` / `Specimens` / `Concrete properties` paragraph, table header, or table footnote when available
- if you rely on code/notation context such as GB/T 50010 `C60`, Eurocode `C60/75`, ACI `f'c`, or Japanese `Fc`, name that context explicitly in `source_evidence`
- do not leave a context-inferred `fc_basis` unexplained in `source_evidence`

## 11. Validation Expectations

Validation must reject:

- missing or blank `specimen_label`
- invalid `fc_basis`
- impossible dimensions or strengths
- `is_valid=false` with non-empty specimen groups
- axial rows with nonzero eccentricity
- eccentric rows with both eccentricities zero
- non-null `fcy150` values that are non-numeric or non-positive
- `is_ordinary=true` with shapes outside circular / square / rectangular / round-ended
- `is_ordinary=true` with non-carbon steel
- `is_ordinary=true` with concrete types outside normal / high-strength / recycled
- `is_ordinary=true` with `loading_pattern != monotonic`
- `is_ordinary=false` with empty `ordinary_exclusion_reasons`
- `is_ordinary_cfst=true` but no specimen has `is_ordinary=true`
- `is_ordinary_cfst=false` but some specimen has `is_ordinary=true`
- `ordinary_filter.ordinary_count` mismatch with actual count of `is_ordinary=true` specimens
- per-specimen `loading_pattern` not in allowed specimen-level values
- duplicate specimen labels

## 12. Final Output Goal

The single-paper JSON should be:

- traceable
- physically plausible
- ordinary-filter aware
- canonical for downstream project-specific processing
