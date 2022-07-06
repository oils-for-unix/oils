#!/usr/bin/env bash
#
# Usage:
#   ./NINJA-config.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/app-deps.sh

main() {

  # Generate implicit and explicit dependencies
  ninja-config

  ./NINJA_config.py
}

main "$@"
