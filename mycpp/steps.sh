#!/usr/bin/env bash
#
# Build steps invoked by Ninja.
#
# Usage:
#   ./steps.sh <function name>
#
# Naming Convention:
#
#   ./configure.py - generates build.ninja
#   build.ninja
#   ninja.sh - wrapper for 'clean' and 'all'.  Invokes Ninja.
#   steps.sh - invoked BY ninja.
#   _ninja/ - tree
#
# TODO: build/actions.sh should be renamed build/steps.sh?  "actions" implies a
# side effect, where as "steps" largely know their outputs an outputs largely

set -o nounset
set -o pipefail
set -o errexit

source common.sh

# TODO: Move ninja-{translate,compile} here

task() {
  local bin=$1  # Run this
  local task_out=$2
  local log_out=$3

  case $bin in
    _ninja/bin/*.asan)
      # copied from run.sh and build/mycpp.sh
      export ASAN_OPTIONS='detect_leaks=0'
      ;;

    examples/*.py)
      # for running most examples
      export PYTHONPATH=".:$REPO_ROOT/vendor"
      ;;
  esac

  case $task_out in
    _ninja/tasks/benchmark/*)
      export BENCHMARK=1
      ;;
  esac

  time-tsv -o $task_out --rusage --field $bin --field $task_out -- $bin >$log_out 2>&1
}

"$@"
