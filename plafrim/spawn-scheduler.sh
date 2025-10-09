set -eo pipefail

# Go to the flatsurvey root directory.
cd "$(dirname "$0")"/..

SCHEDULER="/beegfs/jrueth/scheduler.$1.json"

# Start a scheduler on a random port.
salloc --ntasks=1 --time=72:00:00 srun --pty pixi run dask-scheduler --scheduler-file=$SCHEDULER --port=`shuf -i 32768-60999 -n 1`
