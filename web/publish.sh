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
  ### Publish spec tests to a versioned directory on a web server

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

web-dir() {
  local user=$1
  local dest=$2

  # This is made by copy-web in devtools/release.sh.  Reuse it here.
  rsync --archive --verbose \
    _release/VERSION/web/ $dest 

  echo "Published to $dest"
}

web-dir-versioned() {
  ### Publish static assets needed for the wild HTML pages.
  local user=$1
  local host=$user.org

  local branch=$(current-branch-name)
  local dest=$user@$host:oilshell.org/git-branch/$branch/web/
  web-dir $user $dest
}

web-dir-preview() {
  ### Publish static assets needed for the wild HTML pages.
  local user=$1
  local host=$user.org

  local dest='oilshell.org/preview/web'
  ssh $user@$host mkdir --verbose -p $dest
  local dest=$user@$host:$dest
  web-dir $user $dest
}

preview() {
  ### Publish a file (e.g. _release/VERSION/doc/json.html) to 
  ### oilshell.org/git-branch/...
  local user=$1
  local host=$user.org

  local path=$2

  local dest='oilshell.org/preview/doc'
  ssh $user@$host mkdir --verbose -p $dest
  scp $path $user@$host:$dest
}

file-to-share() {
  local user=$1
  local host=$user.org

  local file=$2
  local dest_suffix=${3:-}  # e.g. .txt

  local dest=$user@$host:oilshell.org/share/$(basename $file)$dest_suffix

  scp $file $dest
}

"$@"
