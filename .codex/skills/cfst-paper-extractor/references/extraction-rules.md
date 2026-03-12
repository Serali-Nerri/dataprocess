# CFST Extraction Rules V2

Use this file as the extraction source of truth for one paper.

Section map:

- `## 1. Target Scope`: decide whether the paper is usable at all.
- `## 2. Ordinary-CFST Gate`: decide whether a valid paper belongs in the ordinary dataset.
- `## 3-6`: apply schema shape, group mapping, paper-level fields, and specimen fields.
- `## 7-12`: apply evidence, loading, numeric, length, table-corruption, and invalid-output rules.

## 1. Target Scope

This workflow is for experimental CFST column papers that can support a unified ML/DL dataset for ultimate axial or eccentric compression resistance.

A paper is `is_valid=true` only when all are true:

- research object includes CFST columns or stub columns
- paper contains physical specimen test evidence
- paper includes usable specimen-level experimental capacity data
- loading mode is axial compression, single-direction eccentric compression, or a clearly separable mixture of those two modes

## 2. Ordinary-CFST Gate

The v2 schema separates:

- `is_valid`
- `is_ordinary_cfst`
- `ordinary_filter.include_in_dataset`

The ordinary decision is intentionally paper-level in v2. Use it as a clean-paper gate: if any specimen set in a valid paper falls outside the ordinary scope, keep the whole paper `is_ordinary_cfst=false` and `ordinary_filter.include_in_dataset=false`.

### 2.1 Include As Ordinary CFST

Set `is_ordinary_cfst=true` only when the specimen set stays within the following scope:

- section shape is one of: circular, square, rectangular, round-ended
- steel tube is conventional carbon steel
- test is at ambient temperature
- loading is static and monotonic
- compression mode is axial or single-direction eccentric compression
- no strengthening, no added confinement device, no stiffener that changes the basic member system
- no durability-conditioned or special-environment test history
- concrete may be:
  - normal concrete
  - high-strength concrete
  - recycled aggregate concrete, with explicit recycled aggregate replacement ratio `R%`

Typical ordinary cases:

- normal concrete
- high-strength concrete
- recycled aggregate concrete with explicit `R%`
- carbon-steel tube
- ambient-temperature static monotonic compression tests
- axial compression
- single-direction eccentric compression

### 2.2 Exclude Or Tag As Special

Set `is_ordinary_cfst=false` and record `ordinary_filter.special_factors` / `ordinary_filter.exclusion_reasons` when any of these dominates the specimen design:

- stainless steel tube
- lightweight aggregate concrete
- self-consolidating concrete
- UHPC / RPC / ultra-high-strength concrete
- fire exposure / corrosion / freeze-thaw / durability-conditioned specimens
- external or internal stiffeners, spirals, CFRP, additional confinement devices
- preload, prestress, impact, cyclic loading, or other nonstandard loading history
- nonstandard section families outside circular / square / rectangular / round-ended
- beam-column, joint, or frame tests without recoverable column-level specimen data

If the paper is valid but non-ordinary, keep `is_valid=true`, `is_ordinary_cfst=false`, and `ordinary_filter.include_in_dataset=false`.

## 3. Top-Level JSON Shape

Required top-level keys:

- `schema_version`
- `paper_id`
- `is_valid`
- `is_ordinary_cfst`
- `reason`
- `ordinary_filter`
- `ref_info`
- `paper_level`
- `Group_A`
- `Group_B`
- `Group_C`

Recommended `schema_version` value:

- `cfst-paper-extractor-v2`

Published `output/<paper_id>.json` files are the canonical dataset artifact. Any downstream tabular conversion is project-specific and outside this skill's canonical schema.

## 4. Group Mapping

- `Group_A`: square / rectangular
  - `b`: outer width
  - `h`: outer depth
- `Group_B`: circular
  - `b = h = D`
  - `r0 = h / 2`
- `Group_C`: elliptical / round-ended / obround
  - `b`: major axis
  - `h`: minor axis
  - `b >= h`
  - `r0 = h / 2`

