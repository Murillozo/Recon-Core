#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
OUT_TXT="$RUN_DIR/subdomains.txt"
OUT_JSON="$RUN_DIR/subdomains.json"
TMP="$RUN_DIR/.sub.tmp"
: > "$TMP"

if command -v subfinder >/dev/null 2>&1; then
  subfinder -silent -d "$DOMAIN" >> "$TMP" || true
fi
if command -v assetfinder >/dev/null 2>&1; then
  assetfinder --subs-only "$DOMAIN" >> "$TMP" || true
fi
if [ ! -s "$TMP" ]; then
  printf "%s\n" "$DOMAIN" > "$TMP"
fi

sort -u "$TMP" > "$OUT_TXT"

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path
domain, txt, out_json, summary = sys.argv[1:5]
subs = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()]
Path(out_json).write_text(json.dumps({"domain":domain,"subdomains":subs}, indent=2))
obj = json.loads(Path(summary).read_text())
obj["modules"]["subdomains"] = {"txt": txt, "json": out_json, "count": len(subs)}
obj["highlights"]["subdomains"] = len(subs)
Path(summary).write_text(json.dumps(obj, indent=2))
PY
