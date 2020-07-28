#!/bin/bash

set -o noglob  # for unquoted $text splitting

tokenize() {
  # read it once
  read -r -d '' text

  for word in $text; do  # relies on word splitting
    echo "$word"
  done
}

main() {
  iters=${1:-100}

  # read it once
  read -r -d '' text

  declare -A words

  # do it a bunch of times
  for (( i = 0; i < iters; ++i )); do

    # Relies on unquoted IFS splitting.  Difference with Python: Python will
    # give you \, but IFS splitting won't.
    for word in $text; do

      # Hm this isn't correct in bash!
      old=${words["$word"]}
      words["$word"]=$((old + 1))

      # BUG in bash, see spec/assoc case #37
      #(( words["$word"] += 1 ))
      #(( words[\$word] += 1 ))
    done
  done

  # note: we can sort the output in the benchmark and assert that it's the same?

  for word in "${!words[@]}"; do
    echo "${words["$word"]} $word"
  done
}

main "$@"
#tokenize "$@"
