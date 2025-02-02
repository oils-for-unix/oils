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
  echo PY DICT

if false; then
  # dict size changed during iteration!!
  python3 -c '
mydict = {1: None, 2: None, 3: None}
for x in mydict:
  if x == 2:
    mydict[99] = None
  print(x)
'
fi

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
  echo 'JS let in OBJ'

  nodejs -e '
let myobj = {"1": null, "2": null, "3": null}
for (let x in myobj) {
  if (x === "2") {
    myobj["99"] = null;
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

YSH=${YSH:-bin/ysh}

mutate-ysh() {
  echo ---
  echo 'YSH List'

  $YSH -c '
var mylist = [1,2,3]
for x in (mylist) {
  if (x === 2) {
    call mylist->append(99)
  }
  echo $x
}
'

  echo ---
  echo 'YSH Dict'

  $YSH -c '
var mydict = {"1": null, "2": null, "3": null}
for x in (mydict) {
  if (x === "2") {
    setvar mydict["99"] = null
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
