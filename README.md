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

Place NHANES XPT files in `data/nhanes/` **or** set:

```bash
export ZENLO_AUDIT_DATA=/path/to/nhanes/xpt
```

### Expected files per cycle

For cycle **2017-2018** (suffix `J`), place these files in `DATA_DIR`:

| File | NHANES content | Harness biomarkers |
|------|------------------|-------------------|
| `DEMO_J.XPT` | Demographics | SEQN, RIDAGEYR, RIAGENDR, RIDRETH3 |
| `CRP_J.XPT` | C-reactive protein | LBXCRP → **HSCRP** |
| `GLU_J.XPT` | Fasting glucose + insulin | LBXGLU → **GLU**, LBXIN → **INSULIN** |
| `BIOPRO_J.XPT` | Standard biochemistry | LBXSCA → **CALCIUM**, LBXFER → **FERRITIN**, LBXGH → **HBA1C** |
| `HDL_J.XPT` | HDL cholesterol | LBDHDD → **HDL** |
| `TRIGLY_J.XPT` | Triglycerides | LBXTR → **TG** |

Other supported cycles: `2011-2012` (G), `2013-2014` (H), `2015-2016` (I) — same stem pattern with cycle letter.

Download from [NHANES](https://wwwn.cdc.gov/nchs/nhanes/) or copy from your server (`~/data/nhanes/` on DO).

## Run CLI

```bash
source .venv/bin/activate

# Single biomarker
python -m audit_harness.run --biomarker HSCRP --cycle 2017-2018

# Single pattern
python -m audit_harness.run --pattern inflammation --cycle 2017-2018

# All configured units
python -m audit_harness.run --all --cycle 2017-2018
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
