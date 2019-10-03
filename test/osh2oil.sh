#!/usr/bin/env bash
#
# Usage:
#   ./osh-to-oil-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh

osh-to-oil() {
  bin/oshc translate "$@"
}

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
osh0-oil3() {
  set +o errexit
  osh-to-oil "$@" | diff -u /dev/fd/3 - 
  local status=$?
  set -o errexit

  if test $status -ne 0; then
    fail
  fi
}

args-vars() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo one "$@" two
OSH
echo one @Argv two
OIL

  # These are all the same.  Join by first char of IFS.
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo one $* "__$*__" $@ two
OSH
echo one $ifsjoin(Argv) "__$ifsjoin(Argv)__" $ifsjoin(Argv) two
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $? $#
OSH
echo $Status $Argc
OIL
}

unquote-subs() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "$1" "$foo"
OSH
echo $1 $foo
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "${foo}"
OSH
echo $(foo)
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "$(echo hi)"
OSH
echo $[echo hi]
OIL
}

special-vars() {
  # TODO: Some ops don't require $(), like $foo[1] and $foo[1:1+3]
  # We don't want $(foo[1]).
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${?} ${#} ${@}
OSH
echo $(Status) $(len(Argv)) @Argv
OIL

  # How to do $1 and then 0?
  # $join([$1 0])

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $9 $10 ${10} ${11}
OSH
echo $9 $10 $10 $11   # Rule is changed
OIL
}

arg-array() {
  # Only "$@" goes to @Argv
  # "__$@__" should be
  #
  # "__$Argv[0]" @Argv[1:-1] "$Argv[-1]__"
  # 
  # But this is probably too rare to really happen.  Just remove it.

  # Yeah the rest go to $join(Argv)
  # does join respect IFS though?  Have to work that out.
  # or maybe $ifsjoin(Argv) -- make explicit the global variable.

  # NOTE: This is with autosplit?  What about without splitting?

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $@ $* "$@" "$*" "__$@__" "__$*__"
OSH
echo $ifsjoin(Argv) $ifsjoin(Argv) @Argv "$ifsjoin(Argv)" "__$ifsjoin(Argv)__" "__$ifsjoin(Argv)__"
OIL
}

bracket-ops() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${a[1]} ${a[@]} ${PIPESTATUS[@]} ${BASH_REMATCH[@]}
OSH
echo $a[1] @a $PipeStatus @Match
OIL
}

# I think ! can raise an exception.  No named references or keys yet.
prefix-ops() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${#s} ${#a[@]}
OSH
echo $len(s) $len(a)
OIL
}

suffix-ops() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${s:-3}
echo ${s:-}
echo ${s:-''}
echo ${s:-""}
echo ${s##suffix}
OSH
echo $(s or '3')
echo $(s or '')
echo $(s or '')
echo $(s or "")
echo $s.trimRight('suffix')
OIL
}

slice() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${a:1:2} ${a[@]:1:2}
OSH
echo $a[1:3] @a[1:3]
OIL
}

# Replace is Python syntax for constants, and JavaScript syntax for
# constant/regex.
patsub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${s/foo/bar} ${s//foo/bar}
OSH
echo $s.replace('foo', 'bar') $s.replace('foo', 'bar', :ALL)
OIL
}

simple-command() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo hi
OSH
echo hi
OIL
}

line-breaks() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo one \
  two three \
  four
OSH
echo one \
  two three \
  four
OIL
}

bracket-builtin() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
[ ! -z "$foo" ] || die
OSH
test ! -z $foo || die
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
if [ "$foo" -eq 3 ]; then
  echo yes
fi
OSH
if test $foo -eq 3 {
  echo yes
}
OIL
}

builtins() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
. lib.sh
OSH
source lib.sh
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
[ -f lib.sh ] && . lib.sh
OSH
test -f lib.sh && source lib.sh
OIL

  # Runtime option is setoption. Compile time is at top of file, with :option
  # +errexit.  This aids compilation.
  # could also be "bashoption" for deprecated stuff.
  # Hm but this is the DEFAULT.
  osh0-oil3 << 'OSH' 3<< 'OIL'
set -o errexit
OSH
setoption +errexit
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo '\n'
echo -e '\n'
echo -e -n '\n'
OSH
echo '\\n'
echo '\n'
write '\n'
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
eval 'echo $?'
OSH
oshEval('echo $?')  # call into osh!
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
exec 1>&2  # stdout to stderr from now on
OSH
redir !1 > !2
OIL

  # TODO: Statically parseable [ invocations can be built in?
  # But not dynamic ones like [ foo $op bar ].
}


