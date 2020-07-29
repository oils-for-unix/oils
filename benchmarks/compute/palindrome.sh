#!/bin/bash
#
# Usage:
#   ./unicode.sh <function name>

#shopt -s globasciiranges

main() {
  if test "$1" = "unicode"; then
    echo "palindrome.sh: unicode" 1>&2
  else
    LANG=C
  fi

  while read -r line; do
    local n=${#line}

    if test $n -eq 0; then  # skip blank lines
      continue
    fi

    h=$((n / 2))  # floor division
    local palindrome=T
    for (( i = 0; i < h; ++i )); do
      #echo ${line:i:1} ${line:n-1-i:1}
      if test "${line:i:1}" != "${line:n-1-i:1}"; then
        palindrome=''
      fi
    done

    if test -n "$palindrome"; then
      printf '%s\n' "$line"
    fi
  done
}

main "$@"
