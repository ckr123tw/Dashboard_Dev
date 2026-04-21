#!/usr/bin/env bash
set -eu
MF="$HOME/miniforge3"
# shellcheck disable=SC1091
source "$MF/etc/profile.d/conda.sh"
conda activate pecan-dash
cd /mnt/c/DinMA/Projects/Dashboard_Dev

DASHBOARD_DEBUG=0 DASHBOARD_PORT=8051 python -m app.main >/tmp/dash.out 2>&1 &
APP_PID=$!
trap 'kill $APP_PID 2>/dev/null || true' EXIT

for i in $(seq 1 20); do
  if curl -fsS -o /tmp/dash_index.html http://127.0.0.1:8051/; then
    echo "server up after ${i} polls"
    break
  fi
  sleep 0.5
done

if [ ! -s /tmp/dash_index.html ]; then
  echo "!! no response"
  cat /tmp/dash.out
  exit 1
fi

echo "--- index size: $(wc -c </tmp/dash_index.html) bytes"
grep -o '<title>[^<]*</title>' /tmp/dash_index.html || true

# Grab dash's app-entry JSON so we can see the layout was actually created.
curl -fsS http://127.0.0.1:8051/_dash-layout | python -c "
import json, sys
layout = json.load(sys.stdin)
def walk(node, depth=0):
    if isinstance(node, dict):
        t = node.get('type')
        cid = (node.get('props') or {}).get('id')
        if t and cid:
            print('  ' * depth + f'{t} id={cid}')
        for v in (node.get('props') or {}).values():
            walk(v, depth + 1)
    elif isinstance(node, list):
        for v in node:
            walk(v, depth)
walk(layout)
"
