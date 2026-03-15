---
name: cfst-paper-extractor
description: Extract specimen-level data from MinerU-parsed CFST paper folders into schema-v2 JSON, validate ordinary-CFST inclusion, provenance, and physical plausibility, orchestrate isolated one-paper workers, and publish canonical JSON outputs. Use when Codex needs to prepare raw MinerU parses, extract one or many CFST experimental papers, repair or review CFST JSON outputs, or build unified ML/DL-ready datasets from ordinary and special-case CFST studies.
---

# CFST Paper Extractor

Use only bundled files in this skill. Do not depend on external metadata manifests.

## Use This Workflow

1. Prepare a batch workspace from raw MinerU paper folders.

```bash
python .codex/skills/cfst-paper-extractor/scripts/prepare_batch.py \
  --raw-root . \
  --output-root runs/a1_demo
```

This creates `parsed_with_tables/`, `manifests/`, `tmp/`, `output/`, and `logs/`.

2. Before extracting or repairing a paper, read:

- `references/extraction-rules.md` for schema, ordinary-CFST rules, evidence requirements, and numeric constraints.
- `references/single-flow.md` for the worker contract, execution order, setup-image rules, mandatory table-image reconciliation, and retry behavior.

To jump within those files, run:

```bash
rg -n "^## " .codex/skills/cfst-paper-extractor/references/extraction-rules.md \
  .codex/skills/cfst-paper-extractor/references/single-flow.md
```

3. Write one paper only to its worker-local temp JSON inside the worker sandbox, then validate that same temp JSON before the worker exits.

```bash
python .codex/skills/cfst-paper-extractor/scripts/worker_sandbox.py \
  --worktree-path <worker_worktree> \
  --paper-dir-relpath runs/a1_demo/parsed_with_tables/A1-1 \
  --output-dir runs/a1_demo/tmp/A1-1 \
  --cwd-mode workspace \
  -- \
  python .codex/skills/cfst-paper-extractor/scripts/validate_single_output.py \
    --json-path runs/a1_demo/tmp/A1-1/A1-1.json \
    --expect-valid true \
    --strict-rounding
```

Direct parent-shell calls to `scripts/validate_single_output.py` and `scripts/safe_calc.py` are intentionally rejected in this strict variant; both helpers require `CFST_SANDBOX=1` and must run under `scripts/worker_sandbox.py`.

Add `--expect-count N` when the paper has a known specimen count.

4. After workers finish, publish validated JSON outputs. Treat `output/<paper_id>.json` as the canonical downstream artifact.

```bash
python .codex/skills/cfst-paper-extractor/scripts/publish_validated_output.py \
  --batch-manifest runs/a1_demo/manifests/batch_manifest.json \
  --tmp-root runs/a1_demo/tmp \
  --output-dir runs/a1_demo/output \
  --publish-log runs/a1_demo/logs/publish_log.jsonl
```

5. When running a long batch inside a git repo, checkpoint published outputs only when needed.

```bash
python .codex/skills/cfst-paper-extractor/scripts/checkpoint_output_commits.py \
  --processed-count 10 \
  --output-dir runs/a1_demo/output
```

## Respect These Contracts

### Batch orchestration

- Use a parent-child model for every multi-paper extraction.
- Regardless of paper count, extraction work must always be executed by a spawned worker sub-agent; even a single-paper extraction must not be performed directly by the parent agent.
- Spawn one worker sub-agent per normalized paper folder.
- Cap concurrency at 5 active paper workers.
- Declare worker ownership at launch: one paper folder, one worker-local temp JSON path, and one worker worktree path.
- Treat the repository as concurrently modified; workers must ignore unrelated changes and must not revert anything outside their ownership.
- Keep the parent focused on orchestration, validation review, retries, and publication after workers launch.
- Retry a failed paper once with a focused correction prompt. If it still fails, return the failure reason and temp JSON path.

### Worker execution

