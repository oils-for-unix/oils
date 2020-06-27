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

#### Lower Case with constant string (VERY WEIRD)
x='AAA ABC DEF'
echo ${x,A}
echo ${x,,A}  # replaces every A only?
## STDOUT:
aAA ABC DEF
aaa aBC DEF
## END

#### Lower Case glob
x='ABC DEF'
echo ${x,[d-f]}
echo ${x,,[d-f]}  # This seems buggy, it doesn't include F?
## STDOUT:
ABC DEF
ABC deF
## END

#### ${x@Q}
x="FOO'BAR spam\"eggs"
eval "new=${x@Q}"
test "$x" = "$new" && echo OK
## STDOUT:
OK
## END

#### ${array@Q}
array=(x 'y\nz')
echo ${array@Q}
echo ${array[@]@Q}
## STDOUT:
'x'
'x' 'y\nz'
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

#### assoc array and @P @Q @a

# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${A@P} - ${A[@]@P} - ${!A[@]@P}'
echo status=$?

# note: "y z" causes a bug!
$SH -c 'declare -A A=(["x"]="y"); echo ${A@P} - ${A[@]@Q} - ${!A[@]@Q}'
echo status=$?

$SH -c 'declare -A A=(["x"]=y); echo ${A@a} - ${A[@]@a} - ${!A[@]@a}'
echo status=$?
## STDOUT:
- y -
status=0
- 'y' -
status=0
A - A -
status=0
## END
