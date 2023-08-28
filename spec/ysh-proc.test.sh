## oils_failures_allowed: 1

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

f a b
echo status=$?  # status 2 because it's a usage error

## STDOUT:
status=42
status=2
## END

#### Open proc has "$@"
shopt -s oil:all
proc foo { 
  write ARGV "$@"
}
builtin set -- a b c
foo x y z
## STDOUT:
ARGV
x
y
z
## END

#### Closed proc doesn't have "$@"
shopt -s oil:all
proc foo(d, e, f) { 
  write params $d $e $f
  write ARGV "$@"
}
builtin set -- a b c
foo x y z
## STDOUT:
params
x
y
z
ARGV
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

# doesn't require oil:all
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

shopt -s oil:all

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

# TODO: default args can only be mutable

proc p (a; mylist, mydict; a Int = 3) {
  json write (mylist)
  json write (mydict)
  json write (a)
}

p WORD ([1,2,3], {name: 'bob'})

p a (:| a b |, {bob}, a = 5)

## STDOUT:
[1, 2, 3]
## END


#### Proc name-with-hyphen
shopt --set parse_proc

proc name-with-hyphen {
  echo "$@"
}
name-with-hyphen x y z
## STDOUT:
x y z
## END

#### Proc with block arg
shopt --set parse_proc

# TODO: Test more of this
proc f(x, y; block) {
  echo F
}
f a b

# With varargs and block
shopt --set parse_proc

proc g(x, y, ...rest; block) {
  echo G
}
g a b c d
## STDOUT:
F
G
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

#### Out param / setref
shopt --set parse_proc

proc f(input, out Ref) {  # : means accept a string "reference"
  #pp cell __out
  setref out = "PREFIX-$input"
}

var myvar = 'value'
echo myvar=$myvar
f zzz :myvar   # : means that it's the name of a variable
echo myvar=$myvar

## STDOUT:
myvar=value
myvar=PREFIX-zzz
## END

#### Pass out param through 2 levels of proc

shopt --set parse_proc

proc p(s, out Ref) {
  setref out = "PREFIX-$s"  # only goes up ONE level
}

proc p2(s, out Ref) {
  # SILLY MANUAL idiom, because setref only looks up one level (scope_e.Parent)

  var tmp = null  # can be null
  p $s :tmp
  setref out = tmp

  # TODO: test 
  #   p (s, :tmp) 
  #   p (s, 'tmp')
  #
  # I think there's no reason they shouldn't work
  # You strip : in command mode, but in expr mode it's a string

  echo tmp=$tmp
}

var top = 'top'
p2 zzz :top
echo top=$top

## STDOUT:
tmp=PREFIX-zzz
top=PREFIX-zzz
## END


#### 'return' doesn't accept expressions
proc p {
  return 1 + 2
}
p
## status: 2
## STDOUT:
## END

#### procs are in same namespace as shell functions
shopt --set parse_proc

myfunc() {
  echo hi
}

proc myproc {
  echo hi
}

declare -F
## STDOUT:
declare -f myfunc
declare -f myproc
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

shopt --set oil:upgrade
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

