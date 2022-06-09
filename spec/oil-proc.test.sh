# Oil Functions

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

#### Proc with explicit args
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

#### Proc with varargs

# TODO: opts goes with this
# var opt = grep_opts.parse(ARGV)
#
# func(**opt)  # Assumes keyword args match?
# parse :grep_opts :opt @ARGV

shopt -s oil:all

proc f(@names) {
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

#### varargs 2
shopt -s oil:all

proc f(first, @rest) {  # @ means "the rest of the arguments"
  write --sep ' ' -- $first
  write --sep ' ' -- @rest        # @ means "splice this array"
}
f a b c
## STDOUT:
a
b c
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
proc f(x, y, block Block) {
  echo F
}
f a b

# With varargs and block
shopt --set parse_proc

proc g(x, y, @rest, block Block) {
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
## status: 1
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

proc f(input, :out) {  # : means accept a string "reference"
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
shopt --set redefine_proc

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


#### Proc with untyped* args

shopt -s oil:all

proc f(foo, bar) {
  write params $foo $bar
}
f a b
## STDOUT:
params
a
b
## END


#### Proc with untyped* rest? args

shopt -s oil:all

proc f(foo, bar, @rest) {
  write --sep ' ' -- $foo
  write --sep ' ' -- $bar
  write --sep ' ' -- @rest        # @ means "splice this array"
}
f a b c
## STDOUT:
a
b
c
## END


#### Proc with untyped* rest? typed* rest? args

shopt -s oil:all

proc f(foo, @rest, bar, @rest) {
}
f a b c d e
echo status=$?
## status: 2
## stdout-json: ""
## OK mksh status: 1


#### Proc with untyped* rest? typed* args

shopt -s oil:all

proc p(foo, bar, @rest, b) {
  echo hi
}
p a b c d
## STDOUT:
hi
## END


#### Proc with untyped* rest? typed* rest? args

shopt -s oil:all

proc p(foo, bar, @rest, @rest2, b Block) {
}
f a b c d e
echo status=$?
## status: 2
## stdout-json: ""
## OK mksh status: 1