#!/usr/bin/env bash
set -euo pipefail
DOMAIN="$1"; RUN_DIR="$2"; SUMMARY="$3"
URLS="$RUN_DIR/urls.txt"
OUT_TXT="$RUN_DIR/xss_candidates.txt"
OUT_JSON="$RUN_DIR/xss_candidates.json"
: > "$OUT_TXT"

if [ -f "$URLS" ] && [ -s "$URLS" ]; then
  if command -v gf >/dev/null 2>&1; then
    gf xss < "$URLS" > "$OUT_TXT" || true
  else
    grep '=' "$URLS" > "$OUT_TXT" || true
  fi

  if command -v uro >/dev/null 2>&1; then
    uro < "$OUT_TXT" > "$RUN_DIR/.xss.uro" || true
    mv "$RUN_DIR/.xss.uro" "$OUT_TXT"
  fi
fi

python3 - "$DOMAIN" "$OUT_TXT" "$OUT_JSON" "$SUMMARY" <<'PY'
import json,sys
from pathlib import Path

domain, txt, out_json, summary = sys.argv[1:5]
rows = [x.strip() for x in Path(txt).read_text().splitlines() if x.strip()] if Path(txt).exists() else []
Path(out_json).write_text(json.dumps({"domain": domain, "xss_candidates": rows}, indent=2), encoding="utf-8")
obj = json.loads(Path(summary).read_text(encoding="utf-8"))
obj["modules"]["xss_candidates"] = {"txt": txt, "json": out_json, "count": len(rows)}
obj["highlights"]["xss_candidates"] = len(rows)
Path(summary).write_text(json.dumps(obj, indent=2), encoding="utf-8")
PY
