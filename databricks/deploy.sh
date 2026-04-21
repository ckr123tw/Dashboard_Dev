#!/usr/bin/env bash
# One-shot Databricks deployment helper.
#
# Usage:
#     # first time
#     ./deploy.sh init            # validates the bundle
#     ./deploy.sh data            # runs the load_toy_data job
#     ./deploy.sh app             # deploys + starts the Databricks App
#
#     # everything (data + app)
#     ./deploy.sh all
#
# Required env vars (or a configured Databricks CLI profile):
#     DATABRICKS_HOST              e.g. https://adb-xxxxx.yy.azuredatabricks.net
#     DATABRICKS_TOKEN             personal access token (dev)  --OR--
#     DATABRICKS_CLIENT_ID/SECRET  service-principal OAuth
#
# Bundle variables may be overridden on the command line:
#     WAREHOUSE_ID=abcdef ./deploy.sh all
#     TARGET=prod CATALOG=main SCHEMA=variant_dashboard ./deploy.sh all
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cd "$here"

TARGET="${TARGET:-dev}"
CATALOG="${CATALOG:-main}"
SCHEMA="${SCHEMA:-}"            # empty => use the bundle default (per-target)
WAREHOUSE_ID="${WAREHOUSE_ID:-}"
APP_NAME="${APP_NAME:-variant-prevalence}"

var_flags=()
if [[ -n "$CATALOG" ]]; then var_flags+=(--var "catalog=$CATALOG"); fi
if [[ -n "$SCHEMA"  ]]; then var_flags+=(--var "schema=$SCHEMA");   fi
if [[ -n "$WAREHOUSE_ID" ]]; then var_flags+=(--var "warehouse_id=$WAREHOUSE_ID"); fi
if [[ -n "$APP_NAME" ]]; then var_flags+=(--var "app_name=$APP_NAME"); fi

require_cli() {
    if ! command -v databricks >/dev/null 2>&1; then
        echo "!! databricks CLI not found."
        echo "   Install: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
        exit 127
    fi
}

cmd="${1:-all}"
require_cli

case "$cmd" in
    init)
        echo ">>> Validating bundle (target=$TARGET)"
        databricks bundle validate -t "$TARGET" "${var_flags[@]}"
        ;;
    deploy)
        echo ">>> Deploying bundle (target=$TARGET)"
        databricks bundle deploy -t "$TARGET" "${var_flags[@]}"
        ;;
    data)
        echo ">>> Running data-load job"
        databricks bundle deploy -t "$TARGET" "${var_flags[@]}"
        databricks bundle run -t "$TARGET" load_toy_data "${var_flags[@]}"
        ;;
    app)
        echo ">>> Deploying Databricks App '$APP_NAME' (target=$TARGET)"
        databricks bundle deploy -t "$TARGET" "${var_flags[@]}"
        databricks bundle run -t "$TARGET" dashboard "${var_flags[@]}"
        echo ">>> App URL:"
        databricks apps get "$APP_NAME" --output json 2>/dev/null | grep -Eo '"url":"[^"]+"' || true
        ;;
    all)
        "$0" init
        "$0" data
        "$0" app
        ;;
    *)
        echo "Unknown command: $cmd"
        echo "Usage: $0 {init|deploy|data|app|all}"
        exit 2
        ;;
esac