export-readonly() {
  # Dynamic export falls back on sh-builtin

  osh0-oil3 << 'OSH' 3<< 'OIL'
export "$@"
OSH
sh-builtin export @Argv
OIL

  # Separate definition and attribute?
  osh0-oil3 << 'OSH' 3<< 'OIL'
export FOO
export BAR=bar
OSH
setenv FOO
BAR = 'bar'
setenv BAR
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
readonly FOO
readonly BAR=bar
OSH
freeze FOO
BAR = 'bar'
OIL
}

redirect() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
cat >out.txt <in.txt
OSH
cat >out.txt <in.txt
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
cat >out.txt 2> err.txt
OSH
cat >out.txt !2 > err.txt
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "error message" >& 2 
OSH
echo "error message" > !2 
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "error message" 1>&2 
OSH
echo "error message" !1 > !2 
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
cat >${out} <${in}
OSH
cat >$(out) <$(in)
OIL
}

# TODO: Make this pass after fixing left-to-right LST invariant.  That is,
# SimpleCommand(..., cmd_part*)
redirect-position-matters() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
< input.txt cat >output.txt
OSH
< input.txt cat >output.txt
OIL
}

here-doc() {
  # DQ context
  osh0-oil3 << 'OSH' 3<< 'OIL'
  cat <<ONE
echo $hi ${varsub} $((1 + 2)) $(echo comsub)
ONE
OSH
  cat << """
echo $hi $(varsub) $shExpr('1 + 2') $[echo comsub]
"""
OIL

  # SQ context
  osh0-oil3 << 'OSH' 3<< 'OIL'
  cat <<'ONE'
single quoted
ONE
OSH
  cat << '''
single quoted
'''
OIL

  # <<- in DQ context
  osh0-oil3 << 'OSH' 3<< 'OIL'
	cat <<-ONE
	indented ${varsub} $((1 + 2))
	body $(echo comsub)
	ONE
OSH
	cat << """
indented $(varsub) $shExpr('1 + 2')
body $[echo comsub]
"""
OIL

  # <<- in SQ context
  osh0-oil3 << 'OSH' 3<< 'OIL'
	cat <<-'ONE'
	indented
	body
	ONE
OSH
	cat << '''
indented
body
'''
OIL

  return
  # Bug fix: the combination of an empty here doc and a redirect afterward.
  osh0-oil3 << 'OSH' 3<< 'OIL'
  cat <<EOF >expect
EOF
OSH
  cat << """ >expect
"""
OIL
}

here-string() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
cat <<< "double $foo"
cat <<< 'single'
OSH
cat << "double $foo"
cat << 'single'
OIL
}

more-env() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo 1
FOO=bar BAR=baz echo 2
echo 2
OSH
echo 1
env FOO=bar BAR=baz echo 2
echo 2
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
FOO="${bar}" BAR="$(echo hi)" echo 2
OSH
env FOO=$(bar) BAR=$[echo hi] echo 2
OIL
}

# NOTE: This is probably wrong
export-case() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
export foo=bar spam="${var}/const"
OSH
export foo=bar spam="$(var)/const"
OIL
}

# , and ; are similar.
assign() {
  # global variable.  Since we don't know if it's sourced, turn it into 
  # 'setglobal'.
  osh0-oil3 << 'OSH' 3<< 'OIL'
g=
g=x
OSH
setglobal g = ''
setglobal g = 'x'
OIL

  cat >/dev/null <<TODO_ENABLE
  # empty quoted words
  osh0-oil3 << 'OSH' 3<< 'OIL'
dq=""
OSH
setglobal dq = ""
OIL

  # empty quoted words
  osh0-oil3 << 'OSH' 3<< 'OIL'
sq=''
OSH
setglobal sq = ''
OIL
TODO_ENABLE

  # Local variable
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local foo=$(basename $1)
}
OSH
proc f {
  var foo = $[basename $1]
}
OIL

  # More than one local on a line
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local one=1 two three=3
}
OSH
proc f {
  var one = '1', two = '', three = '3'
}
OIL

  # local that is mutated
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local one=1 two
  one=x
  two=y
  g=z
}
OSH
proc f {
  var one = '1', two = ''
  set one = 'x'
  set two = 'y'
  setglobal g = 'z'
}
OIL

  # Top-level constant
  osh0-oil3 << 'OSH' 3<< 'OIL'
