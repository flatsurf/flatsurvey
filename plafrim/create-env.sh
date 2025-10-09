set -eo pipefail

# To install pixi, ssh -R 3333 and set https_proxy=socks5://localhost:3333.
# Then install pixi as usual. The conda-forge repositories are not blocked by
# PlaFRIM, only the installation scripts are, so reconnect without this hack.

# Go to the flatsurvey root directory.
cd "$(dirname "$0")"/..

# We install the pixi environment into a fast local directory.
DETACHED_ENVIRONMENTS=/tmp/jrueth/pixi

mkdir -p .pixi
cat <<EOF > .pixi/config.toml
detached-environments = "$DETACHED_ENVIRONMENTS"
EOF

# We cannot install our environment on the devel machines since the ulimit is
# set to 300 processes which is not enough for a functional pixi.
