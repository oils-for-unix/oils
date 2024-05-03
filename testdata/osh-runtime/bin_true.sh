#!/usr/bin/env bash
#
# Synthetic shell benchmarks
#
# Usage:
#   testdata/osh-runtime/bin_true.sh <function name>

# Run under:
# - benchmarks/uftrace to trace allocations
# - benchmarks/osh-runtime for wall time and GC stats

# make sure we can run under dash

#set -o nounset
#set -o pipefail
#set -o errexit

main() {
  local n=${1:-1000}

  echo "Running /bin/true $n times"

  local i=0
  while test $i -lt $n; do
    /bin/true
    i=$(( i + 1 ))
  done

  echo 'Done'
}

# Other tests we can do:
# - Subshell
# - Pipeline

main "$@"
