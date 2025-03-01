## compare_shells: bash

#### [k1]=v1 (BashArray)
# Note: This and next tests have originally been in "spec/assign.test.sh" and
# compared the behavior of OSH's BashAssoc and Bash's indexed array.  After
# supporting "arr=([index]=value)" for indexed arrays, the test was adjusted
# and copied here. See also the corresponding tests in "spec/assign.test.sh"
a=([k1]=v1 [k2]=v2)
echo ${a["k1"]}
echo ${a["k2"]}
## STDOUT:
v2
v2
## END

#### [k1]=v1 (BashAssoc)
declare -A a
a=([k1]=v1 [k2]=v2)
echo ${a["k1"]}
echo ${a["k2"]}
## STDOUT:
v1
v2
## END

#### [k1]=v1 looking like brace expansions (BashArray)
declare -A a
a=([k2]=-{a,b}-)
echo ${a["k2"]}
## STDOUT:
-{a,b}-
## END

#### [k1]=v1 looking like brace expansions (BashAssoc)
a=([k2]=-{a,b}-)
echo ${a["k2"]}
## STDOUT:
-{a,b}-
## END
## BUG bash STDOUT:
[k2]=-a-
## END

#### BashArray cannot be changed to BashAssoc and vice versa
declare -a a=(1 2 3 4)
eval 'declare -A a=([a]=x [b]=y [c]=z)'
echo status=$?
argv.py "${a[@]}"

declare -A A=([a]=x [b]=y [c]=z)
eval 'declare -a A=(1 2 3 4)'
echo status=$?
argv.py $(printf '%s\n' "${A[@]}" | sort)
## STDOUT:
status=1
['1', '2', '3', '4']
status=1
['x', 'y', 'z']
## END
