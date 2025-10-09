set -eo pipefail

# Go to the flatsurvey root directory.
cd "$(dirname "$0")"/..

pixi install --locked

pixi run python -c 'import cppyy'
