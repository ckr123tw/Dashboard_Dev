#!/usr/bin/env bash
# Shared helpers for the project's shell scripts.
#
# Sourcing this file:
#   - sets REPO_ROOT to the absolute path of the repo (independent of cwd),
#   - defines `activate_env` which activates the conda env (or errors out
#     with an actionable message), searching common install locations.
#
# Intentionally portable (bash, Linux/macOS/WSL, no GNU-specific features).

# Resolve repo root = parent of this file's directory. Works whether invoked
# via `bash scripts/foo.sh`, `./scripts/foo.sh`, or `source _lib.sh`.
_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${_LIB_DIR}/.." && pwd)"
export REPO_ROOT

ENV_NAME="${ENV_NAME:-pecan-dash}"

activate_env() {
    # If conda is already on PATH, trust it.
    if command -v conda >/dev/null 2>&1; then
        # shellcheck disable=SC1091
        source "$(conda info --base)/etc/profile.d/conda.sh"
    else
        # Probe common install locations.
        local candidates=(
            "${CONDA_HOME:-}/etc/profile.d/conda.sh"
            "${MINIFORGE_HOME:-}/etc/profile.d/conda.sh"
            "$HOME/miniforge3/etc/profile.d/conda.sh"
            "$HOME/miniconda3/etc/profile.d/conda.sh"
            "$HOME/anaconda3/etc/profile.d/conda.sh"
            "/opt/conda/etc/profile.d/conda.sh"
            "/opt/miniforge3/etc/profile.d/conda.sh"
        )
        local found=""
        for c in "${candidates[@]}"; do
            if [ -n "${c:-}" ] && [ -f "${c}" ]; then
                found="${c}"
                break
            fi
        done
        if [ -z "${found}" ]; then
            echo >&2 "ERROR: could not locate a conda installation."
            echo >&2 "Install Miniforge (https://github.com/conda-forge/miniforge) or set CONDA_HOME."
            return 1
        fi
        # shellcheck disable=SC1090
        source "${found}"
    fi

    if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
        echo >&2 "ERROR: conda env '${ENV_NAME}' not found."
        echo >&2 "Run scripts/setup_conda_env.sh first (creates the env from environment.yml)."
        return 1
    fi

    conda activate "${ENV_NAME}"
}
