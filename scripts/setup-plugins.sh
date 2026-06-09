#!/bin/sh
# Creates symlinks in the pixi environment bin/ directory so nxrunner
# (SIMPLNX 1.7.0) can discover the .simplnx plugin shared libraries.
# nxrunner hardcodes its plugin search path to dirname(argv[0]) == bin/,
# but the conda dream3dnx package installs plugins to lib/.
#
# Usage: bash scripts/setup-plugins.sh [env_dir]
#   env_dir defaults to the directory containing nxrunner (usually the current conda environment)

set -eu

nxpath=$(which nxrunner)
nxenv=$(cd -- "${nxpath%/bin/nxrunner}" && pwd)

ENV_DIR="${1:-$nxenv}"

echo "Linking .simplnx plugins from $ENV_DIR/lib"
find "$ENV_DIR/lib" -maxdepth 1 -type f -name "*.simplnx" | while IFS= read -r f; do
  target="$ENV_DIR/bin/$(basename "$f")"
  if [ ! -L "$target" ]; then
    ln -sf "../lib/$(basename "$f")" "$target"
    echo "Created: $target"
  fi
done
