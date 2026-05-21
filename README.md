# zenlo-audit

Independent Python audit harness for validating **Zenlo Labs** biomarker classifiers and clinical pattern detectors against **NHANES** population data.

## Purpose

This repository re-implements Zenlo's classification logic from **cited clinical specifications** — not by copying the production TypeScript codebase. Two independent implementations that agree strengthen validation; divergences are audit findings.

Outputs support Validation Reports (~121 audit units): distribution statistics, agreement metrics, and fairness/subgroup analyses suitable for model cards and regulatory documentation.

## License

MIT — Copyright (c) 2026 Zenlo LLC. See [LICENSE](LICENSE).

## Requirements

- Python **3.12**
- NHANES XPT files (not included — see [Data setup](#data-setup))

## Setup

```bash
cd ~/Projects/zenlo-audit
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data setup

NHANES XPT files live in **per-cycle subfolders** under the data root:

```
data/nhanes/2015-2016/DEMO_I.XPT
data/nhanes/2015-2016/GLU_I.XPT
...
```

Or set the root (cycle subfolder is appended automatically):

```bash
export ZENLO_AUDIT_DATA=/path/to/nhanes   # loader reads $ZENLO_AUDIT_DATA/2015-2016/*.XPT
```

### Expected files — cycle 2015-2016 (suffix `I`)

Place these in `data/nhanes/2015-2016/` (or `$ZENLO_AUDIT_DATA/2015-2016/`):

| File | NHANES column | Harness code |
|------|---------------|--------------|
| `DEMO_I.XPT` | SEQN, RIDAGEYR, RIAGENDR, RIDRETH3 | demographics |
| `GLU_I.XPT` | LBXGLU | **GLU** |
| `INS_I.XPT` | LBXIN (or LBDINSI → converted) | **INSULIN** |
| `GHB_I.XPT` | LBXGH | **HBA1C** |
| `HDL_I.XPT` | LBDHDD | **HDL** |
| `TRIGLY_I.XPT` | LBXTR | **TG** |
| `TCHOL_I.XPT` | LBXTC | **TOTAL_CHOL** |

**Not available on DO server for cycle I:** CRP (hs-CRP), BIOPRO (calcium, ferritin). The harness reports `DATA_UNAVAILABLE` for HSCRP, CALCIUM, FERRITIN, and the **inflammation** pattern — it does not crash.

Other supported cycles: `2007-2008` (E), `2011-2012` (G), `2013-2014` (H), `2017-2018` (J) — same file stem pattern with cycle letter, in `data/nhanes/<cycle>/`.

Download from [NHANES](https://wwwn.cdc.gov/nchs/nhanes/) or copy from your server (`~/data/nhanes/` on DO).

## Run CLI

```bash
source .venv/bin/activate

# Single biomarker (cycle 2015-2016 default)
python -m audit_harness.run --biomarker GLU --cycle 2015-2016

# Single pattern
python -m audit_harness.run --pattern metabolic_syndrome --cycle 2015-2016

# All configured units
python -m audit_harness.run --all --cycle 2015-2016
```

Outputs land in `output/`:

- `{UNIT}_results.json` — full results + manifest wrapper
- `{UNIT}_report.md` — human-readable validation report
- `manifest.json` — reproducibility record (Python version, package pins, input SHA-256 hashes, git commit)

## Unit tests (no XPT required)

```bash
pytest tests_pytest/ -v
```

## External replication

1. Clone this repo (public, MIT).
2. Create venv, `pip install -r requirements.txt`.
3. Download the same NHANES cycle XPT files into `data/nhanes/`.
4. Run `python -m audit_harness.run --biomarker HSCRP --cycle 2017-2018`.
5. Compare `output/manifest.json` file hashes and `output/HSCRP_results.json` to the published reference run.

## Project structure

```
audit_harness/
  loaders/nhanes.py      # XPT merge + cohort filters
  spec/                  # Cited reference ranges + pattern rules (independent)
  classifiers/           # Biomarker + pattern detection
  tests/                 # distribution, agreement, fairness analysis modules
  reporters/markdown.py  # Jinja2 → .md reports
  run.py                 # CLI
tests_pytest/            # pytest for harness code (synthetic fixtures)
```

## Supported units (bootstrap)

**Biomarkers:** HSCRP, GLU, INSULIN, CALCIUM, TG, HDL, HBA1C, LDL

**Patterns:** inflammation, insulin_resistance, metabolic_syndrome

## Disclaimer

Research / validation tooling only. Not legal or medical advice. Independent of Zenlo Labs production deployment.
