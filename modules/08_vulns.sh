#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
ALIVE="$RUN_DIR/alive.txt"
OUT_TXT="$RUN_DIR/vulns.txt"
OUT_JSON="$RUN_DIR/vulns.json"
: > "$OUT_TXT"

if [ -f "$ALIVE" ] && [ -s "$ALIVE" ] && command -v nuclei >/dev/null 2>&1; then
  awk '{print $1}' "$ALIVE" | nuclei -silent -severity low,medium,high,critical > "$OUT_TXT" || true
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path

domain, txt, out_json, summary = sys.argv[1:5]
rows = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()] if Path(txt).exists() else []
Path(out_json).write_text(json.dumps({"domain": domain, "nuclei_findings": rows}, indent=2), encoding="utf-8")
obj = json.loads(Path(summary).read_text(encoding="utf-8"))
obj["modules"]["vulns"] = {"txt": txt, "json": out_json, "count": len(rows)}
obj["highlights"]["nuclei_findings"] = len(rows)
Path(summary).write_text(json.dumps(obj, indent=2), encoding="utf-8")
PY
