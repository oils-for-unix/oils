#!/usr/bin/env bash
#
# Synthetic test with 1000 regexes.
#
# Usage:
#   benchmarks/regcomp-cache/run.sh <function name>
#
# Example:
#   benchmarks/regcomp-cache/run.sh match-many

set -o nounset
set -o pipefail
set -o errexit

match-many() {
  local num_pat=${1:-300}
  local num_str=${1:-300}

  echo BASH_VERSION=${BASH_VERSION:-}
  echo OILS_VERSION=${OILS_VERSION:-}

  declare -a REGEXES=()
  for i in $(seq $num_pat); do
    REGEXES[i]="$i?($i*)$i+"  # last char is modified with ? then * and +
  done

  echo "${REGEXES[@]}"

  local num_yes=0
  local num_tried=0

  for i in $(seq $num_str); do
    local str="$i$i$i"  # 3 copies
    for j in $(seq $num_pat); do
      local re="${REGEXES[j]}"
      if [[ $str =~ $re ]]; then
        echo "string $str matches pattern $re - captured '${BASH_REMATCH[1]}'"
        num_yes=$(( num_yes + 1 ))
      fi
      num_tried=$(( num_tried + 1 ))
    done
  done

  echo
  echo "num_yes = $num_yes"
  echo "num_tried = $num_tried"
}

compare() {
  # must do ./NINJA-config.sh first

  local bin=_bin/cxx-opt/osh
  ninja $bin

  local dir=_tmp/regcomp-cache
  mkdir -p $dir

  # with bash
  { time $0 match-many; } >$dir/bash-stdout.txt 2>$dir/bash-time.txt

  # with OSH
  { time $bin $0 match-many; } >$dir/osh-stdout.txt 2>$dir/osh-time.txt

  diff -u $dir/*-stdout.txt  # should have equal output
  head $dir/*-time.txt  # show timings
}


"$@"

