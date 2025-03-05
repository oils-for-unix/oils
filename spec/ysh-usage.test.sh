## our_shell: ysh
## oils_failures_allowed: 2

#### ysh --location-str --location-start-line

set +o errexit

$[ENV.SH] --location-str foo.hay --location-start-line 42 -c 'echo ()' 2>err.txt

cat err.txt | grep -o -- '-- foo.hay:42: Unexpected'


# common idiom is to use -- to say it came from a file
$[ENV.SH] --location-str '[ stdin ]' --location-start-line 10 -c 'echo "line 10";
echo ()' 2>err.txt

cat err.txt | fgrep -o -- '-- [ stdin ]:11: Unexpected'

## STDOUT:
-- foo.hay:42: Unexpected
line 10
-- [ stdin ]:11: Unexpected
## END

#### ysh --eval

echo 'echo one --eval' >one.ysh
$[ENV.SH] --eval one.ysh -c 'echo flag -c'
echo

echo 'echo myscript' >myscript.sh
$[ENV.SH] --eval one.ysh myscript.sh
echo

# eval comes before oshrc
echo 'echo oshrc' >oshrc
$[ENV.SH] --rcfile oshrc --eval one.ysh -i -c 'echo flag -c'
echo

exit

echo 'echo two --eval' >two.ysh

$[ENV.SH] --eval one.ysh --eval two.ysh -c 'echo flag -c'


## STDOUT:
one --eval
flag -c

one --eval
myscript

one --eval
oshrc
flag -c

## END

#### ysh --eval-pure

echo TODO

## STDOUT:
## END

#### ysh --eval cannot load file

$[ENV.SH] --eval nonexistent.ysh -c 'echo flag -c'

## status: 1
## STDOUT:
## END

#### ysh --eval parse error

echo 'echo zz; ( echo' >bad.ysh

$[ENV.SH] --eval bad.ysh -c 'echo hi'

## STDOUT:
## END

#### ysh --eval runtime error

echo 'echo flag --eval; false; echo bye' >bad.ysh

$[ENV.SH] --eval bad.ysh -c 'echo flag -c'

## STDOUT:
flag --eval
flag -c
## END

#### ysh --eval exit status

echo 'echo hi; exit 99; echo bye' >e.ysh

$[ENV.SH] --eval e.ysh -c 'echo hi'

## status: 99
## STDOUT:
hi
## END

#### ysh --eval respects _this_dir

#echo tmp=$[ENV.TMP]

var dir = "$[ENV.TMP]/code"
mkdir -p $dir

echo 'echo one; source $_this_dir/two.ysh' > $dir/one.ysh
echo 'echo two' > $dir/two.ysh

$[ENV.SH] --eval $dir/one.ysh -c 'echo flag -c'

## STDOUT:
one
two
flag -c
## END


#### --debug-file
var TMP = ENV.TMP
$[ENV.SH] --debug-file $TMP/debug.txt -c 'true'
grep 'Oils started with' $TMP/debug.txt >/dev/null && echo yes
## stdout: yes

#### Filename quoting

echo '(BAD' > no-quoting
echo '(BAD' > 'with spaces.sh'
echo '(BAD' > $'bad \xff'

write -n '' > err.txt

$[ENV.SH] no-quoting 2>>err.txt || true
$[ENV.SH] 'with spaces.sh' 2>>err.txt || true
$[ENV.SH] $'bad \xff' 2>>err.txt || true

egrep --only-matching '^.*:1' err.txt

## STDOUT:
no-quoting:1
"with spaces.sh":1
b'bad \yff':1
## END


#### shopt --set verbose_errexit

try {
  $[ENV.SH] -c '/bin/false' 2>on.txt
}

try {
  $[ENV.SH] +o verbose_errexit -c '/bin/false' 2>off.txt
}

wc -l on.txt off.txt
#echo
#cat on.txt off.txt

## STDOUT:
 3 on.txt
 0 off.txt
 3 total
## END

#### YSH shows options correctly (bug fix)

$[ENV.SH] -o | egrep 'errexit|pipefail'

## STDOUT:
set -o errexit
set -o pipefail
## END

#### --tool syntax-tree respects frontend/syntax_abbrev.py

$[ENV.SH] --tool syntax-tree <<< '''
echo 'sq'
'''

$[ENV.SH] --tool syntax-tree <<< '''
echo "hi $x ${y}"
'''

$[ENV.SH] --tool syntax-tree <<< '''
var x = 42 + a
'''

# this reflects the default width

## STDOUT:
(C (w <Lit_Chars echo>) (w (SQ sq)))
(C
  (w <Lit_Chars echo>)
  (w (DQ <Lit_Chars "hi "> ($ x) <Lit_Chars " "> (${ VSub_Name y)))
)
(command.VarDecl
  keyword:<KW_Var var>
  lhs:[(NameType left:<Expr_Name x> name:x)]
  rhs:(expr.Binary op:<Arith_Plus "+"> left:(Const Expr_DecInt _) right:(Var a))
)
## END
