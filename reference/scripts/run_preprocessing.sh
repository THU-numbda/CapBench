#!/usr/bin/env bash
# Process standard CapBench window buckets through the dataset pipeline.
#
# Usage:
#   python -m pip install -e ".[all]"
#   bash scripts/run_preprocessing.sh
#
# Overrides:
#   NUM_JOBS=2
#   PIPELINE_STAGES="cap3d cnn binary_masks"
#   USE_DEFAULT_NET_NAMES=1

set -euo pipefail

NUM_JOBS="${NUM_JOBS:-1}"
PIPELINE_STAGES="${PIPELINE_STAGES:-cap3d cnn binary_masks}"
USE_DEFAULT_NET_NAMES="${USE_DEFAULT_NET_NAMES:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PIPELINE_SCRIPT="window_tools/window_processing_pipeline.py"
LOG_DIR="log/preprocessing"
JOBLOG="${LOG_DIR}/parallel_joblog.tsv"
SUMMARY_TSV="${LOG_DIR}/summary.tsv"

mkdir -p "$LOG_DIR"

if ! command -v parallel &>/dev/null; then
    echo "ERROR: GNU parallel is required for this developer script. Install it separately and rerun."
    exit 1
fi

# Format: NAME|DATASET_PATH|WINDOWS_FILE
ALL_TASKS=(
    "nangate45_small|datasets/nangate45/small|datasets/nangate45/small/windows.yaml"
    "nangate45_medium|datasets/nangate45/medium|datasets/nangate45/medium/windows.yaml"
    "nangate45_large|datasets/nangate45/large|datasets/nangate45/large/windows.yaml"
    "sky130hd_small|datasets/sky130hd/small|datasets/sky130hd/small/windows.yaml"
    "sky130hd_medium|datasets/sky130hd/medium|datasets/sky130hd/medium/windows.yaml"
    "sky130hd_large|datasets/sky130hd/large|datasets/sky130hd/large/windows.yaml"
)

TASKS=()
for spec in "${ALL_TASKS[@]}"; do
    IFS='|' read -r name dataset_path windows_file <<< "$spec"
    if [[ -f "$windows_file" ]]; then
        TASKS+=("$spec")
    else
        echo "Skipping $name: missing windows file $windows_file"
    fi
done

if [[ "${#TASKS[@]}" -eq 0 ]]; then
    echo "ERROR: No preprocessing tasks are runnable."
    exit 1
fi

echo "Window preprocessing: ${#TASKS[@]} task(s)"
echo "Parallel jobs: $NUM_JOBS"
echo "Pipeline stages: $PIPELINE_STAGES"
echo "Job log: $JOBLOG"
echo ""

export PIPELINE_SCRIPT LOG_DIR PIPELINE_STAGES USE_DEFAULT_NET_NAMES

run_one() {
    local spec="$1"
    local name dataset_path windows_file
    IFS='|' read -r name dataset_path windows_file <<< "$spec"

    local stdout_file="${LOG_DIR}/${name}_stdout.txt"
    local result_file="${LOG_DIR}/${name}.result.tsv"
    local status="failed"
    local exit_code=1
    local -a pipeline_args=()
    read -r -a pipeline_args <<< "$PIPELINE_STAGES"

    local -a cmd=(
        python3 "$PIPELINE_SCRIPT"
        --windows-file "$windows_file"
        --dataset-path "$dataset_path"
        --pipeline "${pipeline_args[@]}"
    )

    if [[ "$USE_DEFAULT_NET_NAMES" == "1" ]]; then
        cmd+=(--default-net-names)
    fi

    local start_ts
    start_ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$start_ts] START $name | dataset=${dataset_path} | windows=${windows_file}"

    if "${cmd[@]}" >"$stdout_file" 2>&1; then
        status="ok"
        exit_code=0
    else
        exit_code=$?
    fi

    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$name" \
        "$dataset_path" \
        "$windows_file" \
        "$status" \
        "$exit_code" \
        "$stdout_file" \
        > "$result_file"

    local end_ts
    end_ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$end_ts] DONE $name | status=${status}, exit=${exit_code}"

    return "$exit_code"
}
export -f run_one

set +e
printf '%s\n' "${TASKS[@]}" | \
    parallel \
        --jobs "$NUM_JOBS" \
        --joblog "$JOBLOG" \
        --line-buffer \
        --env PIPELINE_SCRIPT --env LOG_DIR --env PIPELINE_STAGES --env USE_DEFAULT_NET_NAMES \
        run_one {}
PARALLEL_EXIT=$?
set -e

printf 'name\tdataset_path\twindows_file\tstatus\texit_code\tstdout_log\n' > "$SUMMARY_TSV"
for spec in "${TASKS[@]}"; do
    IFS='|' read -r name dataset_path windows_file <<< "$spec"
    result_file="${LOG_DIR}/${name}.result.tsv"
    if [[ -f "$result_file" ]]; then
        cat "$result_file" >> "$SUMMARY_TSV"
    else
        printf '%s\t%s\t%s\tmissing\t\t%s\n' \
            "$name" "$dataset_path" "$windows_file" "${LOG_DIR}/${name}_stdout.txt" \
            >> "$SUMMARY_TSV"
    fi
done

echo ""
echo "==================================================="
echo " PREPROCESSING SUMMARY"
echo "==================================================="

TOTAL=${#TASKS[@]}
FAILED=$(awk -F'\t' 'NR > 1 && $4 != "ok" {count++} END {print count + 0}' "$SUMMARY_TSV")
PASSED=$((TOTAL - FAILED))

echo "Passed: $PASSED / $TOTAL"
if [[ "$FAILED" -gt 0 ]]; then
    echo "Failed: $FAILED / $TOTAL"
    echo ""
    echo "Failed tasks:"
    awk -F'\t' 'NR > 1 && $4 != "ok" {print "  " $1 " (exit=" $5 ")"}' "$SUMMARY_TSV"
fi
echo ""
if [[ "$PARALLEL_EXIT" -ne 0 ]]; then
    echo "GNU parallel exit code: $PARALLEL_EXIT"
    echo ""
fi

if command -v column &>/dev/null; then
    column -ts $'\t' "$SUMMARY_TSV"
else
    cat "$SUMMARY_TSV"
fi

echo ""
echo "Logs:        $LOG_DIR/"
echo "Job log:     $JOBLOG"
echo "Summary TSV: $SUMMARY_TSV"
