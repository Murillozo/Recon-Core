#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
OUT_TXT="$RUN_DIR/ports.txt"
OUT_JSON="$RUN_DIR/ports.json"

if command -v naabu >/dev/null 2>&1; then
  naabu -host "$DOMAIN" -silent > "$OUT_TXT" || true
elif command -v nmap >/dev/null 2>&1; then
  nmap -Pn -T4 --top-ports 100 "$DOMAIN" | awk '/^[0-9]+\// {print $1" "$2" "$3}' > "$OUT_TXT" || true
else
  : > "$OUT_TXT"
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path
domain, txt, out_json, summary = sys.argv[1:5]
ports = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()]
Path(out_json).write_text(json.dumps({"domain":domain,"ports":ports}, indent=2))
obj = json.loads(Path(summary).read_text())
obj["modules"]["ports"] = {"txt": txt, "json": out_json, "count": len(ports)}
obj["highlights"]["open_ports"] = len(ports)
Path(summary).write_text(json.dumps(obj, indent=2))
PY
