set -eo pipefail

# Go to the flatsurvey root directory.
cd "$(dirname "$0")"/..

SCHEDULER=/beegfs/jrueth/scheduler.$1.json

echo "Connecting worker from `hostname` to scheduler $SCHEDULER"

MKL_NUM_THREADS=1 SAGE_NUM_THREADS=1 OMP_NUM_THREADS=1 DOT_SAGE=/tmp/sage.jrueth$1 pixi run dask worker --scheduler-file $SCHEDULER --nthreads 1 --nworkers 1 --no-nanny --preload flatsurvey.dask.worker --memory-limit=128G
