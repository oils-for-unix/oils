# Oil Functions

#### Open proc (any number of args)
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
proc f() {
  return 42
}
f
echo status=$?

# TODO: This should abort, or have status 1
f a b
echo status=$?

## status: 1
## STDOUT:
status=42
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
proc f(x='foo') {
  echo x=$x
}
f
## STDOUT:
x=foo
## END

#### Proc with explicit args

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
  write -sep ' ' -- $first
  write -sep ' ' -- @rest        # @ means "splice this array"
}
f a b c
## STDOUT:
a
b c
## END

#### Proc name-with-hyphen
proc name-with-hyphen {
  echo "$@"
}
name-with-hyphen x y z
## STDOUT:
x y z
## END

#### Proc with block arg

# TODO: Test more of this
proc f(x, y, &block) {
  echo F
}
f a b

# With varargs and block
proc g(x, y, @rest, &block) {
  echo G
}
g a b c d
## STDOUT:
F
G
## END

#### proc returning wrong type

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

# TODO: Implement the :out syntax, and setref, using the nameref flag

proc f(input, :out) {  # : means accept a string "reference"
  setref out = "PREFIX-$in"
}

var myvar = 'zzz'
f zzz :myvar        # : means pass a string "reference" (optional)
echo myvar=$myvar

## STDOUT:
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
