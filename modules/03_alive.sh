#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
SUBS="$RUN_DIR/subdomains.txt"
OUT_TXT="$RUN_DIR/alive.txt"
OUT_JSON="$RUN_DIR/alive.json"

if [ -f "$SUBS" ] && command -v httpx >/dev/null 2>&1; then
  httpx -silent -l "$SUBS" -status-code -title > "$OUT_TXT" || true
else
  if curl -skI "https://$DOMAIN" >/dev/null 2>&1; then
    echo "https://$DOMAIN [200]" > "$OUT_TXT"
  else
    : > "$OUT_TXT"
  fi
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path
domain, txt, out_json, summary = sys.argv[1:5]
alive = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()]
Path(out_json).write_text(json.dumps({"domain":domain,"alive_hosts":alive}, indent=2))
obj = json.loads(Path(summary).read_text())
obj["modules"]["alive"] = {"txt": txt, "json": out_json, "count": len(alive)}
obj["highlights"]["alive_hosts"] = len(alive)
Path(summary).write_text(json.dumps(obj, indent=2))
PY
