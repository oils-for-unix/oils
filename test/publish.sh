#!/usr/bin/env bash
#
# Usage:
#   ./publish.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

log() {
  echo "$@" 1>&2
}

versioned-dest() {
  local branch=$(git rev-parse --abbrev-ref HEAD)
  log "branch $branch"
  local hash=$(git rev-parse $branch)
  local short_hash=${hash:0:8}
  log "hash $short_hash"

  local dest="oilshell.org/git-branch/$branch/$short_hash"
  echo $dest
}

spec() {
  local user=$1
  local host=$2

  # Add hostname because spec tests aren't hermetic yet.
  local dest
  dest="$(versioned-dest)/$(hostname)/spec"

  ssh $user@$host mkdir -p $dest

  # rsync is faster than scp and has the --no-target-directory behavior.
  # We need --copy-links because the CSS files are symlinks.
  rsync --archive --verbose --copy-links \
    _tmp/spec/ $user@$host:$dest/

  echo "Visit http://$dest/RESULTS.html"
}

# TODO: These should really go to the oilshell.org__deploy repo.

# Publish unit tests
unit() {
  echo 'Hello from publish.sh'
}

# NOTE: Have to copy the web/ dir too?  For testing, use ./local.sh
# test-release-tree.
wild() {
  local user=$1
  local host=$2

  local dest
  dest="$(versioned-dest)"  # no wild/ suffix, since it's wild.wwz/

  ssh $user@$host mkdir -p $dest

  rsync --archive --verbose \
    _release/VERSION/test/wild.wwz $user@$host:$dest/

  echo "Visit http://$dest/wild.wwz/"
}

"$@"
