#!/usr/bin/env bash
# Syntax-check every YAML file under databricks/ plus environment.yml.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${HERE}/_lib.sh"
activate_env
cd "${REPO_ROOT}"

python - <<'PY'
import pathlib

try:
    import yaml
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml"])
    import yaml

targets = sorted(
    list(pathlib.Path("databricks").glob("*.yml"))
    + list(pathlib.Path("databricks").glob("*.yaml"))
    + [pathlib.Path("environment.yml")]
)
for p in targets:
    yaml.safe_load(p.read_text())
    print(f"{p} -> OK")
PY
