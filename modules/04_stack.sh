#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
ALIVE="$RUN_DIR/alive.txt"
OUT_TXT="$RUN_DIR/stack.txt"
OUT_JSON="$RUN_DIR/stack.json"

: > "$OUT_TXT"
if [ -f "$ALIVE" ] && [ -s "$ALIVE" ]; then
  while IFS= read -r line; do
    url="$(echo "$line" | awk '{print $1}')"
    server="$(curl -skI "$url" | awk -F': ' 'tolower($1)=="server"{print $2}' | tr -d '\r')"
    tech="$(curl -skI "$url" | awk -F': ' 'tolower($1)=="x-powered-by"{print $2}' | tr -d '\r')"
    echo "$url | server=${server:-unknown} | x-powered-by=${tech:-unknown}" >> "$OUT_TXT"
  done < "$ALIVE"
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path
domain, txt, out_json, summary = sys.argv[1:5]
entries = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()]
Path(out_json).write_text(json.dumps({"domain":domain,"fingerprints":entries}, indent=2))
obj = json.loads(Path(summary).read_text())
obj["modules"]["stack"] = {"txt": txt, "json": out_json, "count": len(entries)}
obj["highlights"]["fingerprints"] = len(entries)
Path(summary).write_text(json.dumps(obj, indent=2))
PY
