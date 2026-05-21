"""Markdown validation report generation from harness results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Template

REPORT_TEMPLATE = Template("""# Zenlo Audit Validation Report

**Unit:** {{ unit_type }} `{{ unit_id }}`
**NHANES cycle:** {{ cycle }}
**Generated:** {{ generated_at }}

## Cohort summary

| Metric | Value |
|--------|-------|
| Total rows | {{ cohort.n_total }} |
| Valid / detected | {{ cohort_display }} |

## Distribution

```json
{{ distribution_json }}
```

## Agreement

```json
{{ agreement_json }}
```

## Fairness / subgroups

```json
{{ fairness_json }}
```

---

*Independent audit harness — not attorney-reviewed. For validation research only.*
""")


def render_markdown_report(results: dict[str, Any]) -> str:
    cohort_display = results["cohort"].get("n_valid", results["cohort"].get("n_detected", "—"))
    return REPORT_TEMPLATE.render(
        cohort_display=cohort_display,
        distribution_json=json.dumps(results.get("distribution", {}), indent=2, default=str),
        agreement_json=json.dumps(results.get("agreement", {}), indent=2, default=str),
        fairness_json=json.dumps(results.get("fairness", {}), indent=2, default=str),
        **results,
    )


def write_report(results: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(render_markdown_report(results), encoding="utf-8")


def write_json(results: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