readonly myConstStr=two
OSH
const myConstStr = 'two'
OIL

  # Local constant
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local myStr=one
  readonly myConstStr=two
}
OSH
proc f {
  var myStr = 'one'
  const myConstStr = 'two'
}
OIL

  # NOTE: This could be shExpr() instead of $shExpr, but both are allowed.
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local myStr=$1
  readonly myConstStr=$((1 + 2))
}
OSH
proc f {
  var myStr = $1
  const myConstStr = $shExpr('1 + 2')
}
OIL
}

assign2() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
foo=bar spam="$var"
OSH
setglobal foo = 'bar', spam = $var
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
readonly foo=bar spam="${var}"
OSH
const foo = 'bar', spam = $(var)
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local foo=bar spam=eggs
  foo=mutated
  g=new
}
OSH
proc f {
  var foo = 'bar', spam = 'eggs'
  set foo = 'mutated'
  setglobal g = 'new'
}
OIL
  return

  # Inside function
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() { foo=bar spam=${var:-default}; }
OSH
proc f { setglobal foo = 'bar', spam = $(var or 'default'); }
OIL
}

assign-with-flags() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
declare -r foo=bar
OSH
const foo = 'bar'
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
declare -x foo=bar
OSH
export var foo = 'bar'
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
declare -rx foo
declare -r -x foo
OSH
export const foo
export const foo
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local -r foo=bar
}
OSH
proc f {
  const foo = 'bar'
}
OIL
}

# This isn't close to working.
assign-array() {
  return
  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local -a array
  array[x++]=1
}
OSH
proc f {
  var array = []
  set array[shExpr('x++')]=1
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
a[x++]=1
OSH
set a[shExpr('x++')]=1
OIL

}


array-literal() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
a=(1 2 3)
OSH
var a = [1 2 3]
OIL
}

pipeline() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
ls | sort | uniq -c | sort -n -r
OSH
ls | sort | uniq -c | sort -n -r
OIL

  # TODO: ! -> not --
  # PROBLEM: It applies to the entire pipeline?  Gah.
  # I guess you can keep it as a word?  It can't be a descriptor.
  # Or maybe !! ?
  # if !echo hi | wc {
  #
  # }
  #
  # Oh yeah this seems fine.
  # if not echo hi {
  # }
  # if not { echo hi | wc } {
  # }
  # PipeStatus

  return
  osh0-oil3 << 'OSH' 3<< 'OIL'
! echo hi | wc
OSH
not -- echo hi | wc
OIL
}

# 'set' is a keyword in Oil, so the multiple usages of 'set' builtin have to
# become something else.

builtin-set() {
  # option is a keyword like setglobal?  The RHS it optional; defaults to true?
  osh0-oil3 << 'OSH' 3<< 'OIL'
set -o nounset
set +o errexit
OSH
option nounset
option errexit = false
OIL

  # We could do:
  # setoption nounset = true, errexit = false

  # Accept old syntax too
  osh0-oil3 << 'OSH' 3<< 'OIL'
set -o nounset -o pipefail +o errexit
OSH
sh-builtin set -o nounset -o pipefail +o errexit
OIL

  # Mutating the arguments array is discouraged/deprecated in Oil.  Just 
  # make a new first-class array instead of mutating the existing one.
  osh0-oil3 << 'OSH' 3<< 'OIL'
set a b c
OSH
setargv a b c
OIL
}

and-or() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
ls && echo "$@" || die "foo"
OSH
ls && echo @Argv || die "foo"
OIL
}

posix-func() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
func1() {
  echo func1
  func2()
  {
    echo func2
  }
}
OSH
proc func1 {
  echo func1
  proc func2
  {
    echo func2
  }
}
OIL
}

subshell-func() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
subshell-func() (
  echo subshell
)
OSH
proc subshell-func {
  shell { 
    echo subshell
  }
}
OIL
}

ksh-func() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
function func1 {  # no parens
  echo func1
  function func2()
  {
    echo func2
  }
}
OSH
proc func1 {  # no parens
  echo func1
  proc func2
  {
    echo func2
  }
}
OIL
}

for-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x in a b c \
  d e f; do
  echo $x
