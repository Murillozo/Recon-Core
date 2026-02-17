#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
OUT_TXT="$RUN_DIR/urls.txt"
OUT_JSON="$RUN_DIR/urls.json"

: > "$OUT_TXT"
if command -v gau >/dev/null 2>&1; then
  gau "$DOMAIN" >> "$OUT_TXT" || true
fi
if command -v waybackurls >/dev/null 2>&1; then
  echo "$DOMAIN" | waybackurls >> "$OUT_TXT" || true
fi
sort -u "$OUT_TXT" -o "$OUT_TXT"

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path
domain, txt, out_json, summary = sys.argv[1:5]
urls = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()]
Path(out_json).write_text(json.dumps({"domain":domain,"urls":urls}, indent=2))
obj = json.loads(Path(summary).read_text())
obj["modules"]["urls"] = {"txt": txt, "json": out_json, "count": len(urls)}
obj["highlights"]["urls"] = len(urls)
Path(summary).write_text(json.dumps(obj, indent=2))
PY
