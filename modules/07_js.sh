#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
OUT_TXT="$RUN_DIR/js_urls.txt"
OUT_JSON="$RUN_DIR/js_urls.json"
TMP="$RUN_DIR/.js.tmp"
: > "$TMP"

if command -v gauplus >/dev/null 2>&1; then
  echo "$DOMAIN" | gauplus >> "$TMP" || true
fi
if command -v waybackurls >/dev/null 2>&1; then
  echo "$DOMAIN" | waybackurls >> "$TMP" || true
fi
if command -v gau >/dev/null 2>&1; then
  gau "$DOMAIN" >> "$TMP" || true
fi

grep -iE '\.js([?#].*)?$' "$TMP" | sort -u > "$OUT_TXT" || true

if [ -s "$OUT_TXT" ] && command -v httpx >/dev/null 2>&1; then
  httpx -silent -l "$OUT_TXT" -status-code > "$RUN_DIR/js_alive.txt" || true
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path

domain, txt, out_json, summary = sys.argv[1:5]
rows = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()] if Path(txt).exists() else []
Path(out_json).write_text(json.dumps({"domain": domain, "javascript_urls": rows}, indent=2), encoding="utf-8")
obj = json.loads(Path(summary).read_text(encoding="utf-8"))
obj["modules"]["javascript"] = {"txt": txt, "json": out_json, "count": len(rows)}
obj["highlights"]["javascript_urls"] = len(rows)
Path(summary).write_text(json.dumps(obj, indent=2), encoding="utf-8")
PY
