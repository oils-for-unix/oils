#!/usr/bin/env bash
#
# Survey code: toward a common test/benchmark framework.
#
# Usage:
#   test/all.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

grep-time-tool() {

  # Current users:
  #   benchmarks/
  #     gc,osh-runtime,ovm-build
  #   build/
  #     ninja-rules-py.sh  # for mycpp-logs-equal
  #   soil/
  #     worker.sh
  #   test/
  #     stateful,unit

  egrep --color -n 'time-tsv' */*.sh

  echo

  # benchmarks/
  #   osh-parser/
  egrep --color -n 'benchmarks/time_.py' */*.sh

  echo

  # benchmarks/ovm-build has more for time-tsv
  egrep --color -n 'TIME_PREFIX' */*.sh
}

grep-print-tasks() {

  # Current users:
  #   benchmarks/
  #    gc,osh-parser,osh-runtime,uftrace,vm-baseline
  #
  # Should use it:
  #   benchmarks/
  #     compute/
  #   test/
  #     stateful/
  #     wild.sh  # has 'all' function

  # Using Python programs:
  #  spec/*  uses sh_spec.py
  #  spec/stateful/{signals,job_control,...}.py

  egrep --color -n 'print-tasks' */*.sh
}

grep-soil-run() {
  # It would be nice to make these more fine-grained

  egrep --color -n '^soil-run' */*.sh

  echo

  egrep --color -n '^run-for-release' */*.sh
}

all-print-tasks() {
  # All benchmarks and tests should use this style!
  #
  # Then we can time, status, stdout / output files consistentely.

  # Only prints a single column now!
  benchmarks/uftrace.sh print-tasks

  echo

  # Modern style
  benchmarks/gc.sh print-tasks

  echo

  # Modern style of benchmark
  benchmarks/osh-runtime.sh print-tasks 'no-host' '_bin/cxx-dbg/osh'

  return

  # requires provenance
  benchmarks/osh-parser.sh print-tasks
}

"$@"
