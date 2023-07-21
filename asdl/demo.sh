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

_run-asdl() {
  local asdl_path=$1  # e.g. osh/osh.asdl

  local name
  name=$(basename $asdl_path .asdl)

  local out=_tmp/${name}_asdl.py

  # abbrev module is optional
   > $out
}

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

py-exceptions() {
  PYTHONPATH='.:vendor/:_tmp/'

  cat >_tmp/exceptions.asdl <<EOF
module runtime
{
  control_flow =
    Return(int code)
  | Break(int levels)
  | Continue(int levels)
  deriving [Exception]
}
EOF

  asdl/asdl_main.py mypy _tmp/exceptions.asdl > _tmp/exceptions_asdl.py

  python2 -c '
from _tmp.exceptions_asdl import control_flow, control_flow_t, control_flow_str

def demo(i):
  if i == 0:
    raise control_flow.Return(0)
  else:
    raise control_flow.Break(0)

for i in range(2):
  try:
    demo(i)
  except control_flow.Return as ret:
    print("Returned %d" % ret.code)
  except control_flow_t as other:
    print("Unexpected control flow: %s" % control_flow_str(other.tag()))
'

  asdl/asdl_main.py cpp _tmp/exceptions.asdl _tmp/exceptions
  cat _tmp/exceptions.{h,cc}
}

"$@"