Unlike v1, `Group_A.r0` is not forced to zero. Keep a nonzero corner radius when the paper provides it or when the section is clearly rounded-corner rectangular.

## 5. Required Paper-Level Fields

### 5.1 `ordinary_filter`

Required keys:

- `include_in_dataset`: boolean
- `special_factors`: list of strings
- `exclusion_reasons`: list of strings

### 5.2 `ref_info`

Required keys:

- `title`
- `authors`
- `journal`
- `year`
- `citation_tag`

Optional:

- `doi`
- `language`

### 5.3 `paper_level`

Required keys:

- `loading_mode`
- `boundary_condition`
- `test_temperature`
- `loading_regime`
- `loading_pattern`
- `setup_figure`
- `expected_specimen_count`
- `notes`

`loading_mode` allowed values:

- `axial`
- `eccentric`
- `mixed`
- `unknown`

`test_temperature` allowed values:

- `ambient`
- `elevated`
- `post_fire`
- `unknown`

`loading_regime` allowed values:

- `static`
- `dynamic`
- `impact`
- `unknown`

`loading_pattern` allowed values:

- `monotonic`
- `cyclic`
- `repeated`
- `unknown`

`setup_figure` keys:

- `figure_id`
- `image_path`
- `page`

`boundary_condition` is trace metadata. Keep any defensible text the paper provides, but `null` or `unknown` is acceptable when the support condition cannot be recovered confidently. Do not derive `L` from boundary condition alone.

## 6. Required Specimen Fields

Every specimen row in `Group_A`, `Group_B`, or `Group_C` must contain:

- `ref_no`
- `specimen_label`
- `section_shape`
- `loading_mode`
- `boundary_condition`
- `fc_value`
- `fc_type`
- `fc_basis`
- `fy`
- `fcy150`
- `r_ratio`
- `steel_type`
- `concrete_type`
- `b`
- `h`
- `t`
- `r0`
- `L`
- `e1`
- `e2`
- `n_exp`
- `source_evidence`
- `evidence`
- `quality_flags`

### 6.1 Enumerations

`section_shape`:

- `square`
- `rectangular`
- `circular`
- `elliptical`
- `round-ended`
- `obround`

`loading_mode`:

- `axial`
- `eccentric`

`fc_basis`:

- `cube`
- `cylinder`
- `prism`
- `unknown`

`steel_type`:

- `carbon_steel`
- `stainless_steel`
- `other`
- `unknown`

`concrete_type`:

- `normal`
- `high_strength`
- `lightweight`
- `recycled`
- `self_consolidating`
- `uhpc`
- `other`
- `unknown`

### 6.2 Field Semantics

- `ref_no`: fixed empty string `""`
- `specimen_label`: unique, non-empty specimen ID
- `boundary_condition`: trace metadata for the specimen support/end condition; may be `null` or `unknown`
- `fc_value`: source concrete strength value in MPa
- `fc_type`: source concrete specimen description, for example `Cube 150` or `Cylinder 100x200`
- `fc_basis`: basis category of `fc_value`
- `fy`: steel yield strength in MPa
- `fcy150`: normalized 150 mm cylinder compressive strength in MPa; keep the key present, but `null` is allowed during extraction when project-level conversion is deferred
- `r_ratio`: recycled aggregate ratio in percent, use `0` for normal concrete
- `b`, `h`, `t`, `r0`, `L`, `e1`, `e2`: numbers stored in mm
- `L`: project geometric specimen length in mm; do not reinterpret it as effective length
- `n_exp`: experimental ultimate load in kN
- `source_evidence`: concise human-readable trace string
- `quality_flags`: list of extraction-risk flags such as `ocr_recovered`, `derived_L`, `unit_converted`

For recycled aggregate concrete, `r_ratio` must record the recycled aggregate replacement ratio `R%`.

### 6.3 Canonical Units

Store numeric values in the published JSON using these canonical units:

- `fc_value`, `fy`, `fcy150`: `MPa`
- `r_ratio`: `%`
- `b`, `h`, `t`, `r0`, `L`, `e1`, `e2`: `mm`
- `n_exp`: `kN`

