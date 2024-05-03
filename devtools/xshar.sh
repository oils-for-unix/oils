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
  local manifest=$2
  #shift

  local name
  name=$(basename $main .sh)

  local tar=_tmp/$name.tar.gz

  # Need --files-from because we can run out of ARGV!

  tar --create --gzip --files-from $manifest --file $tar "$main"
  ls -l $tar

  local out=_release/$name.xshar 

  print-shell $tar $main > $out
  chmod +x $out
  ls -l $out
  echo
}

create-hello() {
  local tmp=_tmp/hello-manifest.txt
  find yaks/ -name '*.py' > $tmp
  create devtools/hello-xshar.sh $tmp

  ls -l -h _release
}

test-oils-manifest() {
  echo '_release/oils-for-unix.tar'

  echo 'oil-version.txt'

  echo 'benchmarks/time_.py'
  echo 'benchmarks/time-helper.c'

  # TODO: implement shell-deps tool
  #
  # osh --tool shell-deps build/py.sh
  echo 'build/dev-shell.sh'
  echo 'build/py.sh'
  echo 'build/common.sh'
  echo 'devtools/run-task.sh'

  # osh --tool shell-deps benchmarks/osh-runtime.sh
  # copied from benchmarks/osh-runtime.sh
  cat <<'EOF'
benchmarks/osh-runtime.sh
benchmarks/common.sh
benchmarks/id.sh
soil/common.sh
test/common.sh
test/tsv-lib.sh
EOF
  echo 'benchmarks/gc_stats_to_tsv.py'
  echo 'devtools/tsv_concat.py'

  find testdata/osh-runtime

  find Python-2.7.13/
}

create-test-oils() {
  devtools/release-native.sh make-tar

  local tmp=_tmp/test-oils-manifest.txt
  test-oils-manifest > $tmp
  create devtools/test-oils.sh $tmp
  ls -l -h _release
}

soil-run-hello() {
  create-hello
  _release/hello-xshar.xshar main a b c
}

soil-run-test-oils() {
  create-test-oils

  # Demo of flag parsing
  XSHAR_DIR=/tmp/test-oils.xshar.REUSED _release/test-oils.xshar osh-runtime \
    --num-iters 1 --num-shells 1 --num-workloads 1

  # Run it twice to test that SKIP_REBUILD works
  XSHAR_DIR=/tmp/test-oils.xshar.REUSED _release/test-oils.xshar --help
  XSHAR_DIR=/tmp/test-oils.xshar.REUSED _release/test-oils.xshar --version
}

run-task "$@"
