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

print-help() {
  # Other flags:
  #
  # --host       host to upload to?
  # --auth       allow writing to host
  # --no-taskset disable taskset?

  local xshar_path=test-oils.xshar  # hard-coded for now

  cat <<EOF
Usage: $xshar_path ACTION FLAGS*

Actions:

  osh-runtime (only one supported)

  Flags:
    -n --num-iters (default: 1)  Run everything this number of times.

    -s --num-shells              Run the first N of osh, bash, dash

    -w --num-workloads           Run the first N of the workloads

  Workloads:
EOF
  benchmarks/osh-runtime.sh print-workloads
  cat <<EOF

Example:

  $xshar_path osh-runtime --num-iters 2 --num-shells 2 --num-workloads 3

will run this benchmark matrix 2 times:

  (osh, bash) X (hello-world, bin-true, configure-cpython)

About xshar:

  This is a self-extracting executable.  It contains:

  1. The oils-for-unix tarball, which can be compiled on any machine easily
  2. Benchmarking scripts
  3. This harness, which compiles the tarball, accepts flags, runs benchmarks.

EOF
}

print-version() {
  echo "$0 was built from git commit ${XSHAR_GIT_COMMIT:-?}"
}

parse-flags-osh-runtime() {
  ### Sets global vars FLAG_*

  while test $# -ne 0; do
    case "$1" in
      -v|--version)
        print-version
        exit
        ;;
      -h|--help)
        print-help
        exit
        ;;

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
  ### Show how we compile the code

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

if test $# -eq 0; then
  print-help
else
  case "$1" in
    -v|--version)
      print-version
      exit
      ;;
    -h|--help)
      print-help
      exit
      ;;
  esac

  "$@"
fi
