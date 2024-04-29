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
  base64 -d <<'XSHAR_DATA' | tar -x -z
EOF

  # Print code that extracts here doc
  base64 < $tar 

  cat <<EOF
XSHAR_DATA
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
  echo
}

create-hello() {
  find yaks/ -name '*.py' | xargs -- $0 create devtools/hello-xshar.sh 
  ls -l -h _release
}

test-oils-manifest() {
  echo '_release/oils-for-unix.tar'

  echo 'oil-version.txt'

  # TODO: need osh --tool shell-deps for these

  echo 'devtools/release-native.sh'
  echo 'benchmarks/time_.py'
  echo 'benchmarks/time-helper.c'

  # extracted tarball
  #find _deps/osh-runtime/util-linux-2.40

  # we could include Python-2.7.13 too
}

create-test-oils() {
  devtools/release-native.sh make-tar

  test-oils-manifest | xargs -- $0 create devtools/test-oils.sh 
  ls -l -h _release
}

soil-run-hello() {
  create-hello
  _release/hello-xshar.xshar main a b c
}

soil-run-test-oils() {
  create-test-oils

  # Run it twice to test that SKIP_REBUILD works
  for x in 1 2; do
    XSHAR_DIR=/tmp/test-oils.xshar.REUSED _release/test-oils.xshar demo a b c
  done
}

run-task "$@"
