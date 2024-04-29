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
