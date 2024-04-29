#!/usr/bin/env bash
#
# xshar - Executable shell archive
#
# Usage:
#   devtools/xshar.sh <function name>
#
# devtools/
#   xshar.sh  # this file
#   test-oils.sh  # can run benchmarks
#
# Results in:
#
#   _release/test-oils.xshar
#
# Runtime deps:
#
#   /bin/sh
#   tar, gzip -d
#   base64

set -o nounset
set -o pipefail
set -o errexit

source devtools/run-task.sh  # run-task

print-shell() {
  local tar=$1
  local main=$2

  # Same as soil/worker.sh
  local git_commit
  git_commit=$(git log -n 1 --pretty='format:%H')

  sed "s/__GIT_COMMIT__/$git_commit/" <<'EOF'
#!/bin/sh

export XSHAR_REPO=oilshell/oil
export XSHAR_GIT_COMMIT=__GIT_COMMIT__

name=$(basename $0)  # e.g. hello-xshar.xshar
default_dir=/tmp/$name.$$

# User can override this, and then _build/oils.sh can use SKIP_REBUILD to make
# it faster.  Multiple runs without compiling.

export XSHAR_DIR=${XSHAR_DIR:-$default_dir}

change_dir() {
  mkdir -p "$XSHAR_DIR"
  cd "$XSHAR_DIR"
}

extract_data() {
  base64 -d >tmp.tar.gz <<'XSHAR_DATA'
EOF

  # Print code that extracts here doc
  base64 < $tar 

  cat <<EOF
XSHAR_DATA

  tar -x -z < tmp.tar.gz
}

change_dir
extract_data
EOF
  echo "$main" '"$@"'

  # We don't bother to clean up after, it's in /tmp
}

create() {
  local main=${1:-devtools/test-oils.sh}
  # Include the main file
  #shift

  local name
  name=$(basename $main .sh)

  local tar=_tmp/$name.tar.gz

  tar --create --gzip --file $tar "$main" "$@"
  ls -l $tar

  local out=_release/$name.xshar 

  print-shell $tar $main > $out
  chmod +x $out
  ls -l $out
}

create-hello() {
  find yaks/ -name '*.py' | xargs -- $0 create devtools/hello-xshar.sh 
  ls -l _release
}

soil-run-hello() {
  create-hello
  _release/hello-xshar.xshar main a b c
}

soil-run-test-oils() {
  echo TODO
}

run-task "$@"
