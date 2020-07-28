#!/bin/bash
#
# Usage:
#   ./unicode.sh <function name>

#shopt -s globasciiranges

main() {
  # need RAW here!!!
  read -r -d '' text

  local len=${#text}
  echo len=$len

  local pat='[A-Z]'
  # why doesn't this work???
  #local pat='[#-~]'


  for (( i = 0; i < len; ++i )); do
    local ch="${text:i:1}"
    #if [[ $ch =~ $pat ]]; then
    if true; then
      echo "$i $ch"
    else
      #echo "[$i $ch]"
      true
    fi
  done
}

main "$@"
