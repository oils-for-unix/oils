#!/usr/bin/env bash
#
# Temporarily publish test results under versioned directories.
#
# Usage:
#   ./publish.sh <function name>
#
# Use cases:
# - Blogging
# - Shared debugging
# - Running tests on machines without a web server.
#
# Releases publish HTML the oilshell.org__deploy repo, but here we publish
# directly to web servers.

set -o nounset
set -o pipefail
set -o errexit

log() {
  echo "$@" 1>&2
}

current-branch-name() {
  git rev-parse --abbrev-ref HEAD
}

versioned-dest() {
  local branch=$(current-branch-name)
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

  local dest
  # Add hostname because spec tests aren't hermetic yet.
  #dest="$(versioned-dest)/$(hostname)/spec"
  dest="$(versioned-dest)/spec"

  ssh $user@$host mkdir -p $dest

  # rsync is faster than scp and has the --no-target-directory behavior.
  # We need --copy-links because the CSS files are symlinks.
  rsync --archive --verbose --copy-links \
    _tmp/spec/ $user@$host:$dest/

  echo "Visit http://$dest/"
}

# Publish unit tests
unit() {
  echo 'Hello from publish.sh'
}

compress-wild() {
  local out="$PWD/_tmp/wild/wild.wwz"
  pushd _tmp/wild/www
  time zip -r -q $out .  # recursive, quiet
  ls -l $out
}

# NOTE: Have to copy the web/ dir too?  For testing, use ./local.sh
# test-release-tree.
wild() {
  local user=$1
  local host=${2:-${user}.org}  # default host looks like the name

  local dest
  dest="$(versioned-dest)"  # no wild/ suffix, since it's wild.wwz/

  ssh $user@$host mkdir -p $dest

  rsync --archive --verbose \
    _tmp/wild/wild.wwz $user@$host:$dest/

  echo "Visit http://$dest/wild.wwz/"
}

# Publish static assets needed for the wild HTML pages.
web-dir() {
  local user=$1
  local host=${2:-${user}.org}  # default host looks like the name
  local branch=${3:-$(current-branch-name)}
  local dest=$user@$host:oilshell.org/git-branch/$branch/web/

  # This is made by copy-web in scripts/release.sh.  Reuse it here.
  rsync --archive --verbose \
    _release/VERSION/web/ $dest 

  echo "Published to $dest"
}

"$@"
