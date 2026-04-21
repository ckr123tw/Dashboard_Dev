#!/usr/bin/env bash
# Install miniforge into ~/miniforge3 (if absent) and create the pecan-dash conda env.
# Idempotent: re-running upgrades the env via --prune.
set -euo pipefail

MF="$HOME/miniforge3"
PROJECT_DIR="/mnt/c/DinMA/Projects/Dashboard_Dev"

if [ ! -x "$MF/bin/conda" ]; then
    echo ">>> Installing Miniforge into $MF"
    cd /tmp
    if [ ! -f mf.sh ]; then
        wget -q \
            https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
            -O mf.sh
    fi
    bash mf.sh -b -p "$MF"
else
    echo ">>> Miniforge already present at $MF"
fi

# shellcheck disable=SC1091
source "$MF/etc/profile.d/conda.sh"
conda --version

cd "$PROJECT_DIR"

if conda env list | awk '{print $1}' | grep -qx pecan-dash; then
    echo ">>> Updating existing pecan-dash env"
    conda env update -n pecan-dash -f environment.yml --prune
else
    echo ">>> Creating pecan-dash env"
    conda env create -f environment.yml
fi

echo ">>> Verifying imports"
conda run -n pecan-dash python -c "import dash, plotly, pandas, pytest; print('dash', dash.__version__, 'plotly', plotly.__version__, 'pandas', pandas.__version__)"
echo ">>> DONE"
