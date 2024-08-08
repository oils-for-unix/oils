## oils_failures_allowed: 0

#### Open proc (any number of args)
shopt --set parse_proc

proc f {
  var x = 42
  return $x
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
status=42
## END

#### Closed proc with no args, passed too many
shopt --set parse_proc

proc f() {
  return 42
}
f
echo status=$?

f a b  # status 2

## status: 3
## STDOUT:
status=42
## END

#### Open proc has ARGV
shopt -s ysh:all
proc foo { 
  echo ARGV @ARGV
  # do we care about this?  I think we want to syntactically remove it from YSH
  # but it can still be used for legacy
  echo dollar-at "$@"
}
builtin set -- a b c
foo x y z
## STDOUT:
ARGV x y z
dollar-at a b c
## END

#### Closed proc has empty "$@" or ARGV
shopt -s ysh:all

proc foo(d, e, f) { 
  write params $d $e $f
  argv.py dollar-at "$@"
  argv.py ARGV @ARGV
}
builtin set -- a b c
foo x y z
## STDOUT:
params
x
y
z
['dollar-at', 'a', 'b', 'c']
['ARGV']
## END

#### Proc with default args
shopt --set parse_proc

proc f(x='foo') {
  echo x=$x
}
f
## STDOUT:
x=foo
## END

#### Proc with word params
shopt --set parse_proc

# doesn't require ysh:all
proc f(x, y, z) {
  echo $x $y $z
  var ret = 42
  return $ret
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
a b c
status=42
## END

#### Proc with ... "rest" word params 

# TODO: opts goes with this
# var opt = grep_opts.parse(ARGV)
#
# func(**opt)  # Assumes keyword args match?
# parse :grep_opts :opt @ARGV

shopt -s ysh:all

proc f(...names) {
  write names: @names
}
# this gets called with 3 args then?
f a b c
echo status=$?
## STDOUT:
names:
a
b
c
status=0
## END

#### word rest params 2
shopt --set ysh:all

proc f(first, ...rest) {  # @ means "the rest of the arguments"
  write --sep ' ' -- $first
  write --sep ' ' -- @rest        # @ means "splice this array"
}
f a b c
## STDOUT:
a
b c
## END

#### proc with typed args
shopt --set ysh:upgrade

# TODO: duplicate param names aren't allowed
proc p (a; mylist, mydict; opt Int = 42) {
  pp test_ (a)
  pp test_ (mylist)
  pp test_ (mydict)
  #pp test_ (opt)
}

p WORD ([1,2,3], {name: 'bob'})

echo ---

p x (:| a b |, {bob: 42}, a = 5)

## STDOUT:
(Str)   "WORD"
(List)   [1,2,3]
(Dict)   {"name":"bob"}
---
(Str)   "x"
(List)   ["a","b"]
(Dict)   {"bob":42}
## END

#### Proc name-with-hyphen
shopt --set parse_proc parse_at

proc name-with-hyphen {
  echo @ARGV
}
name-with-hyphen x y z
## STDOUT:
x y z
## END

#### Proc with block arg
shopt --set ysh:upgrade

# TODO: Test more of this
proc f(x, y ; ; ; block) {
  echo f word $x $y

  if (block) {
    eval (block)
  }
}
f a b { echo FFF }

# With varargs and block
shopt --set parse_proc

proc g(x, y, ...rest ; ; ; block) {
  echo g word $x $y
  echo g rest @rest

  if (block) {
    eval (block)
  }
}
g a b c d {
  echo GGG
}

## STDOUT:
f word a b
FFF
g word a b
g rest c d
GGG
## END

#### proc returning wrong type
shopt --set parse_proc

# this should print an error message
proc f {
  var a = %(one two)
  return $a
}
f
## status: 3
## STDOUT:
## END

#### proc returning invalid string
shopt --set parse_proc

# this should print an error message
proc f {
  var s = 'not an integer status'
  return $s
}
f
## status: 1
## STDOUT:
## END

#### 'return' doesn't accept expressions
proc p {
  return 1 + 2
}
p
## status: 2
## STDOUT:
## END

#### declare -F prints procs and shell-funcs
shopt --set parse_proc

myfunc() {
  echo hi
}

proc myproc {
  echo hi
}

declare -F

## status: 0
## STDOUT:
declare -f myfunc
declare -f myproc
## END

#### procs are in same namespace as variables
shopt --set parse_proc

proc myproc {
  echo hi
}

echo "myproc is a $[type(myproc)]"

## STDOUT:
myproc is a Proc
## END

#### Nested proc is disallowed at parse time
shopt --set parse_proc

# NOTE: we can disallow this in Oil statically ...
proc f {
  proc g {
    echo 'G'
  }
  g
}
f
g
## status: 2
## stdout-json: ""

#### Procs defined inside compound statements (with redefine_proc)

shopt --set ysh:upgrade
shopt --set redefine_proc_func

for x in 1 2 {
  proc p {
    echo 'loop'
  }
}
p

{
  proc p {
    echo 'brace'
  }
}
p

## STDOUT:
loop
brace
## END

#### Block can be passed literally, or as expression in third arg group
shopt --set ysh:upgrade

proc p ( ; ; ; block) {
  eval (block)
}

p { echo literal }

var block = ^(echo expression)
p (; ; block)

## STDOUT:
literal
expression
## END

#### Pass through all 4 kinds of args

shopt --set ysh:upgrade

proc p2 (...words; ...typed; ...named; block) {
  pp test_ (words)
  pp test_ (typed)
  pp test_ (named)
  #pp test_ (block)
  # To avoid <Block 0x??> - could change pp test_
  echo $[type(block)]
}

proc p1 (...words; ...typed; ...named; block) {
  p2 @words (...typed; ...named; block)
}

p2 a b ('c', 'd', n=99) {
  echo literal
}
echo

# Same thing
var block = ^(echo expression)

# Note: you need the second explicit ;

p2 a b ('c', 'd'; n=99; block)
echo

# what happens when you do this?
p2 a b ('c', 'd'; n=99; block) {
  echo duplicate
}

## status: 1
## STDOUT:
(List)   ["a","b"]
(List)   ["c","d"]
(Dict)   {"n":99}
Block

(List)   ["a","b"]
(List)   ["c","d"]
(Dict)   {"n":99}
Command

## END

#### Global and local ARGV, like "$@"
shopt -s parse_at
argv.py "$@"
argv.py @ARGV
#argv.py "${ARGV[@]}"  # not useful, but it works!

set -- 'a b' c
argv.py "$@"
argv.py @ARGV  # separate from the argv stack

f() {
  argv.py "$@"
  argv.py @ARGV  # separate from the argv stack
}
f 1 '2 3'
## STDOUT:
[]
[]
['a b', 'c']
[]
['1', '2 3']
[]
## END


#### Mutating global ARGV

$SH -c '
shopt -s ysh:upgrade

argv.py global @ARGV

# should not be ignored
call ARGV->append("GG")

argv.py global @ARGV
'
## STDOUT:
['global']
['global', 'GG']
## END

#### Mutating local ARGV

$SH -c '
shopt -s ysh:upgrade

argv.py global @ARGV

proc p {
  argv.py @ARGV
  call ARGV->append("LL")
  argv.py @ARGV
}

p local @ARGV

argv.py global @ARGV

' dummy0 'a b' c

## STDOUT:
['global', 'a b', 'c']
['local', 'a b', 'c']
['local', 'a b', 'c', 'LL']
['global', 'a b', 'c']
## END


#### typed proc allows all kinds of args
shopt -s ysh:upgrade

typed proc p (w; t; n; block) {
  pp test_ (w)
  pp test_ (t)
  pp test_ (n)
  echo $[type(block)]
}

p word (42, n=99) {
  echo block
}


## STDOUT:
(Str)   "word"
(Int)   42
(Int)   99
Block
## END

#### can unset procs without -f
shopt -s ysh:upgrade

proc foo() {
  echo bar
}

try { foo }
echo status=$[_error.code]

# TODO: should we abandon declare -F in favour of `pp proc`?
declare -F
unset foo
declare -F

try { foo }
echo status=$[_error.code]

## STDOUT:
bar
status=0
declare -f foo
status=127
## END

#### procs shadow sh-funcs
shopt -s ysh:upgrade redefine_proc_func

f() {
  echo sh-func
}

proc f {
  echo proc
}

f
## STDOUT:
proc
## END

#### first word skips non-proc variables
shopt -s ysh:upgrade

grep() {
  echo 'sh-func grep'
}

var grep = 'variable grep'

grep

# We first find `var grep`, but it's a Str not a Proc, so we skip it and then
# find `function grep`.

## STDOUT:
sh-func grep
## END

#### proc resolution changes with the local scope
shopt -s ysh:upgrade

proc foo {
  echo foo
}

proc bar {
  echo bar
}

proc inner {
  var foo = bar
  foo  # Will now reference `proc bar`
}

foo
inner
foo  # Back to the global scope, foo still references `proc foo`

# Without this behavior, features like `eval(b, vars={ flag: __flag })`, needed
# by parseArgs, will not work. `eval` with `vars` adds a new frame to the end of
# `mem.var_stack` with a local `flag` set to `proc __flag`. However, then we
# cannot resolve `flag` by only checking `mem.var_stack[0]` like we could with
# a proc declared normally, so we must search `mem.var_stack` from last to first.

## STDOUT:
foo
bar
foo
## END
