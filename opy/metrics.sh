#!/bin/bash
#
# Somewhat like build/metrics.sh for OPy.
#
# Usage:
#   ./metrics.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Compare opcodes emitted by compiler2 vs. ones defined.
compare-opcodes() {
  # 67 opcodes emitted
  local pat='self.emit|self.unaryOp|self.binaryOp|self._nameOp|self._implicitNameOp|INPLACE|CALL_FUNCTION'
  egrep "$pat" compiler2/pycodegen.py | egrep -o '[A-Z][A-Z_]+' |
    sort | uniq > _tmp/opcodes-emitted.txt

  # 119 ops?
  PYTHONPATH=. python2 > _tmp/opcodes-defined.txt -c '
from compiler2 import opcode
names = sorted(opcode.opmap)
for n in names:
  print(n)
'

  diff -u _tmp/opcodes-{defined,emitted}.txt | tee _tmp/opcode-diff.txt || true
  
  # Opcodes emitted but not defined?  This is approximate because some opcodes
  # are dynamically defined, like SLICE+0 vs SLICE.
  grep '^+' _tmp/opcode-diff.txt | grep -v SLICE

  # Found issue: VERSION=1 is still there, and UNPACK_TUPLE isn't used!

  wc -l _tmp/opcodes-{defined,emitted}.txt  # 119 defined
}

"$@"
