## CFST Paper Extractor

Workspace-local enhanced version of `cfst-paper-extractor`, adapted for:

- ordinary CFST filtering
- field-level provenance
- stricter physical validation
- batch preparation directly from MinerU paper folders
- ML/DL-oriented unified flat export

For eccentric specimens, `e1` and `e2` signs are preserved as source evidence. Opposite signs are allowed and are not used by themselves to exclude an ordinary specimen.

### Main additions

- `scripts/prepare_batch.py`
  - discovers available MinerU paper folders
  - preprocesses them into normalized `images/ + table/` folders
  - writes batch manifests, worker-job specs, and state files
- `scripts/validate_single_output.py`
  - validates schema v2 outputs
  - enforces ordinary-CFST tagging and physical plausibility
- `scripts/export_unified_dataset.py`
  - flattens validated JSON into ML-ready CSV
- `scripts/publish_validated_output.py`
  - validates worker JSON, publishes to `output/`, and records publish logs
- `scripts/bootstrap_git_repo.py`
  - optional helper to initialize a repo for worktree-based execution

### Suggested workflow

1. Prepare paper manifests directly from MinerU folders:

```bash
python .codex/skills/cfst-paper-extractor/scripts/prepare_batch.py \
  --raw-root . \
  --output-root runs/a1_demo
```

2. Extract one paper into schema v2 JSON using the rules in:

- `.codex/skills/cfst-paper-extractor/references/extraction-rules.md`
- `.codex/skills/cfst-paper-extractor/references/single-flow.md`

3. Validate one paper:

```bash
python .codex/skills/cfst-paper-extractor/scripts/validate_single_output.py \
  --json-path runs/a1_demo/tmp/A1-1/A1-1.json \
  --expect-valid true \
  --strict-rounding
```

4. Publish validated outputs:

```bash
python .codex/skills/cfst-paper-extractor/scripts/publish_validated_output.py \
  --batch-manifest runs/a1_demo/manifests/batch_manifest.json \
  --tmp-root runs/a1_demo/tmp \
  --output-dir runs/a1_demo/output \
  --publish-log runs/a1_demo/logs/publish_log.jsonl
```

5. Export unified CSV:

```bash
python .codex/skills/cfst-paper-extractor/scripts/export_unified_dataset.py \
  --input-dir runs/a1_demo/output \
  --output-csv runs/a1_demo/exports/unified_dataset.csv
```
