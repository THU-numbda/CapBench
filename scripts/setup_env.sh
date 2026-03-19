#!/usr/bin/env bash
# Thin compatibility helper for CapBench installation and cache defaults.
#
# Preferred install flow:
#   python -m pip install -e ".[all]"
#
# Optional compatibility usage:
#   source scripts/setup_env.sh          # export CAPBENCH_CACHE_DIR
#   source scripts/setup_env.sh install  # install into the current Python env
#
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export CAPBENCH_CACHE_DIR="${CAPBENCH_CACHE_DIR:-${HOME}/.cache/capbench}"

if [[ "${1:-}" == "install" ]]; then
    echo "Installing CapBench into the current Python environment ..."
    (
        cd "$REPO_ROOT" && \
        python -m pip install -e ".[all]"
    ) || return 1 2>/dev/null || exit 1
fi

echo "CAPBENCH_CACHE_DIR=${CAPBENCH_CACHE_DIR}"
echo "Preferred install: cd ${REPO_ROOT} && python -m pip install -e \".[all]\""