## 7. Evidence Contract

Each specimen `evidence` object must contain:

- `page`
- `table_id`
- `figure_id`
- `table_image`
- `setup_image`
- `value_origin`

`value_origin` is a dictionary keyed by field name. Each populated field entry should contain:

- `kind`: `direct`, `derived`, `normalized`, or `recovered_from_image`
- `raw_text`
- `raw_unit`
- `formula`
- `source`

When a stored value is converted to canonical units or normalized from another basis, preserve the original text/unit in `value_origin` and mark the step with `kind = normalized` or `quality_flags += ["unit_converted"]` as appropriate.

Example:

```json
{
  "value_origin": {
    "L": {
      "kind": "derived",
      "raw_text": "L = 3D",
      "raw_unit": "mm",
      "formula": "3 * 141.4",
      "source": "Page 4, Fig. 1"
    }
  }
}
```

## 8. Loading-Mode Rules

- determine paper-level loading mode from setup-figure evidence when available
- preserve specimen-level loading mode in every row
- if specimen `loading_mode = axial`, enforce `e1 = 0` and `e2 = 0`
- if specimen `loading_mode = eccentric`, at least one of `e1`, `e2` must be nonzero
- preserve the original signs of `e1` and `e2`
- `e1` and `e2` may have the same sign or opposite signs; sign alone must not be used to exclude an otherwise ordinary specimen
- mixed papers must still store each specimen row with its own loading mode

## 9. Numerical Rules

- use `scripts/safe_calc.py` for every conversion and derived value
- convert stored values to the canonical units defined above before writing JSON
- round numeric outputs to `0.001`
- enforce:
  - `fc_value > 0`
  - `fy > 0`
  - `fcy150 > 0` when `fcy150` is populated
  - `b > 0`
  - `h > 0`
  - `t > 0`
  - `L > 0`
  - `n_exp > 0`
  - `0 <= r_ratio <= 100`
- `t` must be strictly smaller than `min(b, h) / 2`
- keep `fcy150 = null` when the project defers strength-basis conversion; do not fabricate it during extraction

Ordinary-CFST inclusion requires all specimen rows to stay within:

- `section_shape in {square, rectangular, circular, round-ended}`
- `steel_type = carbon_steel`
- `concrete_type in {normal, high_strength, recycled}`
- `test_temperature = ambient`
- `loading_regime = static`
- `loading_pattern = monotonic`

## 10. Length Rule

Determine `L` as the project geometric specimen length with this priority:

1. explicit specimen length in paper text/table/note
2. explicit formula or ratio with clear variable meaning
3. figure-based derivation with explicit geometry evidence, including steel-tube net height when the figure makes that geometry unambiguous

If the paper does not name `L` directly but the specimen/setup figure makes the steel-tube net height derivable, use that geometric length and record the basis in `source_evidence` and `evidence.value_origin.L`.

Do not populate `L` when the geometry basis is ambiguous. Do not infer `L` from boundary-condition assumptions or effective-length formulas.

## 11. Markdown Table Corruption Gate

Treat markdown table text as invalid and switch to image-first recovery when any holds:

- merged specimen labels
- one cell contains multiple candidate scalar values
- row/column alignment is unstable
- unit header and data column semantics drift
- a source/reference column contains load-like numbers
- OCR split fragments make scalar assignment ambiguous

When recovery is needed:

- use `table/` image as primary evidence
- use markdown/context only as locator support
- preserve a `quality_flags` marker

## 12. Invalid And Failed Outputs

### 12.1 Invalid Paper

If paper is outside the experimental CFST-column scope:

- `is_valid=false`
- `is_ordinary_cfst=false`
- `ordinary_filter.include_in_dataset=false`
- `ref_info` may still contain bibliographic metadata when available
- `Group_A=[]`, `Group_B=[]`, `Group_C=[]`

### 12.2 Processing Failure

When evidence is insufficient for a defensible extraction:

- stop with a clear failure reason
- do not fabricate row values
- keep intermediate output outside final published output
