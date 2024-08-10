# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 1

#### Eval does not take a literal block - can restore this later

var b = ^(echo obj)
eval (b)

eval (^(echo command literal))

# Doesn't work because it's a positional arg
eval { echo block }

## status: 3
## STDOUT:
obj
command literal
## END


#### Eval a block within a proc
proc run (;;; block) {
  eval (block)
}

run {
  echo 'In a block!'
}
## STDOUT:
In a block!
## END

#### Eval block created by calling a proc
proc lazy-block ( ; out; ; block) {
  call out->setValue(block)
}

var myglobal = 0

lazy-block (&my_block) {
  json write (myglobal)
}

eval (my_block)
setvar myglobal = 1
eval (my_block)
## STDOUT:
0
1
## END

#### eval (block) can read variables like eval ''

proc p2(code_str) {
  var mylocal = 42
  eval $code_str
}

p2 'echo mylocal=$mylocal'

proc p (;;; block) {
  var mylocal = 99
  eval (block)
}

p {
  echo mylocal=$mylocal
}


## STDOUT:
mylocal=42
mylocal=99
## END

#### eval should have a sandboxed mode

proc p (;;; block) {
  var this = 42

  # like push-registers?  Not sure
  # We could use state.ctx_Temp ?  There's also ctx_FuncCall etc.
  #
  # I think we want to provide full control over the stack.
  push-frame {
    eval (block)
  }
}

p {
  echo $this
}

## status: 1
## STDOUT:
TODO
## END

#### eval with argv bindings
eval (^(echo "$@"), pos_args=:| foo bar baz |)
eval (^(pp test_ (:| $1 $2 $3 |)), pos_args=:| foo bar baz |)
## STDOUT:
foo bar baz
(List)   ["foo","bar","baz"]
## END

#### eval lines with argv bindings
proc my-split (;;; block) {
  while read --raw-line {
    var cols = _reply => split()
    eval (block, pos_args=cols)
  }
}

printf 'a b\nc d\n' | my-split {
  echo "$2 $1"
}

printf 'a b\nc d\n' | my-split {
  var mylocal = 'mylocal'
  echo "$2 $1 $mylocal"
}

# Now do the same thing inside a proc
proc p {
  printf 'a b\nc d\n' | my-split {
    var local2 = 'local2'
    echo "$2 $1 $local2"
  }
}

echo
p

## STDOUT:
b a
d c
b a mylocal
d c mylocal

b a local2
d c local2
## END

#### eval lines with var bindings

proc my-split (;;; block) {
  while read --raw-line {
    var cols = _reply => split()
    eval (block, vars={_line: _reply, _first: cols[0]})
  }
}

printf 'a b\nc d\n' | my-split {
  var mylocal = 'mylocal'
  echo "$_line | $_first $mylocal"
}

# Now do the same thing inside a proc
proc p {
  printf 'a b\nc d\n' | my-split {
    var local2 = 'local2'
    echo "$_line | $_first $local2"
  }
}

echo
p

## STDOUT:
a b | a mylocal
c d | c mylocal

a b | a local2
c d | c local2
## END

#### eval with custom dollar0
var b = ^(write $0)
eval (b, dollar0="my arg0")
## STDOUT:
my arg0
## END

#### eval with vars bindings
var myVar = "abc"
eval (^(pp test_ (myVar)))
eval (^(pp test_ (myVar)), vars={ 'myVar': '123' })

# eval doesn't modify it's environment
eval (^(pp test_ (myVar)))

## STDOUT:
(Str)   "abc"
(Str)   "123"
(Str)   "abc"
## END

#### dynamic binding names and mutation
proc foreach (binding, in_; list ;; block) {
  if (in_ !== "in") {
    error 'Must use the "syntax" `foreach <binding> in (<expr>) { ... }`'
  }

  for item in (list) {
    eval (block, vars={ [binding]: item })
  }
}

var mydicts = [{'a': 1}, {'b': 2}, {'c': 3}]
foreach mydict in (mydicts) {
  var mylocal = 'z'
  setvar mydict.z = mylocal

  pp test_ (mydict)
  setvar mydict.d = 0
}
echo

for d in (mydicts) {
  pp test_ (d)
}

## STDOUT:
(Dict)   {"a":1,"z":"z"}
(Dict)   {"b":2,"z":"z"}
(Dict)   {"c":3,"z":"z"}

(Dict)   {"a":1,"z":"z","d":0}
(Dict)   {"b":2,"z":"z","d":0}
(Dict)   {"c":3,"z":"z","d":0}
## END

#### binding procs in the eval-ed namespace
proc __flag (short, long) {
  echo "flag $short $long"
}

proc __arg (name) {
  echo "arg $name"
}

proc parser (; spec ;; block) {
  eval (block, vars={ 'flag': __flag, 'arg': __arg })
}

parser (&spec) {
  flag -h --help
  arg file
}

# but flag/arg are unavailable outside of `parser`
# _error.code = 127 is set on "command not found" errors

try { flag }
if (_error.code !== 127) { error 'expected failure' }

try { arg }
if (_error.code !== 127) { error 'expected failure' }

## STDOUT:
flag -h --help
arg file
## END

#### vars initializes the variable frame, but does not remember it
var vars = { 'foo': 123 }
eval (^(var bar = 321;), vars=vars)
pp test_ (vars)

## STDOUT:
(Dict)   {"foo":123}
## END

#### eval pos_args must be strings
eval (^(true), pos_args=[1, 2, 3])
## status: 3

#### eval with vars follows same scoping as without
proc local-scope {
  var myVar = "foo"
  eval (^(echo $myVar), vars={ someOtherVar: "bar" })
  eval (^(echo $myVar))
}

# In global scope
var myVar = "baz"
eval (^(echo $myVar), vars={ someOtherVar: "bar" })
eval (^(echo $myVar))

local-scope
## STDOUT:
baz
baz
foo
foo
## END

#### eval 'mystring' vs. eval (myblock)

eval 'echo plain'
echo plain=$?
var b = ^(echo plain)
eval (b)
echo plain=$?

echo

# This calls main_loop.Batch(), which catches
# - error.Parse
# - error.ErrExit
# - error.FatalRuntime - glob errors, etc.?

try {
  eval 'echo one; false; echo two'
}
pp test_ (_error)

# This calls CommandEvaluator.EvalCommand(), as blocks do

var b = ^(echo one; false; echo two)
try {
  eval (b)
}
pp test_ (_error)

## STDOUT:
plain
plain=0
plain
plain=0

one
(Dict)   {"code":1}
one
(Dict)   {"code":1}
## END
