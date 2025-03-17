#!/usr/bin/env bash
#
# Survey List/array APIs
#
# Usage:
#   demo/survey-list.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

# Python and JS string and regex replacement APIs

insert() {
  # negative underflow just means insert at the beginning
  python3 -c '
a = ["a", "b", "c", "d", "e"]

a.insert(0, "zero")
print(a)

a.insert(-1, "negative 1")
print(a)
a.insert(-1, "negative 1 again")
print(a)

a.insert(-98, "negative 98")
print(a)

a.insert(-97, "negative 97")
print(a)
'
}

"$@"
