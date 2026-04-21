#!/usr/bin/env bash
# Starts the Dash server in the background, polls it for readiness, fetches
# `/` and `/_dash-layout`, then kills the server. Prints a summary of the
# layout tree to prove the app is wired correctly end-to-end.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${HERE}/_lib.sh"
activate_env
cd "${REPO_ROOT}"

PORT="${PORT:-8051}"
WORK="$(mktemp -d)"
cleanup() { rm -rf "${WORK}"; [ -n "${APP_PID:-}" ] && kill "${APP_PID}" 2>/dev/null || true; }
trap cleanup EXIT

DASHBOARD_DEBUG=0 DASHBOARD_PORT="${PORT}" python -m app.main >"${WORK}/out.log" 2>&1 &
APP_PID=$!

for i in $(seq 1 40); do
    if curl -fsS -o "${WORK}/index.html" "http://127.0.0.1:${PORT}/"; then
        echo "server up after ${i} polls"
        break
    fi
    sleep 0.5
done

if [ ! -s "${WORK}/index.html" ]; then
    echo "!! server did not come up; last log lines:"
    tail -n 40 "${WORK}/out.log"
    exit 1
fi

echo "--- index size: $(wc -c <"${WORK}/index.html") bytes"
grep -o '<title>[^<]*</title>' "${WORK}/index.html" || true

curl -fsS -o "${WORK}/layout.json" "http://127.0.0.1:${PORT}/_dash-layout"
LAYOUT="${WORK}/layout.json" python - <<'PY'
import json, os
with open(os.environ["LAYOUT"]) as fh:
    layout = json.load(fh)

def walk(node, depth=0):
    if isinstance(node, dict):
        t = node.get("type")
        cid = (node.get("props") or {}).get("id")
        if t and cid:
            print("  " * depth + f"{t} id={cid}")
        for v in (node.get("props") or {}).values():
            walk(v, depth + 1)
    elif isinstance(node, list):
        for v in node:
            walk(v, depth)

walk(layout)
PY
