## compare_shells: bash
## oils_failures_allowed: 5

#### Lower Case with , and ,,
x='ABC DEF'
echo ${x,}
echo ${x,,}
echo empty=${empty,}
echo empty=${empty,,}
## STDOUT:
aBC DEF
abc def
empty=
empty=
## END

#### Upper Case with ^ and ^^
x='abc def'
echo ${x^}
echo ${x^^}
echo empty=${empty^}
echo empty=${empty^^}
## STDOUT:
Abc def
ABC DEF
empty=
empty=
## END

#### Case Folding of Unicode Characters

# https://www.utf8-chartable.de/unicode-utf8-table.pl

x=$'\u00C0\u00C8'  # upper grave
y=$'\u00E1\u00E9'  # lower acute

echo u ${x^}
echo U ${x^^}

echo l ${x,}
echo L ${x,,}

echo u ${y^}
echo U ${y^^}

echo l ${y,}
echo L ${y,,}

## STDOUT:
u ÀÈ
U ÀÈ
l àÈ
L àè
u Áé
U ÁÉ
l áé
L áé
## END

#### Lower Case with constant string (VERY WEIRD)
x='AAA ABC DEF'
echo ${x,A}
echo ${x,,A}  # replaces every A only?
## STDOUT:
aAA ABC DEF
aaa aBC DEF
## END

#### Lower Case glob

# Hm with C.UTF-8, this does no case folding?
export LC_ALL=en_US.UTF-8

x='ABC DEF'
echo ${x,[d-f]}
echo ${x,,[d-f]}  # This seems buggy, it doesn't include F?
## STDOUT:
ABC DEF
ABC deF
## END

#### ${x@u} U l L upper / lower case (bash 5.1 feature)

# https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html

x='abc def'
echo "${x@u}"

# TODO: we need to upgrade the spec tests to bash 5.1 (or bash 5.2 is coming
# out soon)

## N-I bash status: 1
## N-I bash STDOUT:
## END


#### ${x@Q}
x="FOO'BAR spam\"eggs"
eval "new=${x@Q}"
test "$x" = "$new" && echo OK
## STDOUT:
OK
## END

#### ${array@Q} and ${array[@]@Q}
array=(x 'y\nz')
echo ${array[@]@Q}
echo ${array@Q}
echo ${array@Q}
## STDOUT:
'x' 'y\nz'
'x'
'x'
## END
## OK osh STDOUT:
x $'y\\nz'
x
x
## END

#### ${!prefix@} ${!prefix*} yields sorted array of var names
ZOO=zoo
ZIP=zip
ZOOM='one two'
Z='three four'

z=lower

argv.py ${!Z*}
argv.py ${!Z@}
argv.py "${!Z*}"
argv.py "${!Z@}"
for i in 1 2; do argv.py ${!Z*}  ; done
for i in 1 2; do argv.py ${!Z@}  ; done
for i in 1 2; do argv.py "${!Z*}"; done
for i in 1 2; do argv.py "${!Z@}"; done
## STDOUT:
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z ZIP ZOO ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z ZIP ZOO ZOOM']
['Z ZIP ZOO ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
## END

#### ${!prefix@} matches var name (regression)
hello1=1 hello2=2 hello3=3
echo ${!hello@}
hello=()
echo ${!hello@}
## STDOUT:
hello1 hello2 hello3
hello hello1 hello2 hello3
## END

#### ${var@a} for attributes
array=(one two)
echo ${array@a}
declare -r array=(one two)
echo ${array@a}
declare -rx PYTHONPATH=hi
echo ${PYTHONPATH@a}

# bash and osh differ here
#declare -rxn x=z
#echo ${x@a}
## STDOUT:
a
ar
rx
## END

#### ${var@a} error conditions
echo [${?@a}]
## STDOUT:
[]
## END

#### undef and @P @Q @a
$SH -c 'echo ${undef@P}'
echo status=$?
$SH -c 'echo ${undef@Q}'
echo status=$?
$SH -c 'echo ${undef@a}'
echo status=$?
## STDOUT:

status=0

status=0

status=0
## END
## OK osh STDOUT:

status=0
''
status=0

status=0
## END


#### argv array and @P @Q @a
$SH -c 'echo ${@@P}' dummy a b c
echo status=$?
$SH -c 'echo ${@@Q}' dummy a 'b\nc'
echo status=$?
$SH -c 'echo ${@@a}' dummy a b c
echo status=$?
## STDOUT:
a b c
status=0
'a' 'b\nc'
status=0

status=0
## END
## OK osh STDOUT:
status=1
a $'b\\nc'
status=0
a
status=0
## END

#### assoc array and @P @Q @a

# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${A@P} - ${A[@]@P}'
echo status=$?

# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${A@Q} - ${A[@]@Q}'
echo status=$?

$SH -c 'declare -A A=(["x"]=y); echo ${A@a} - ${A[@]@a}'
echo status=$?
## STDOUT:
- y
status=0
- 'y'
status=0
A - A
status=0
## END
## OK osh STDOUT:
status=1
status=1
A - A
status=0
## END

#### ${!var[@]@X}
# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${!A[@]@P}'
if test $? -ne 0; then echo fail; fi

# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x y"]="y"); echo ${!A[@]@Q}'
if test $? -ne 0; then echo fail; fi

$SH -c 'declare -A A=(["x"]=y); echo ${!A[@]@a}'
if test $? -ne 0; then echo fail; fi
# STDOUT:



# END
## OK osh STDOUT:
fail
'x y'
a
## END

#### ${#var@X} is a parse error
# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${#A[@]@P}'
if test $? -ne 0; then echo fail; fi

# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${#A[@]@Q}'
if test $? -ne 0; then echo fail; fi

$SH -c 'declare -A A=(["x"]=y); echo ${#A[@]@a}'
if test $? -ne 0; then echo fail; fi
## STDOUT:
fail
fail
fail
## END

#### ${!A@a} and ${!A[@]@a}
declare -A A=(["x"]=y)
echo x=${!A[@]@a}
echo x=${!A@a}

# OSH prints 'a' for indexed array because the AssocArray with ! turns into
# it.  Disallowing it would be the other reasonable behavior.

## STDOUT:
x=
x=
## END
