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
## STDOUT:
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
['Z ZIP ZOO ZOOM']
['Z', 'ZIP', 'ZOO', 'ZOOM']
## END

