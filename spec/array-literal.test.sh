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

#### s+=() with strict_array
case $SH in bash) ;; *) shopt --set strict_array;; esac

s1=hello
s2=world

# Overwriting Str with a new BashArray is allowed
eval 's1=(1 2 3 4)'
echo status=$?
declare -p s1
# Promoting Str to a BashArray is disallowed
eval 's2+=(1 2 3 4)'
echo status=$?
declare -p s2
## STDOUT:
status=0
declare -a s1=(1 2 3 4)
status=1
declare -- s2=world
## END
## N-I bash STDOUT:
status=0
declare -a s1=([0]="1" [1]="2" [2]="3" [3]="4")
status=0
declare -a s2=([0]="world" [1]="1" [2]="2" [3]="3" [4]="4")
## END

#### declare -A s+=() with strict_array
case $SH in bash) ;; *) shopt --set strict_array;; esac

s1=hello
s2=world

# Overwriting Str with a new BashAssoc is allowed
eval 'declare -A s1=([a]=x [b]=y)'
echo status=$?
declare -p s1
# Promoting Str to a BashAssoc is disallowed
eval 'declare -A s2+=([a]=x [b]=y)'
echo status=$?
declare -p s2
## STDOUT:
status=0
declare -A s1=(['a']=x ['b']=y)
status=1
declare -- s2=world
## END
## N-I bash STDOUT:
status=0
declare -A s1=([b]="y" [a]="x" )
status=0
declare -A s2=([0]="world" [b]="y" [a]="x" )
## END