done
OSH
for x in [a b c \
  d e f] {
  echo $x
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
for x in a b c \
  d e f
do
  echo $x
done
OSH
for x in [a b c \
  d e f]
{
  echo $x
}
OIL
}

empty-for-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x in 
do
  echo $x
done
OSH
for x in []
{
  echo $x
}
OIL
}

args-for-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x; do
  echo $x
done
OSH
for x in @Argv {
  echo $x
}
OIL

  # NOTE: we don't have the detailed spid info to preserve the brace style.
  # Leave it to the reformatter?
  return

#set -- 1 2 3
#setargv -- 1 2 3
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x
do
  echo $x
done
OSH
for x in @Argv
{
  echo $x
}
OIL
}

while-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
while read line; do
  echo $line
done
OSH
while read line {
  echo $line
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
while read \
  line; do
  echo $line
done
OSH
while read \
  line {
  echo $line
}
OIL
}

while-expr-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
x=0
while (( x < 3 )); do
  (( x++ ))
  echo $x
done
OSH
setglobal x = '0'
while sh-expr ' x < 3 ' {
  sh-expr ' x++ '
  echo $x
}
OIL
}

until-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
x=0
until  (( x == 3 )); do
  (( x++ ))
  echo $x
done
OSH
setglobal x = '0'
while not  sh-expr ' x == 3 ' {
  sh-expr ' x++ '
  echo $x
}
OIL
}

if_() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
if true; then
  echo yes
fi
OSH
if true {
  echo yes
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
if true
then
  echo yes
fi
OSH
if true
{
  echo yes
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
if true; then
  echo yes
elif false; then
  echo elif
elif spam; then
  echo elif
else
  echo no
fi
OSH
if true {
  echo yes
} elif false {
  echo elif
} elif spam {
  echo elif
} else {
  echo no
}
OIL
}

# TODO: This should match $foo with ...

case_() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
case $var in
  foo|bar)
    [ -f foo ] && echo file
    ;;
  '')
    echo empty
    ;;
  *)
    echo default
    ;;
esac
OSH
match $var {
  with foo|bar
    test -f foo && echo file
    
  with ''
    echo empty
    
  with *
    echo default
    
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
case "$var" in
  *)
    echo foo
    echo bar  # no dsemi
esac
OSH
match $var {
  with *
    echo foo
    echo bar  # no dsemi
}
OIL
}

subshell() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi;)
OSH
shell {echo hi;}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi)
OSH
shell {echo hi}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi; echo bye)
OSH
shell {echo hi; echo bye}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
( (echo hi; echo bye ) )
OSH
shell { shell {echo hi; echo bye } }
OIL
}

brace-group() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
{ echo hi; }
OSH
do { echo hi; }
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
{ echo hi; echo bye; }
OSH
do { echo hi; echo bye; }
OIL
}

# FAILING
fork() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
sleep 1&
OSH
fork sleep 1
OIL
}

# Downgraded to one_pass_parse.  This means \" will be wrong, but meh.
# Here the WordParser makes another pass with CommandParser.
#
# We could also translate it to:
#   echo $[compat backticks 'echo hi']
# But that might be overly pedantic.  This will work most of the time.

backticks() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo `echo hi ${var}`
OSH
echo $[echo hi $(var)]
OIL

  return
  # TODO: Not sure why this one is failing
  if false; then
    osh0-oil3 << 'OSH' 3<< 'OIL'
echo `{ echo hi; }`
OSH
echo $[do { echo hi }]
OIL
  fi

  # This also has problems
  osh0-oil3 << 'OSH' 3<< 'OIL'
  echo $({ echo hi; })
OSH
echo $[do { echo hi }]
OIL
}

# Uses one_pass_parse
lhs-assignment() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
foo=bar
a[x+1]=bar
OSH
setglobal foo = 'bar'
compat array-assign a 'x+1' 'bar'
OIL
}

var-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $foo
OSH
echo $foo
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $foo ${bar} "__${bar}__"
OSH
echo $foo $(bar) "__$(bar)__"
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${foo:-default}
OSH
echo $(foo or 'default')
OIL
}

command-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $(echo hi)
OSH
echo $[echo hi]
OIL

  # In double quotes
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "__$(echo hi)__"
OSH
echo "__$[echo hi]__"
OIL
}

proc-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo <(echo hi) >(echo hi)
OSH
echo $<[echo hi] $>[echo hi]
OIL
}

