#!/usr/bin/env bash
#
# Usage:
#   ./publish.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

spec() {
  local user=$1
  local host=$2
  local label=${3:-$(hostname)}  # what machine we ran it on

  local branch=$(git rev-parse --abbrev-ref HEAD)
  echo $branch
  local hash=$(git rev-parse $branch)
  local short_hash=${hash:0:8}
  echo $short_hash

  local dest=oilshell.org/git-branch/$branch/$short_hash/$label/spec
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
wild() {
  echo 'Hello from publish.sh'
}

"$@"
