#!/usr/bin/env bash
set -eu
MF="$HOME/miniforge3"
# shellcheck disable=SC1091
source "$MF/etc/profile.d/conda.sh"
conda activate pecan-dash
pip install "databricks-sql-connector>=3.3" "databricks-sdk>=0.30"
python -c "import databricks.sql, databricks.sdk; print('databricks-sql-connector', databricks.sql.__version__); from databricks.sdk import WorkspaceClient; print('databricks-sdk OK')"
