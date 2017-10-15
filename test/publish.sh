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
  local label=${1:-$(hostname)}  # what machine we ran it on

  local branch=$(git rev-parse --abbrev-ref HEAD)
  log "branch $branch"
  local hash=$(git rev-parse $branch)
  local short_hash=${hash:0:8}
  log "hash $short_hash"

  local dest="oilshell.org/git-branch/$branch/$short_hash/$label"
  echo $dest
}

spec() {
  local user=$1
  local host=$2

  local dest
  dest="$(versioned-dest)/spec"

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

# Wild Tests.  NOTE: There's code for this in the oilshell.org repo.
compress-wild() {
  local dest=_tmp/wild-deploy
  mkdir -p $dest

  local out=$PWD/$dest/wild.wwz  # abs path for zip
  rm -f -v $out

  pushd _tmp/wild/www
  time zip -r -q $out .  # recursive, quiet
  popd

  test/wild-runner.sh link-static $dest
  ls -l -h $dest
}

wild() {
  local user=$1
  local host=$2

  local dest
  dest="$(versioned-dest)"  # no wild/ suffix, since it's wild.wwz/

  ssh $user@$host mkdir -p $dest

  rsync --archive --verbose --copy-links \
    _tmp/wild-deploy/ $user@$host:$dest/

  echo "Visit http://$dest/wild.wwz/"
}

"$@"
