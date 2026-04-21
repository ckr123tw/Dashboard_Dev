#!/usr/bin/env bash
set -eu
MF="$HOME/miniforge3"
# shellcheck disable=SC1091
source "$MF/etc/profile.d/conda.sh"
conda activate pecan-dash
cd /mnt/c/DinMA/Projects/Dashboard_Dev
pytest -q "$@"
