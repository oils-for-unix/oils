#!/bin/bash
#
# Usage:
#   ./osh-to-oil-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit


osh-to-oil() {
  bin/osh --no-exec --fix "$@"
}

fail() {
  echo 'TEST FAILED'
  exit 1
}

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
osh0-oil3() {
  osh-to-oil "$@" | diff -u /dev/fd/3 - || fail
}

special-vars() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $? $# $@
OSH
echo $Status $len(Argv) @Argv
OIL

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

builtins() {
  # Runtime option is setoption. Compile time is at top of file, with :option
  # +errexit.  This aids compilation.
  # could also be "bashoption" for deprecated stuff.
  osh0-oil3 << 'OSH' 3<< 'OIL'
set -o errexit
OSH
setoption +errexit
OIL
  # Could also be OPT['errexit'] = F.  I think that is too low level.

  osh0-oil3 << 'OSH' 3<< 'OIL'
. lib.sh
OSH
source lib.sh
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

  # TODO: Statically parseable [ invocations can be built in?
  # But not dynamic ones like [ foo $op bar ].
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
}

# , and ; are similar.
assign() {
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
ls && echo || die "foo"
OSH
ls && echo || die "foo"
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
}

if_() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
if true; then
  echo yes
elif false; then
  echo elif
else
  echo no
fi
OSH
if true {
  echo yes
} elif false {
  echo elif
} else {
  echo no
}
OIL
}

case_() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
case var in
  foo|bar)
    echo foobar
    ;;
  *)
    echo default
    ;;
esac
OSH
match var {
  'foo' or 'bar' {
    echo foobar
  }
  * {
    echo default
  }
}
OIL
}

subshell() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi)
done
OSH
shell {echo hi}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi; echo bye)
done
OSH
shell {echo hi; echo bye}
OIL
}

fork() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
sleep 1&
OSH
fork sleep 1
OIL
}

empty-for-loop() {
  for x in 
  do
    echo $x
  done
}

args-for-loop() {
  set -- 1 2 3
  for x
  do
    echo $x
  done
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

all-passing() {
  simple-command
  redirect
  pipeline
  and-or
  posix-func
  ksh-func
  command-sub
  arith-sub
}

"$@"
