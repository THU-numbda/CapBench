#!/usr/bin/env bash
# CapBench environment setup for NGC PyTorch containers (26.02+).
#
# Usage (inside the container):
#   source scripts/setup_env.sh          # just set PYTHONPATH
#   source scripts/setup_env.sh install  # install missing deps + set PYTHONPATH
#
# Tensorboard:
#   Launch the container with network access to use tensorboard:
#     singularity exec --nv pytorch_26.02-py3.sif bash
#     source scripts/setup_env.sh
#     tensorboard --logdir runs --bind_all --port 6006
#
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# If the default python3 doesn't have torch but /usr/bin/python3 does,
# the host miniconda is shadowing the container's Python. Fix PATH so
# the container's system Python takes priority.
if ! python3 -c "import torch" 2>/dev/null; then
    if /usr/bin/python3 -c "import torch" 2>/dev/null; then
        echo "Fixing PATH: container Python shadowed by host miniconda"
        export PATH="/usr/bin:${PATH}"
    fi
fi

export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
export CAPBENCH_CACHE_DIR="${CAPBENCH_CACHE_DIR:-${HOME}/.cache/capbench}"

if [[ "${1:-}" == "install" ]]; then
    echo "Installing CapBench dependencies into ~/.local ..."

    # Packages the NGC PyTorch container already ships:
    #   numpy, scipy, tensorboard, tqdm, matplotlib, pyyaml,
    #   onnx, onnxruntime, jupyter, pandas, scikit-learn

    # Detect PyTorch and CUDA versions
    TORCH_VER="$(python3 -c "import torch; print(torch.__version__.split('+')[0])" 2>/dev/null)" || true
    CUDA_VER="$(python3 -c "import torch; print('cu' + torch.version.cuda.replace('.', ''))" 2>/dev/null)" || true

    if [[ -z "${TORCH_VER}" || -z "${CUDA_VER}" ]]; then
        echo "ERROR: Could not detect PyTorch/CUDA. Are you inside the NGC container?"
        echo "  singularity exec --nv pytorch_26.02-py3.sif bash"
        return 1 2>/dev/null || exit 1
    fi

    echo "PyTorch ${TORCH_VER}, CUDA ${CUDA_VER}"
    echo "Installing CapBench in editable mode with optional extras ..."
    (
        cd "$REPO_ROOT" && \
        pip install --user --quiet -e ".[all]"
    ) 2>&1 | tail -1

    mkdir -p "${HOME}/.local/bin" "${HOME}/.parallel"
    if ! command -v parallel >/dev/null 2>&1; then
        echo "Installing GNU parallel into ~/.local/bin ..."
        curl -L https://git.savannah.gnu.org/cgit/parallel.git/plain/src/parallel \
            -o "${HOME}/.local/bin/parallel"
        chmod +x "${HOME}/.local/bin/parallel"
    fi
    touch "${HOME}/.parallel/will-cite"

    echo "Done. Packages installed to $(python3 -m site --user-site)"
fi

echo "CAPBENCH_CACHE_DIR=${CAPBENCH_CACHE_DIR}"
echo "PYTHONPATH=${PYTHONPATH}"
