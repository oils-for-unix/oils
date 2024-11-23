## our_shell: ysh

#### ysh usage

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

## STDOUT:
(C (w <Id.Lit_Chars echo>) (w (SQ sq)))
(C (w <Id.Lit_Chars echo>) (w (DQ <Id.Lit_Chars "hi "> ($ x) <Id.Lit_Chars " "> (${ Id.VSub_Name y))))
(command.VarDecl
  keyword: <Id.KW_Var var>
  lhs: [(NameType left:<Id.Expr_Name x> name:x)]
  rhs: (expr.Binary op:<Id.Arith_Plus "+"> left:(Const Id.Expr_DecInt _) right:(Var a))
)
## END
