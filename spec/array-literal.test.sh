## compare_shells: bash

#### bash mangles indexed array #1 (keys undergoes arithmetic evaluation)
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

#### bash mangles indexed array #1 (associative array is OK)
declare -A a
a=([k1]=v1 [k2]=v2)
echo ${a["k1"]}
echo ${a["k2"]}
## STDOUT:
v1
v2
## END

#### bash mangles indexed array #2 (associative array is OK)
declare -A a
a=([k2]=-{a,b}-)
echo ${a["k2"]}
## STDOUT:
-{a,b}-
## END

#### bash mangles indexed array #2 (Bash does not recognize [index]=brace-expansion)
a=([k2]=-{a,b}-)
echo ${a["k2"]}
## STDOUT:
-{a,b}-
## END
## BUG bash STDOUT:
[k2]=-a-
## END
