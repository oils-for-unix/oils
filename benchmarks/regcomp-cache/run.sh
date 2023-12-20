#!/usr/bin/env bash
#
# Synthetic test with 1000 regexes.
#
# Usage:
#   benchmarks/regcomp-cache/run.sh <function name>
#
# Example:
#   benchmarks/regcomp-cache/run.sh match-many


match-many() {
  local num_pat=${1:-1000}
  local num_str=${1:-1000}

  declare -a REGEXES=()
  for i in $(seq $num_pat); do
    REGEXES[i]="$i?$i*$i+"  # last char is modified with ? then * and +
  done

  echo "${REGEXES[@]}"

  local num_yes=0
  local num_tried=0

  for str in $(seq $num_str); do
    for i in $(seq $num_pat); do
      local re="${REGEXES[i]}"
      if [[ $str =~ $re ]]; then
        echo "string $str matches pattern $re"
        num_yes=$(( num_yes + 1 ))
      fi
      num_tried=$(( num_tried + 1 ))
    done
  done

  echo
  echo "num_yes = $num_yes"
  echo "num_tried = $num_tried"
}


"$@"

