#!/usr/bin/env bash
#
# Usage:
#   ./osh-to-oil-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

osh-to-oil() {
  $OSH --fix "$@"
}

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
osh0-oil3() {
  osh-to-oil "$@" | diff -u /dev/fd/3 - || fail
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
  # "__$@__" goes "$join(Argv)__"
  # Yeah the rest go to $join(Argv)
  # does join respect IFS though?  Have to work that out.
  # or maybe $ifsjoin(Argv) -- make explicit the global variable.

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $@ $* "$@" "$*" "__$@__" "__$*__"
OSH
echo $Status $len(Argv) @Argv
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
echo ${s:-3} ${s##suffix}
OSH
echo $(s or 3) $s.trimRight('suffix')
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

here-doc() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
cat <<ONE
echo $hi
ONE
OSH
cat << """
echo $hi
"""
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
cat <<'ONE'
single quoted
ONE
OSH
cat << '''
single quoted
'''
OIL

  # TODO: <<-
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

assign-common() {
  # top level
  osh-to-oil --fix -c 'foo=bar spam="$var"'
  osh-to-oil --fix -c 'readonly foo=bar spam="${var}"'
  osh-to-oil --fix -c 'export foo=bar spam="${var}/const"'

  # Inside function
  osh-to-oil --fix -c 'f() { foo=bar spam=${var:-default}; }'
  osh-to-oil --fix -c 'f() { local foo=bar spam=eggs; foo=mutated; g=new; }'

  # TODO:
  # - Test everything without a RHS.  export and readonly
  # - Print RHS as expression
  # - declare -- but this is more rare.  declare is usually 'var'.
}

# , and ; are similar.
assign() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
local foo=$(basename $1)
OSH
var foo = $[basename $1]
OIL
  return


  osh0-oil3 << 'OSH' 3<< 'OIL'
local one=1 two three=3
OSH
one = '1', two = '', three = '3'
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
myStr=one
readonly myConstStr=two
OSH
var myStr = 'hi'
myConstStr = 'hi'
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local myStr=one
  readonly myConstStr=two
}
OSH
proc f {
  var myStr = 'hi'
  myConstStr = 'hi'
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
f() {
  local myStr=$1
  readonly myConstStr=$((1 + 2))
}
OSH
proc f {
  var myStr = $1
  myConstStr = $(1 + 2)
}
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

case_() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
case $var in
  foo|bar)
    [ -f foo ] && echo file
    ;;
  *)
    echo default
    ;;
esac
OSH
matchstr $var {
  foo|bar {
    test -f foo && echo file
    }
  * {
    echo default
    }
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
case "$var" in
  *)
    echo foo
    echo bar  # no dsemi
esac
OSH
matchstr $var {
  * {
    echo foo
    echo bar  # no dsemi
    }
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

fork() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
sleep 1&
OSH
fork sleep 1
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
echo `echo hi`
OSH
echo $[echo hi]
echo $[echo hi]
OIL

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

arith-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo __$((  1+ 2 ))__
OSH
echo __$(  1+ 2 )__
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

# newerThan, olderThan, etc.
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
  more-env
  line-breaks
  redirect
  pipeline
  and-or

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

  # Compound commands
  brace-group
  subshell
  while-loop
  if_
  case_
  for-loop
  empty-for-loop
  args-for-loop
  time-block

  # Builtins
  bracket-builtin
)

all-passing() {
  run-all "${PASSING[@]}"
}

run-for-release() {
  local out_dir=_tmp/osh2oil
  mkdir -p $out_dir

  all-passing | tee $out_dir/log.txt

  echo "Wrote $out_dir/log.txt"
}

"$@"
