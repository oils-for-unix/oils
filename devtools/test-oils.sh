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

osh-runtime() {
  # Extract and compile the tarball
  devtools/release-native.sh test-tar
  # TODO: compile time-helper.c

  # TODO: call benchmarks/osh-runtime to measure
  #
  # Upload TSV files
  # Where?
}

demo() {
  local oils_version
  oils_version=$(head -n 1 oil-version.txt)

  local time_py="$PWD/benchmarks/time_.py"

  build/py.sh time-helper

  # Extract and compile the tarball
  # Similar to devtools/release-native.sh test-tar

  local tmp=_tmp/xshar-demo
  mkdir -p $tmp

  pushd $tmp
  tar -x < ../../_release/oils-for-unix.tar

  pushd oils-for-unix-$oils_version
  build/native.sh tarball-demo

  # TODO: use benchmarks/time_.py
  # TODO: compile time-helper.c

  local osh=$PWD/_bin/cxx-opt-sh/osh 

  $time_py --tsv --rusage -o demo.tsv -- $osh -c 'sleep 0.1; echo "hi from osh"'
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
