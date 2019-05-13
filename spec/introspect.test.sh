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
#
# In other words, BASH_SOURCE is about the DEFINITION.  While FUNCNAME and
# BASH_LINENO are about the CALL.


#### ${FUNCNAME[@]} array
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

#### FUNCNAME with source
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

#### ${BASH_SOURCE[@]} with source and function name
argv.py "${BASH_SOURCE[@]}"
source spec/testdata/bash-source-simple.sh
f
## STDOUT: 
[]
['spec/testdata/bash-source-simple.sh']
['spec/testdata/bash-source-simple.sh']
## END

#### ${BASH_SOURCE[@]} with line numbers
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

#### ${BASH_LINENO[@]} is a stack of line numbers for function calls
# note: it's CALLS, not DEFINITIONS.
g() {
  argv.py G "${BASH_LINENO[@]}"
}
f() {
  argv.py 'begin F' "${BASH_LINENO[@]}"
  g  # line 6
  argv.py 'end F' "${BASH_LINENO[@]}"
}
argv.py ${BASH_LINENO[@]}
f  # line 9
## STDOUT: 
[]
['begin F', '10']
['G', '6', '10']
['end F', '10']
## END

#### $LINENO is the current line, not line of function call
echo $LINENO  # first line
g() {
  argv.py $LINENO  # line 3
}
f() {
  argv.py $LINENO  # line 6
  g
  argv.py $LINENO  # line 8
}
f
## STDOUT: 
1
['6']
['3']
['8']
## END

#### $LINENO for [[
echo one
[[ $LINENO -eq 2 ]] && echo OK
## STDOUT:
one
OK
## END

#### $LINENO for ((
echo one
(( x = LINENO ))
echo $x
## STDOUT:
one
2
## END

#### $LINENO in for loop
# hm bash doesn't take into account the word break.  That's OK; we won't either.
echo one
for x in \
  $LINENO zzz; do
  echo $x
done
## STDOUT:
one
2
zzz
## END

#### $LINENO in for (( loop
# This is a real edge case that I'm not sure we care about.  We would have to
# change the span ID inside the loop to make it really correct.
echo one
for (( i = 0; i < $LINENO; i++ )); do
  echo $i
done
## STDOUT:
one
0
1
## END

#### $LINENO for assignment
a1=$LINENO a2=$LINENO
b1=$LINENO b2=$LINENO
echo $a1 $a2
echo $b1 $b2
## STDOUT:
1 1
2 2
## END
