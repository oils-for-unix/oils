#!/usr/bin/env bash
#
# Build stamp
#
# Usage:
#   build/stamp.sh <function name>

REPO_ROOT=$(cd $(dirname $0)/..; pwd)
source build/common.sh

write-release-date() {
  mkdir -p _build  # Makefile makes this, but scripts/release.sh needs it too

  # Write a readable, sortable date that is independent of time zone.
  date --utc --rfc-3339 seconds > _build/release-date.txt
}

write-git-commit() {
  ### Write git commit only if we need to
  # Ninja works on timestamps, so we don't want to cause rebuilds.

  local out=_build/git-commit.txt
  mkdir -p _build

  # This check is not quite accurate, since you can modify a file, and then run
  # Ninja without running build/py.sh all, which calls this function.  But it's
  # better than nothing.
  if ! git diff --quiet; then
    log 'Working tree is dirty'

    #rm -f -v $out
    echo '<unknown>' > $out
    return
  fi

  local hash
  hash=$(git log -n 1 --pretty='format:%H')

  # Don't disturb the timestamp if it exists!
  if test -f $out; then
    local old
    read -r old < $out

    if test "$old" = "$hash"; then
      log "Unchanged git commit $hash, skipping $out"
      return
    else
      log "Overwriting $out with $hash"
    fi
  fi

  echo $hash > $out
  #log "Wrote $out ($hash)"
}

gen-cpp() {
  ### For printing out in --version

  local in=$1   # stamp from Ninja
  local h_out=$2
  local cc_out=$3

  local hash
  read -r hash < $in
  #log hash=$hash

  cat >$h_out <<EOF
extern const char* gCommitHash;
EOF

  cat >$cc_out <<EOF
const char* gCommitHash = "$hash";
EOF
}

"$@"
