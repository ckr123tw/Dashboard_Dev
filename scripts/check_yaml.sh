#!/usr/bin/env bash
set -eu
MF="$HOME/miniforge3"
# shellcheck disable=SC1091
source "$MF/etc/profile.d/conda.sh"
conda activate pecan-dash
cd /mnt/c/DinMA/Projects/Dashboard_Dev
python - <<'PY'
import yaml, pathlib
root = pathlib.Path("databricks")
for p in sorted(list(root.glob("*.yml")) + list(root.glob("*.yaml"))):
    yaml.safe_load(p.read_text())
    print(f"{p} -> OK")
print("environment.yml ->", type(yaml.safe_load(open("environment.yml").read())).__name__)
PY
