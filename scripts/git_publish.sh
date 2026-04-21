#!/usr/bin/env bash
# Initialise the repo, normalise line endings, commit, create the GitHub
# repository, and push. Idempotent enough to re-run: if the repo already
# exists locally or remotely it just does what's still missing.
set -euo pipefail

cd /mnt/c/DinMA/Projects/Dashboard_Dev

REPO_NAME="${REPO_NAME:-Dashboard_Dev}"
VISIBILITY="${VISIBILITY:-public}"
DESCRIPTION="${DESCRIPTION:-PeCan-style variant prevalence dashboard (Plotly/Dash) with Databricks deployment.}"

# Normalise line endings inside the repo to LF. Files on /mnt/c/ often come
# back as CRLF; .gitattributes + a one-shot sed sweep fixes that before the
# first commit so the initial history is clean.
echo ">>> normalising line endings on text files"
while IFS= read -r -d '' f; do
    # Skip binaries and any CSV we haven't touched.
    case "$f" in
        ./.git/*|./.pytest_cache/*|./__pycache__/*|*/__pycache__/*|*.pyc) continue;;
    esac
    sed -i 's/\r$//' "$f" || true
done < <(find . -type f \( \
    -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.yml" \
    -o -name "*.yaml" -o -name "*.csv" -o -name "*.txt" -o -name "*.toml" \
    -o -name "*.css" -o -name ".gitignore" -o -name ".gitattributes" \
    \) -print0)

chmod +x scripts/*.sh databricks/deploy.sh || true

# --- git init ------------------------------------------------------------
if [ ! -d .git ]; then
    echo ">>> git init"
    git init -q
    git symbolic-ref HEAD refs/heads/main
else
    echo ">>> git repo already initialised"
fi

# --- stage + commit ------------------------------------------------------
git add -A
if git diff --cached --quiet; then
    echo ">>> nothing to commit"
else
    echo ">>> creating commit"
    git commit -q -m "Initial commit: variant prevalence dashboard prototype

- Dash/Plotly prototype modelled on St. Jude PeCan Variant Prevalence page
- Three-row prevalence chart (class proportion / origin / prevalence %)
  with pathway-grouped bars, sunburst navigator, filter panel
- Deterministic toy dataset (3 roots, 16 subtypes, 343 samples, 852 variants)
- Documented ingestion schema (docs/data_schema.md) with strict validation
- Conda env spec (Python 3.11, Dash 4, Plotly 6)
- Databricks deployment: Delta-backed loader, PySpark ingest notebook,
  Databricks Apps manifest (app.yaml), and Asset Bundle (databricks.yml)
- pytest suite (22 tests, all passing)"
fi

# --- create github repo --------------------------------------------------
if git remote get-url origin >/dev/null 2>&1; then
    echo ">>> origin already set: $(git remote get-url origin)"
else
    echo ">>> creating GitHub repository ${REPO_NAME} (${VISIBILITY})"
    gh repo create "${REPO_NAME}" \
        "--${VISIBILITY}" \
        --source=. \
        --remote=origin \
        --description "${DESCRIPTION}" \
        --push
fi

# --- push (covers re-runs where the repo exists but the branch is behind) -
if git remote get-url origin >/dev/null 2>&1; then
    current_branch="$(git symbolic-ref --short HEAD)"
    echo ">>> pushing ${current_branch} to origin"
    git push -u origin "${current_branch}" 2>&1 | tail -n 20 || true
fi

echo ">>> DONE"
gh repo view --json url,visibility,defaultBranchRef --jq '{url, visibility, default: .defaultBranchRef.name}' 2>/dev/null || true
