#!/bin/bash

set -o noglob  # for unquoted $text splitting

tokenize() {
  # read it once
  read -d '' text

  for word in $text; do  # relies on word splitting
    echo "$word"
  done
}

main() {
  iters=${1:-100}

  # read it once
  read -d '' text

  declare -A words

  # do it a bunch of times
  for (( i = 0; i < iters; ++i )); do
    for word in $text; do  # relies on word splitting

      # Hm this isn't correct in bash!
      (( words["$word"] += 1 ))

      # This seems to work?  wtf?
      # This causes a parse error in OSH though... Do we need two benchmarks?

      # Or maybe we need something to turn of static parsing?
      # similar to git

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
