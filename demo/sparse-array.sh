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

demo() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  # Copied from spec/ble-idioms.test.sh

  $osh <<'EOF'
a=( {1..100} )
a[1000]='sparse'

# Convert it to the Dict[BigInt, str] representation
var sp = _a2sp(a)

time while true; do
  var len = _opsp(sp, 'len')
  echo $len

  var new = 'TODO - test slice'

  break
done
EOF

  return

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
