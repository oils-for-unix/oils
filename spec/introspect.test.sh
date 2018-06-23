#!/usr/bin/env bash
#
# Test call stack introspection.  There are a bunch of special variables
# defined here:
#
# https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html
# 
# - The shell function ${FUNCNAME[$i]} is defined in the file
#   ${BASH_SOURCE[$i]} and called from ${BASH_SOURCE[$i+1]}
#
# - ${BASH_LINENO[$i]} is the line number in the source file
#   (${BASH_SOURCE[$i+1]}) where ${FUNCNAME[$i]} was called (or
#   ${BASH_LINENO[$i-1]} if referenced within another shell function). 
#
# - For instance, ${FUNCNAME[$i]} was called from the file
#   ${BASH_SOURCE[$i+1]} at line number ${BASH_LINENO[$i]}. The caller builtin
#   displays the current call stack using this information. 
#
# So ${BASH_SOURCE[@]} doesn't line up with ${BASH_LINENO}.  But
# ${BASH_SOURCE[0]} does line up with $LINENO!
#
# Geez.


### ${FUNCNAME[@]} array
g() {
  argv.py "${FUNCNAME[@]}"
}
f() {
  argv.py "${FUNCNAME[@]}"
  g
  argv.py "${FUNCNAME[@]}"
}
f
## STDOUT: 
['f']
['g', 'f']
['f']
## END

### FUNCNAME with source
f() {
  . spec/testdata/echo-funcname.sh
}
g() {
  f
}
g
. spec/testdata/echo-funcname.sh
argv.py "${FUNCNAME[@]}"
## STDOUT:
['source', 'f', 'g']
['source']
[]
## END

### ${BASH_SOURCE[@]} is a stack of source files for function calls
$SH spec/testdata/bash-source.sh
## STDOUT: 
['begin F funcs', 'f', 'main']
['begin F files', 'spec/testdata/bash-source.sh', 'spec/testdata/bash-source.sh']
['begin F lines', '21', '0']
['G funcs', 'g', 'f', 'main']
['G files', 'spec/testdata/bash-source-2.sh', 'spec/testdata/bash-source.sh', 'spec/testdata/bash-source.sh']
['G lines', '15', '21', '0']
['end F funcs', 'f', 'main']
['end F', 'spec/testdata/bash-source.sh', 'spec/testdata/bash-source.sh']
['end F lines', '21', '0']
## END

### ${BASH_LINENO[@]} is a stack of line numbers for function calls
# note: it's CALLS, not DEFINITIONS.
g() {
  argv.py G "${BASH_LINENO[@]}"
}
f() {
  argv.py 'begin F' "${BASH_LINENO[@]}"
  g  # line 6
  argv.py 'end F' "${BASH_LINENO[@]}"
}
f  # line 9
## STDOUT: 
['begin F', '9']
['G', '6', '9']
['end F', '9']
## END

### $LINENO is the current line, not line of function call
g() {
  argv.py $LINENO  # line 2
}
f() {
  argv.py $LINENO  # line 5
  g
  argv.py $LINENO  # line 7
}
f
## STDOUT: 
['5']
['2']
['7']
## END

