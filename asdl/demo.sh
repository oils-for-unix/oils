#!/usr/bin/env bash
#
# Demo of Python codegen for simpler imports and API
# With backward compatibility
#
# Usage:
#   asdl/demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

py-api() {
  local pkg=_tmp/runtime_asdl

  mkdir -v -p $pkg

  touch _tmp/__init__.py

  cat >$pkg/__init__.py <<EOF
class value_t(object):
  pass

class value_e(object):
  pass

class value(object):
  class Str(value_t):
    pass

# Do all the aliases LAST
#from .value import Str as value__Str

EOF

  cat >$pkg/value.py <<EOF

#from . import value_t
#
#class Str(value_t):
#  pass
EOF


  PYTHONPATH=_tmp python2 -c '
#from _tmp.runtime_asdl import value, value_e, value_t
#from _tmp.runtime_asdl import value__Str

from _tmp.runtime_asdl import value, value_e, value_t


print(value)

print(value.Str)
#print(value.Str.__bases__)

#print(value__Str)

print()

print(value_e)
print(value_t)
'

  python3 -m mypy _tmp/runtime_asdl/{__init__,value}.py
}

"$@"