- Process exactly one normalized paper folder.
- Require these inputs: `<paper_token>.md`, `<paper_token>_content_list_v2.json`, `images/`, and `table/`.
- Read the markdown first for context, then read the relevant `table/` images for every specimen-bearing table used in extraction.
- Extract table data by reconciling the markdown table text against the corresponding `table/` image; do not extract specimen rows from markdown tables alone.
- Resolve `fc_basis` by following `references/extraction-rules.md` §6.2.1 (Concrete-Strength Basis Resolution). Before interpreting symbols such as `fck`, `fc`, `f'c`, or `Fc`, first search nearby material/property text, table headers, and footnotes for concrete-strength-grade signals such as `C30`, `C40`, `C50`, `C60`, or `C60/75`. That section defines the priority order, country/context rules, cross-code symbol disambiguation, and ambiguity fallback. Do not assign `fc_basis` without consulting those rules.
- Inside the worker sandbox, use `scripts/safe_calc.py` for conversions, rounding, and derived values; do not do ad hoc arithmetic.
- Preserve eccentricity signs exactly as source evidence shows them.
- Do not exclude ordinary CFST specimens from the dataset based on the sign pattern of `e1` and `e2` alone.
- Preserve recycled aggregate replacement ratio `R%` in `r_ratio`.

### Output shape

- Produce the schema-v2.1 top-level keys `schema_version`, `paper_id`, `is_valid`, `is_ordinary_cfst`, `reason`, `ordinary_filter`, `ref_info`, `paper_level`, `Group_A`, `Group_B`, and `Group_C`.
- Treat `is_valid=false` as an unusable paper with empty specimen groups.
- Treat `is_valid=true` as usable; extract all specimens regardless of ordinary status.
- Tag each specimen with `is_ordinary` and `ordinary_exclusion_reasons` using the two-tier evaluation in `references/extraction-rules.md` §2.
- Derive `is_ordinary_cfst` from specimen flags: `true` when at least one specimen has `is_ordinary=true`.
- Keep worker output in `tmp/<paper_id>/<paper_id>.json` only.
- Let the parent publish the final JSON into `output/<paper_id>.json`; workers must never write final outputs directly.
- Treat published JSON as canonical. Any project-specific tabular conversion should happen outside this skill.

### Git and sandbox isolation

- Require a git repository with `HEAD` before creating worktrees.
- Initialize one when needed:

```bash
python .codex/skills/cfst-paper-extractor/scripts/bootstrap_git_repo.py \
  --repo-root . \
  --initial-empty-commit
```

- Create every worker environment with `scripts/git_worktree_isolation.py create`.
- Launch every worker only through `scripts/worker_sandbox.py`.
- The paper folder is mounted read-only inside the sandbox; only the declared worker-local temp output directory is writable.
- `scripts/safe_calc.py` and `scripts/validate_single_output.py` are sandbox-only helpers in this variant; they fail fast if `CFST_SANDBOX=1` is missing.
- Require `bubblewrap` or `bwrap`.
- Treat sandbox startup failure as fatal; do not fall back to unsandboxed execution.
- Remove finished worktrees with `scripts/git_worktree_isolation.py remove`.

## Use These Bundled Scripts

- `scripts/prepare_batch.py`: preferred entry point; discover raw paper folders, normalize them, and write manifests/state for worker orchestration.
- `scripts/reorganize_parsed_with_tables.py`: run standalone only when you need normalization without the full batch wrapper or need a dry run or summary.
- `scripts/validate_single_output.py`: sandbox-only validator for one worker-local schema-v2 JSON; checks shape, provenance, plausibility, ordinary-filter consistency, and rounding.
- `scripts/publish_validated_output.py`: revalidate worker outputs, publish final JSON, and append a publish log.
- `scripts/git_worktree_isolation.py`: create and remove per-paper git worktrees with declared sandbox paths.
- `scripts/worker_sandbox.py`: mandatory worker launcher; it mounts paper inputs read-only and the worker-local output directory read-write; never bypass it.
- `scripts/bootstrap_git_repo.py`: initialize a repo and optional empty commit so worktree execution can start.
- `scripts/checkpoint_output_commits.py`: commit or push published outputs at fixed intervals when the repository policy calls for output-only checkpoints.
- `scripts/safe_calc.py`: sandbox-only arithmetic helper for deterministic conversions and derived geometry values instead of handwritten calculations.

## Read These References

- `references/extraction-rules.md`: use for schema details, group mapping, required fields, evidence format, loading-mode decisions, numeric rules, mandatory table-image reconciliation, and invalid-output handling.
- `references/single-flow.md`: use for one-paper worker sequencing, required input layout, mandatory table-image reconciliation, setup-figure rules, and validation expectations.
