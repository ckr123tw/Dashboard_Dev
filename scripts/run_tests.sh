#!/usr/bin/env bash
# Run the pytest suite inside the project's conda env.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${HERE}/_lib.sh"
activate_env
cd "${REPO_ROOT}"
pytest -q "$@"
