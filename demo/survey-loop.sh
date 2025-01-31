#!/usr/bin/env bash
#
# Survey loop behavior
#
# Usage:
#   demo/survey-str-api.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH

# Python and JS string and regex replacement APIs

mutate-py() {
  echo ---
  echo PY

  python3 -c '
mylist = [1,2,3]
for x in mylist:
  if x == 2:
    mylist.append(99)
  print(x)
'

  echo ---
  echo PY comp

  python3 -c '
def myappend(li, i):
  if i == 1:
    li.append(99)
  print(i)
  return i

mylist = [1,2,3]
y = [myappend(mylist, i) for i in mylist]
print(y)
'
}

mutate-js() {
  echo ---
  echo 'JS let'

  nodejs -e '
let mylist = [1,2,3]
for (let x of mylist) {
  if (x === 2) {
    mylist.push(99)
  }
  console.log(x)
}
'

  echo ---
  echo 'JS var'

  nodejs -e '
var mylist = [1,2,3]
for (var x of mylist) {
  if (x === 2) {
    mylist.push(99)
  }
  console.log(x)
}
'
}

mutate-sh() {
  local sh=${1:-bash}

  echo ---
  echo sh=$sh

  $sh -c '
  declare -a mylist=(1 2 3)
  for x in "${mylist[@]}"; do
    if test $x == 2; then
      mylist+=(99)
    fi
    echo $x
  done
  echo "${mylist[@]}"
'
}

mutate-ysh() {
  echo ---
  echo 'YSH'

  ysh -c '
var mylist = [1,2,3]
for x in (mylist) {
  if (x === 2) {
    call mylist->append(99)
  }
  echo $x
}
'
}

compare-mutate() {
  mutate-py
  mutate-js
  mutate-sh bash
  mutate-sh osh
  mutate-ysh
}

"$@"
