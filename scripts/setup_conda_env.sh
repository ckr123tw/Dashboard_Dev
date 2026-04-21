#!/usr/bin/env bash
# Create or update the project's conda env.
#
# Behaviour:
#   - If conda is on PATH, uses it.
#   - Otherwise, if INSTALL_MINIFORGE=1 is set, bootstraps Miniforge into
#     $MINIFORGE_HOME (default ~/miniforge3) and uses that.
#   - Otherwise prints an actionable error.
#
# Works on Linux, macOS, and WSL. Idempotent: re-running updates the env
# via `conda env update --prune`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
cd "${REPO_ROOT}"

ENV_NAME="${ENV_NAME:-pecan-dash}"

bootstrap_miniforge() {
    local target="${MINIFORGE_HOME:-$HOME/miniforge3}"
    if [ -x "${target}/bin/conda" ]; then
        echo ">>> Miniforge already present at ${target}"
    else
        local os arch url
        os="$(uname -s)"
        arch="$(uname -m)"
        url="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-${os}-${arch}.sh"

        echo ">>> Installing Miniforge into ${target} (${os}/${arch})"
        local tmp
        tmp="$(mktemp -d)"
        curl -fsSL "${url}" -o "${tmp}/miniforge.sh"
        bash "${tmp}/miniforge.sh" -b -p "${target}"
        rm -rf "${tmp}"
    fi
    # shellcheck disable=SC1091
    source "${target}/etc/profile.d/conda.sh"
}

if command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
elif [ "${INSTALL_MINIFORGE:-0}" = "1" ]; then
    bootstrap_miniforge
else
    cat >&2 <<EOF
ERROR: conda is not on PATH.
Options:
  1. Install Miniforge manually:
       https://github.com/conda-forge/miniforge
  2. Re-run with INSTALL_MINIFORGE=1 to let this script install it:
       INSTALL_MINIFORGE=1 bash scripts/setup_conda_env.sh
EOF
    exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
    echo ">>> Updating existing env '${ENV_NAME}'"
    conda env update -n "${ENV_NAME}" -f environment.yml --prune
else
    echo ">>> Creating env '${ENV_NAME}'"
    conda env create -f environment.yml
fi

echo ">>> Verifying imports"
conda run -n "${ENV_NAME}" python -c \
    "import dash, plotly, pandas, pytest; \
     print(f'dash={dash.__version__} plotly={plotly.__version__} pandas={pandas.__version__}')"

cat <<EOF

>>> DONE. Activate with:
    conda activate ${ENV_NAME}
EOF
