#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
OUT_TXT="$RUN_DIR/dns.txt"
OUT_JSON="$RUN_DIR/dns.json"

{
  echo "# DNS lookup for $DOMAIN"
  dig +short A "$DOMAIN" || true
  dig +short AAAA "$DOMAIN" || true
  dig +short MX "$DOMAIN" || true
  dig +short NS "$DOMAIN" || true
} | sed '/^$/d' | sort -u > "$OUT_TXT"

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path
domain, txt, out_json, summary = sys.argv[1:5]
records = Path(txt).read_text().splitlines()
Path(out_json).write_text(json.dumps({"domain":domain,"records":records}, indent=2))
obj = json.loads(Path(summary).read_text())
obj["modules"]["dns"] = {"txt": txt, "json": out_json, "count": len(records)}
obj["highlights"]["dns_records"] = len(records)
Path(summary).write_text(json.dumps(obj, indent=2))
PY
