#!/usr/bin/env bash
#
# Usage:
#   trees/vat.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

die() {
  echo "$@" >&2
  exit 1
}

main() {
  local action=${1:-}

  case $action in

    init)
      local dir=${2:-'.'}

      # Set up repo structure
      mkdir -v -p $dir/{primary,cache}

      # Make the 00 objects on demand
      ;;

    verify)
      local dir=${2:-'.'}

      # TODO: decompress and checksum file?
      #
      # Note that git-hash-object takes -t blob, and that --literally bypasses
      # the check
      find primary -name '*.blob.gz' | xargs echo TODO
      ;;

    *)
      die "Invalid action '$action'"
      ;;

  esac
}

main "$@"
