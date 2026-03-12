---
name: cfst-paper-extractor
description: Enhanced CFST paper extractor with ordinary-CFST filtering, schema v2 validation, strict worker sandbox isolation, and parallel worker orchestration.
---

# CFST Paper Extractor

## Overview

This skill builds an ML/DL-ready ordinary CFST column dataset from MinerU-parsed papers.

Core upgrades over v1:

- ordinary-CFST inclusion gate
- schema v2 with paper-level and field-level provenance
- stricter physical validation
- preprocess manifests for `table/` evidence
- batch manifests and worker-job planning
- unified flat CSV export
- explicit publish logs
- mandatory worker sandbox isolation
- mandatory parallel worker orchestration

Keep this skill self-contained:

- use only scripts and references inside this skill directory
- do not depend on `Reffernce.md` or any external metadata manifest

## Runtime Variables

- `<raw_root>`: root containing raw MinerU paper folders
- `<batch_root>`: one batch run root under the current workspace
- `<paper_id>`: citation-style paper id such as `A1-1`
- `<paper_dir_relpath>`: one normalized paper folder path relative to repo root
- `<worker_output_json_path>`: worker-local JSON path under `<batch_root>/tmp/<paper_id>/<paper_id>.json`
- `<final_output_json_path>`: final published JSON path under `<batch_root>/output/<paper_id>.json`
- `<expected_specimen_count>`: expected specimen count when known

## Recommended Workflow

### 1. Prepare batch assets

```bash
python .codex/skills/cfst-paper-extractor/scripts/prepare_batch.py \
  --raw-root . \
  --output-root runs/a1_demo
```

Outputs:

- `manifests/batch_manifest.json`
- `manifests/worker_jobs.json`
- `manifests/batch_state.json`
- `parsed_with_tables/<paper_id>/`

### 2. Extract one paper

Read:

- `references/extraction-rules.md`
- `references/single-flow.md`

Target schema:

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

### 3. Validate one paper

```bash
python .codex/skills/cfst-paper-extractor/scripts/validate_single_output.py \
  --json-path <worker_output_json_path> \
  --expect-valid true \
  --strict-rounding
```

### 4. Publish validated outputs

```bash
python .codex/skills/cfst-paper-extractor/scripts/publish_validated_output.py \
  --batch-manifest runs/a1_demo/manifests/batch_manifest.json \
  --tmp-root runs/a1_demo/tmp \
  --output-dir runs/a1_demo/output \
  --publish-log runs/a1_demo/logs/publish_log.jsonl
```

### 5. Export unified CSV

```bash
python .codex/skills/cfst-paper-extractor/scripts/export_unified_dataset.py \
  --input-dir runs/a1_demo/output \
  --output-csv runs/a1_demo/exports/unified_dataset.csv
```

## Mandatory Agent Model

Use a parent-child model for every extraction task:

1. Parent agent is orchestrator and reviewer only.
2. Parent MUST spawn one worker sub-agent per paper folder.
3. Parent MUST enforce a hard concurrency cap of 5 active worker sub-agents.
4. Each worker MUST process exactly one paper folder.
5. Each worker MUST complete extraction, calculation, validation, and JSON write for its own folder.
6. Parent preflight is limited to git/path checks and script-based preprocess.
7. Parent MUST NOT manually read raw paper markdown/json/images once workers are launched.
8. Parent MUST tell each worker the repository may be concurrently modified by other workers.
9. Parent MUST declare worker ownership paths at launch:
- one paper folder path
- one worker-local temp JSON path under `tmp/<paper_id>/`
- one worker worktree path
10. Worker MUST ignore unrelated repository changes and MUST NOT edit or revert files outside declared ownership.
11. Parent waits for worker results, records pass/fail, retries only failed workers, then publishes final outputs.

## Git Repository Gate

Run before any worker launch:

```bash
git rev-parse --is-inside-work-tree
```

If current directory is not a git repository, stop. Worktree-based isolated execution requires a valid git repo with `HEAD`.

Bootstrap helper:

```bash
python .codex/skills/cfst-paper-extractor/scripts/bootstrap_git_repo.py \
  --repo-root . \
  --initial-empty-commit
```

## Worker Runtime Isolation

Each paper worker MUST run in its own git worktree and MUST be launched through `scripts/worker_sandbox.py`.

Direct worker execution without the sandbox launcher is forbidden.

Create one worker worktree:

```bash
python .codex/skills/cfst-paper-extractor/scripts/git_worktree_isolation.py create \
  --paper-dir <paper_dir_relpath> \
  --output-dir tmp/<paper_id>
```

Returned JSON includes:

- `worktree_path`
- `branch`
- `paper_rel`
- `skill_rel`
- `output_dir`
- `sandbox_allowed_rw`
- `sandbox_allowed_ro`
- `sandbox_entry_cwd`

Launch worker command in sandbox:

```bash
python .codex/skills/cfst-paper-extractor/scripts/worker_sandbox.py \
  --worktree-path <worker_worktree_path> \
  --paper-dir-relpath <paper_rel> \
  --skill-dir-relpath <skill_rel> \
  --output-dir <output_dir> \
  --cwd-mode paper \
  -- <worker_command>
```

Sandbox contract:

- `bubblewrap` / `bwrap` is required
- worker process gets `CFST_SANDBOX=1`
- sandbox startup failure is fatal; no soft-isolation fallback
- worker write scope is limited to the owned paper folder and worker temp output dir
- worker read scope is limited to owned paper folder, this skill, and declared metadata paths

## Final Output Publish Contract

- worker MUST write only to `<worker_output_json_path>`
- worker MUST NOT read or write final published output folders directly
- parent MUST publish final JSON only to `<final_output_json_path>`
- parent publish is the only allowed transition from temp output to final output
- parent records publish log and then removes finished worker worktrees

Cleanup helper:

```bash
python .codex/skills/cfst-paper-extractor/scripts/git_worktree_isolation.py remove \
  --worktree-path <worker_worktree_path> \
  --branch <worker_branch> \
  --delete-branch
```

## Retry Strategy

Use deterministic retry at worker level:

1. First run: worker performs full extraction and validation.
2. If validation fails: worker fixes issues and reruns validation once.
3. If still failing: worker returns failure reason and intermediate JSON path.
4. Parent may respawn a failed paper worker at most one additional time with a focused correction prompt.

## Ordinary-CFST Policy

Use three states instead of a single valid/invalid split:

- `is_valid=false`: not a usable CFST experimental paper
- `is_valid=true`, `is_ordinary_cfst=false`: usable but not part of the ordinary-CFST training set
- `is_valid=true`, `is_ordinary_cfst=true`: include in dataset

Ordinary-CFST inclusion in this workspace means:

- shape is circular, square, rectangular, or round-ended
- steel is carbon steel
- test is ambient-temperature, static, monotonic compression
- loading is axial or single-direction eccentric compression
- concrete may be normal, high-strength, or recycled aggregate concrete
- recycled aggregate replacement ratio `R%` must be preserved in `r_ratio`
- `e1` and `e2` may have the same sign or opposite signs; sign alone is not an exclusion rule

Typical exclusion tags:

- `stainless_steel`
- `lightweight_concrete`
- `self_consolidating_concrete`
- `uhpc`
- `stiffened_section`
- `fire_exposed`
- `durability_conditioned`
- `nonstandard_section_family`
