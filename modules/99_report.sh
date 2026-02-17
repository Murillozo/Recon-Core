#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
REPORT="$RUN_DIR/report.md"

python3 - "$DOMAIN" "$SUMMARY" "$REPORT" <<'PY'
import json,sys
from datetime import datetime
from pathlib import Path

domain, summary_path, report_path = sys.argv[1:4]
summary = json.loads(Path(summary_path).read_text())
high = summary.get("highlights", {})
modules = summary.get("modules", {})

lines = [
    f"# Recon Report - {domain}",
    "",
    f"- Job ID: {summary.get('job_id')}",
    f"- Perfil: {summary.get('profile')}",
    f"- Gerado em: {datetime.utcnow().isoformat()} UTC",
    "",
    "## Destaques",
]
for k,v in high.items():
    lines.append(f"- **{k}**: {v}")

lines.append("\n## Artefatos por módulo")
for module, meta in modules.items():
    lines.append(f"### {module}")
    lines.append(f"- TXT: `{meta.get('txt')}`")
    lines.append(f"- JSON: `{meta.get('json')}`")
    lines.append(f"- Count: `{meta.get('count')}`")

Path(report_path).write_text("\n".join(lines), encoding="utf-8")
PY
