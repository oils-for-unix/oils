#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: Put parse-all and run-all in test/oil-language.sh?

# This doesn't distinguish if they should parse with osh or Oil though!

parse-all-osh() {
  find oil_lang/testdata -name '*.sh' -o -name '*.osh' \
    | xargs -n 1 -- bin/osh -n
}

parse-all-tea() {
  find oil_lang/testdata -name '*.tea' \
    | xargs -n 1 -- bin/oil -n
}

run-all() {
  for prog in oil_lang/testdata/*.{sh,osh}; do
    echo $prog

    local skip=''
    case $prog in
      (*/assign.osh) skip=1 ;;
      (*/no-dynamic-scope.osh) skip=1 ;;
      (*/inline-function-calls.sh) skip=1 ;;
    esac

    if test -n "$skip"; then
      echo "skipping $prog"
      continue
    fi

    echo ---
    bin/osh $prog
  done
}

demo() {
  bin/osh oil_lang/testdata/array-rewrite-1.sh

  bin/osh oil_lang/testdata/array-rewrite-2.sh
  bin/osh oil_lang/testdata/array-splice-demo.osh

  bin/osh oil_lang/testdata/hello.osh

  bin/osh oil_lang/testdata/inline-function-calls.sh all

  bin/osh oil_lang/testdata/sigil-pairs.sh

  # Fails correctly
  bin/osh oil_lang/testdata/no-dynamic-scope.osh

  # TODO: Debug crash
  #bin/osh oil_lang/testdata/assign.osh
}

"$@"
