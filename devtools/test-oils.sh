#!/usr/bin/env bash
#
# Main file for test-oils.xshar
#
# Usage:
#   devtools/test-oils.sh <function name>
#
# It will contain
# 
# _release/
#   oils-for-unix.tar
# benchmarks/
#   time-helper.c
#   osh-runtime.sh
#
# It will run benchmarks, and then upload a TSV file to a server.
#
# The TSV file will be labeled with
#
# - git commit that created the xshar file (in oilshell/oil)
# - date
# - label: github actions / sourcehut
# - and then we'll also have provenance and system info
#   - machine name, OS, CPUs, etc.

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # die

OILS_VERSION=$(head -n 1 oil-version.txt)

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

FLAG_num_iters=1  # iterations
FLAG_num_shells=1
FLAG_num_workloads=1

parse-flags-osh-runtime() {
  ### Sets global vars FLAG_*

  while test $# -ne 0; do
    case "$1" in
      -n|--num-iters)
        if test $# -eq 1; then
          die "-n / --num-iters requires an argument"
        fi
        shift
        FLAG_num_iters=$1
        ;;

      -s|--num-shells)
        if test $# -eq 1; then
          die "-s / --num-shells requires an argument"
        fi
        shift
        FLAG_num_shells=$1
        ;;

      -w|--num-workloads)
        if test $# -eq 1; then
          die "-w / --num-workloads requires an argument"
        fi
        shift
        FLAG_num_shells=$1
        ;;

      *)
        die "Invalid flag '$1'"
        ;;
    esac
    shift
  done
}

osh-runtime() {
  # $XSHAR_DIR looks like like $REPO_ROOT

  parse-flags-osh-runtime "$@"
  echo num_iters=$FLAG_num_iters
  echo num_shells=$FLAG_num_shells
  echo num_workloads=$FLAG_num_workloads

  local time_py="${XSHAR_DIR:-$REPO_ROOT}/benchmarks/time_.py"
  build/py.sh time-helper

  # Extract and compile the tarball
  # Similar to devtools/release-native.sh test-tar
  local tmp=_tmp/oils-tar
  mkdir -p $tmp

  pushd $tmp
  tar -x < ../../_release/oils-for-unix.tar

  pushd oils-for-unix-$OILS_VERSION
  build/native.sh tarball-demo

  local osh=$PWD/_bin/cxx-opt-sh/osh 

  # Smoke test
  $time_py --tsv --rusage -- \
    $osh -c 'echo "smoke test: osh and time_.py"'

  popd
  popd

  benchmarks/osh-runtime.sh test-oils-run $osh \
    $FLAG_num_shells $FLAG_num_workloads $FLAG_num_iters
}

demo() {
  local time_py="$PWD/benchmarks/time_.py"

  build/py.sh time-helper

  # Extract and compile the tarball
  # Similar to devtools/release-native.sh test-tar

  local tmp=_tmp/xshar-demo
  mkdir -p $tmp

  pushd $tmp
  tar -x < ../../_release/oils-for-unix.tar

  pushd oils-for-unix-$OILS_VERSION
  build/native.sh tarball-demo

  local osh=$PWD/_bin/cxx-opt-sh/osh 

  $time_py --tsv --rusage -o demo.tsv -- \
    $osh -c 'sleep 0.1; echo "hi from osh"'
  cat demo.tsv

  popd

  popd

  #time OILS_GC_STATS=1 $osh Python-2.7.13/configure
}

main() {
  # TODO
  #
  # - Extract oils tarball, compile it
  # - Run "$@"
  #
  # test-oils.xshar benchmarks/osh-runtime.sh xshar-main
  #
  # - benchmarks/osh-runtime.sh will create TSV files
  # - then it can upload them to a server

  echo 'Hello from test-oils.sh'
}

"$@"
