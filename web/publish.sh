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
# Releases publish HTML the oils.pub__deploy repo, but here we publish
# directly to web servers.

set -o nounset
set -o pipefail
set -o errexit

readonly HOST='oilshell.org'

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

share-dir-versioned() {
  local dir=$1
  local user=$2
  local host=oilshell.org

  local dest
  dest="$(versioned-dest)/$(basename $dir)"

  ssh $user@$host mkdir -p $dest

  # rsync is faster than scp and has the --no-target-directory behavior.
  # We need --copy-links because the CSS files are symlinks.
  rsync --archive --verbose --copy-links \
    "$dir/" "$user@$host:$dest/"

  echo "Visit http://$dest/"
}

spec() {
  ### Publish spec tests to a versioned directory on a web server

  local user=$1
  share-dir-versioned _tmp/spec $user
}

benchmarks-perf() {
  ### Identical to above, except for the directory

  local user=$1
  share-dir-versioned _tmp/perf $user
}

benchmark() {
  ### Publish benchmarks to a versioned dir

  local user=$1
  local benchmark=${2:-osh-parser}

  local dest
  # Add hostname because spec tests aren't hermetic yet.
  #dest="$(versioned-dest)/$(hostname)/spec"
  dest="$(versioned-dest)/$benchmark"

  echo $dest

  ssh $user@$HOST mkdir -p $dest

  scp _tmp/$benchmark/index.html $user@$HOST:$dest/

  echo "Visit http://$dest/"
}

compress-wild() {
  local out="$PWD/_tmp/wild/wild.wwz"
  pushd _tmp/wild-www
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
  ### Publish static assets needed for the wild HTML pages (versioned)
  local user=$1
  local host=oilshell.org

  local branch=$(current-branch-name)
  local dir=oilshell.org/git-branch/$branch/web/

  local dest=$user@$host:$dir

  ssh $user@$host mkdir --verbose -p $dir
  web-dir $user $dest
}

web-dir-preview() {
  ### Publish static assets needed for the wild HTML pages.
  local user=$1
  local host=oilshell.org

  local dir='oilshell.org/preview/web'

  ssh $user@$host mkdir --verbose -p $dir

  local dest=$user@$host:$dir
  web-dir $user $dest
}

doc-preview() {
  ### Publish a file (e.g. _release/VERSION/doc/json.html) to 
  local user=$1
  local host=oilshell.org

  local path=$2
  local dest=${3:-'oilshell.org/preview/doc'}

  ssh $user@$host mkdir --verbose -p $dest
  scp $path $user@$host:$dest
}

mycpp-benchmarks() {
  doc-preview $1 _tmp/mycpp-benchmarks/index.html oilshell.org/preview/benchmarks/mycpp
}

shell-vs-shell() {
  doc-preview $1 _tmp/shell-vs-shell/index.html oilshell.org/preview/shell-vs-shell
}

file-to-share() {
  local user=$1
  local host=oilshell.org

  local file=$2
  local dest_suffix=${3:-}  # e.g. .txt

  local dest=$user@$host:oilshell.org/share/$(basename $file)$dest_suffix

  scp $file $dest
}

"$@"
