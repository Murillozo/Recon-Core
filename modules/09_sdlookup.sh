#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
OUT_TXT="$RUN_DIR/sdlookup.txt"
OUT_JSON="$RUN_DIR/sdlookup.json"
: > "$OUT_TXT"

if command -v httpx >/dev/null 2>&1 && command -v sdlookup >/dev/null 2>&1; then
  echo "$DOMAIN" | httpx -silent -ip 2>/dev/null | awk '{print $2}' | tr -d '[]' | sort -u > "$RUN_DIR/ips.txt" || true
  if [ -s "$RUN_DIR/ips.txt" ]; then
    while IFS= read -r ip; do
      [ -z "$ip" ] && continue
      echo "$ip" | sdlookup -json >> "$OUT_TXT" || true
    done < "$RUN_DIR/ips.txt"
  fi
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path

domain, txt, out_json, summary = sys.argv[1:5]
rows = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()] if Path(txt).exists() else []
Path(out_json).write_text(json.dumps({"domain": domain, "sdlookup": rows}, indent=2), encoding="utf-8")
obj = json.loads(Path(summary).read_text(encoding="utf-8"))
obj["modules"]["sdlookup"] = {"txt": txt, "json": out_json, "count": len(rows)}
obj["highlights"]["sdlookup_rows"] = len(rows)
Path(summary).write_text(json.dumps(obj, indent=2), encoding="utf-8")
PY
