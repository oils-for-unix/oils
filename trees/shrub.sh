#!/usr/bin/env bash
#
# Usage:
#   trees/shrub.sh <function name>

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

    sync)
      local shrub_dir=${2:-''}
      local dest=${3:-'.'}

      if test -z "$shrub_dir"; then
        die "$0: sync SHRUB_DIR DEST"
      fi

      # Each vref should be sync'd
      # It can have "blobsum" or "treesum", but at first we only support "blobsum"
      # And then we look that up

      find $shrub_dir -name '*.vref' | xargs echo TODO

      # Make the 00/ object dirs on demand
      ;;

    add-dir)
      # Makes a vref and tarball that you can scp/rsync
      local dir=${2:-''}
      local vref=${3:-}

      if test -z "$dir"; then
        die "$0: add-dir DIR VREF"
      fi

      ;;

    verify)
      local dir=${2:-'.'}
      local dest=${3:-}

      echo 'TODO: checksum all files'
      ;;

    reachable)
      local shrub_dir=${2:-'.'}

      if test -z "$shrub_dir"; then
        die "$0: reachable SHRUB_DIR"
      fi

      # TODO: print a list of vblob IDs that are reachable to stdout.  Then you
      # can:
      #
      # - Check if they exist on the remote vat
      # - Copy them to a new vat
      # - You can also walk the git history, etc.

      find $shrub_dir -name '*.vref' | xargs echo TODO

      ;;

    *)
      die "Invalid action '$action'"
      ;;

  esac
}

main "$@"
