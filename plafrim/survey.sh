set -eo pipefail

# Go to the flatsurvey root directory.
cd "$(dirname "$0")"/..

SCHEDULER=/beegfs/jrueth/scheduler.$1.json

# Spawn a survey reading previous cached results from orbit-closure.json and writing (new) results to beegfs
mkdir -p /beegfs/jrueth/flatsurvey/history
touch /beegfs/jrueth/flatsurvey/history/$1/orbit-closure.json
salloc --ntasks=1 --time=72:00:00 srun --pty pixi run flatsurvey --mem-limit=conservative --time-limit=1h --scheduler=$SCHEDULER $2 local-cache --json /beegfs/jrueth/flatsurvey/history/$1/orbit-closure.json orbit-closure json --prefix=/beegfs/jrueth/flatsurvey/$1/