dparen() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
(( n++ ))
echo done
OSH
sh-expr ' n++ '
echo done
OIL
}

arith-sub() {
  # NOTE: This probably needs double quotes?
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo __$((  1+ 2 ))__
OSH
echo __$shExpr('  1+ 2 ')__
OIL
  return

  # Non-standard Bash style
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $[  1+ 2 ]
OSH
echo $(  1+ 2 )
OIL
}

arith-ops() {
  # Operations that change:
  # - ** to ^
  # - ternary to Python style
  # - / % to div mod
  # - bitwise operators:  .& .| .^  .  I think complement is still ~.

  # Precedence also changes, like bitwise operators

  # Not sure about ++i and i++.  Maybe support them only in bash mode.

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $(( a > 0 ? 2**3 : 3/2 ))
OSH
echo $(( 2^3 if a > 0 else 3 div 2 ))
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $(( a << 1 | b & 1 ))
OSH
echo $(( a << 1 .| b .& 1 ))
OIL
}

dbracket-pattern() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
if [[ $foo == *.py ]]; then
  echo Python
fi
OSH
if (foo ~ *.py) {
  echo Python
}
OIL

  # Negated match
  osh0-oil3 << 'OSH' 3<< 'OIL'
if [[ $foo != *.py ]]; then
  echo Python
fi
OSH
if (foo !~ *.py) {
  echo Python
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
regex='.*\.py'
if [[ $foo =~ $regex ]]; then
  echo Python
fi
OSH
setglobal regex = '.*\.py'
if (foo ~ ERE/$regex/) {
  echo Python
}
OIL
}

# Honestly test -dir /  is OK?
#
# What about newerThan, olderThan, etc.

dbracket() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
[[ -d / ]] && echo "is dir"
OSH
isDir('/') && echo "is dir"
OIL
}

escaped-literal() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo \$  \  \n "\$" "\n"
OSH
echo '$'  ' ' 'n' "\$" "\n"
OIL

  return
  # TODO: Have to combine adjacent escaped literals
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo \$\ \$
OSH
echo '$ $'
OIL

  # Make sure we don't mess up the backslash
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo \
  hi
OSH
echo \
  hi
OIL
}

# Hm I still don't have a syntax for this.  I don't like $'' because it's
# confusing with a var.  Use some other punctuation charater like %?
# @'' and @"" ?  &''  &"" ?
#
# Or get rid of word joining?   'foo'"'" becomes c'foo\''
# Glob/*.py/
# C'foo'
# List [1, 2, 'hi']  # JSON
#
# Yeah maybe capital C is better.

c-literal() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $'\tline\n'
OSH
echo c'\tline\n'
OIL
}

words() {
  # I probably should drive this with specific cases, rather than making it
  # super general.  Most scripts don't use WordPart juxtaposition.
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo foo'bar'
echo foo'bar'$baz
OSH
echo 'foobar'
echo "foobar$baz"
OIL

  # Avoiding WordPart joining.
  # Need specific use cases too
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ~/'name with spaces'
OSH
echo "$HOME/name with spaces"
OIL
}

word-joining() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo 'foo'"'" 
OSH
echo c'foo\''
OIL
}

time-block() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
time ls
OSH
time ls
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
time while false; do
  echo $i
done
OSH
time while false {
  echo $i
}
OIL

  return
  # TODO: The "do" has to be removed
  osh0-oil3 << 'OSH' 3<< 'OIL'
time {
  echo one
  echo two
}
OSH
time {
  echo one
  echo two
}
OIL
}

readonly -a PASSING=(
  simple-command
  #assign
  #assign2
  more-env
  line-breaks
  redirect
  here-doc
  pipeline
  and-or
  dparen
  #fork

  # Word stuff
  escaped-literal
  args-vars
  unquote-subs

  # Substitutions
  command-sub
  arith-sub
  unquote-subs

  posix-func
  ksh-func

  # Require --one-pass-parse
  backticks
  lhs-assignment

  # Compound commands
  brace-group
  subshell
  while-loop
  while-expr-loop
  until-loop
  if_
  case_
  for-loop
  empty-for-loop
  args-for-loop
  time-block

  # Builtins
  bracket-builtin
)

list-all-tests() {
  egrep '^[a-z0-9_\-]+\(\) {' $0
}

all-passing() {
  run-all "${PASSING[@]}"
}

run-for-release() {
  run-other-suite-for-release osh2oil all-passing
}

"$@"
