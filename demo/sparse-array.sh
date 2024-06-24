#!/usr/bin/env bash
#
# Test sparse array
#
# Relevant files:
#
#   test/ble-idioms.test.sh
#
#   core/shell.py defines these functions:
#     _a2sp
#     _d2sp
#     _opsp
#   builtin/func_misc.py is where they are implemented
#
#   core/value.asdl defines value.{BashArray,SparseArray}
#
#   _gen/core/value.asdl.* - generated from value.asdl
#
#   _gen/bin/oils_for_unix.mycpp.cc  has the translation of

#
# Usage:
#   demo/sparse-array.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

sum-shift() {
  local n=${1:-1000}

  # Populate array 0 .. n-1
  a=()
  for (( i = 0; i < n; ++i )); do
    a+=( $i )
    #a+=( 1 )
  done
  #echo "${a[@]}"

  # Quadratic loop: sum all numbers, shift by 1
  local sum=0
  while true; do
    local len=${#a[@]}
    if test $len -eq 0; then
      break
    fi

    for (( i = 0; i < len; ++i )); do
      sum=$(( sum + ${a[i]} ))
    done

    #echo sum=$sum

    # Shift
    a=( ${a[@]:1} )
  done

  echo sum=$sum
}

sparse-sum-shift() {
  local osh=$1

  $osh <<'EOF'
shopt --set ysh:upgrade

f() {
  local n=${1:-1000}

  a=()
  var sp = _a2sp(a)  # empty sparse array

  # Populate SparseArray 0 .. n-1
  for (( i = 0; i < n; ++i )); do
    to_append=( $i )
    call _opsp(sp, 'append', to_append)
  done

  #echo "${a[@]}"
  echo "length $[_opsp(sp, 'len')]"
  #echo SUBST @[_opsp(sp, 'subst')]
  #echo KEYS @[_opsp(sp, 'keys')]

  var sum = 0

  while (true) {
    var length = _opsp(sp, 'len')
    if (length === 0) {
      break
    }

    #echo ZERO $sum $[_opsp(sp, 'get', 0)]
    #echo ONE $sum $[_opsp(sp, 'get', 1)]
    for i in (0 .. length) {
      setvar sum += _opsp(sp, 'get', i)
    }

    #echo sum=$sum

    # Slice to BashArray
    var a = _opsp(sp, 'slice', 1, length)

    # Convert back - is this slow?
    setvar sp = _a2sp(a)
  }

  echo sum=$sum
}

f 

EOF
}

compare-sum-shift() {
  # more like 1M iterations - 1.8 seconds in bash
  # So that's 1.8 ms for 1000 iterations

  local osh=_bin/cxx-opt/osh
  ninja $osh

  echo ===
  echo $osh SparseArray
  echo
  time sparse-sum-shift $osh

  for sh in bash $osh; do
    echo ===
    echo $sh
    echo
    time $sh $0 sum-shift
  done
}

append-sparse() {
  local n=${1:-24}  # up to 2^n
  local m=${2:-2000}

  to_append=( $(seq $m) )  # split words

  a=()
  for (( i = 0; i < n; ++i )) {
    a[$(( 1 << i ))]=$i
    a+=( ${to_append[@]} )
  }
  #echo ${a[@]}
  #echo ${!a[@]}
  echo ${#a[@]}
}

sparse-append-sparse() {
  local osh=${1:-_bin/cxx-opt/osh}
  local n=${2:-24}
  local m=${3:-2000}

  NUM_ITERS=$n TO_APPEND=$m $osh <<'EOF'
n=$NUM_ITERS
m=$TO_APPEND
to_append=( $(seq $m) )  # split words before ysh:upgrade


shopt --set ysh:upgrade

f() {
  a=()
  var sp = _a2sp(a)

  for (( i = 0; i < n; ++i )) {
    call _opsp(sp, 'set', 1 << i, str(i))
    call _opsp(sp, 'append', to_append)

    #time call _opsp(sp, 'append', to_append)
    #echo $[_opsp(sp, 'len')]
    #echo
  }
  echo $[_opsp(sp, 'len')]
  #echo @[_opsp(sp, 'subst')]
  #echo @[_opsp(sp, 'keys')]
}

f
EOF
}

compare-append-sparse() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  echo ===
  echo $osh SparseArray
  echo
  time sparse-append-sparse $osh

  for sh in bash $osh; do
    echo ===
    echo $sh
    echo
    time $sh $0 append-sparse
  done
}

demo() {
  # Compiles faster
  #local osh=_bin/cxx-asan/osh

  local osh=_bin/cxx-opt/osh

  ninja $osh

  $osh <<'EOF'

# Create regular bash array

a=( {1..100} )
a[1000]='sparse'
echo $[type(a)]

# Time O(n^2) slicing in a loop

time while true; do
  # Convert it to the Dict[BigInt, str] representation
  var sp = _a2sp(a)
  #echo $[type(sp)]

  var len = _opsp(sp, 'len')
  #echo "sparse length $len"

  setvar a = _opsp(sp, 'slice', 1, 2000)
  #echo "array length ${#a[@]}"
  echo "array ${a[@]}"

  if test ${#a[@]} -eq 0; then
    break
  fi
done
EOF

  return

  # Copied from spec/ble-idioms.test.sh
  $osh <<'EOF'

a=( foo {25..27} bar )

a[10]='sparse'

var sp = _a2sp(a)
echo $[type(sp)]

echo len: $[_opsp(sp, 'len')]

#echo $[len(sp)]

shopt -s ysh:upgrade

echo subst: @[_opsp(sp, 'subst')]
echo keys: @[_opsp(sp, 'keys')]

echo slice: @[_opsp(sp, 'slice', 2, 5)]

call _opsp(sp, 'set', 0, 'set0')

echo get0: $[_opsp(sp, 'get', 0)]
echo get1: $[_opsp(sp, 'get', 1)]

to_append=(x y)
call _opsp(sp, 'append', to_append)
echo subst: @[_opsp(sp, 'subst')]
echo keys: @[_opsp(sp, 'keys')]

echo ---

# Sparse
var d = {
  '1': 'a',
  '10': 'b',
  '100': 'c',
  '1000': 'd',
  '10000': 'e',
  '100000': 'f',
}

var sp2 = _d2sp(d)

echo len: $[_opsp(sp2, 'len')]
echo subst: @[_opsp(sp2, 'subst')]

EOF

}

"$@"
