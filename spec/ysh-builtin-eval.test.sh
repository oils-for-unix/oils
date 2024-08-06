# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 8

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
eval (^(echo "$@")) (pos_args=:| foo bar baz |)
eval (^(pp test_ (:| $1 $2 $3 |))) (pos_args=:| foo bar baz |)
## STDOUT:
foo bar baz
(List)   ["foo","bar","baz"]
## END

#### eval lines with argv bindings
proc lines (;;; block) {
  while read --line {
    var cols = _reply => split()
    eval (block, pos_args=cols)
  }
}

printf 'a b\nc d' | lines { echo $1 }

## STDOUT:
a
c
## END

#### eval with custom arg0
eval (^(write $0)) (arg0="my arg0")
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
abc
123
## END

#### dynamic binding names and mutation
proc foreach (binding, in_; list ;; block) {
  if (in_ !== "in") {
    error 'Must use the "syntax" `foreach <binding> in (<expr>) { ... }`'
  }

  for _ in (list) {
    eval (block, vars={ binding: _ })
  }
}

var mydicts = [{'a': 1}, {'b': 2}, {'c': 3}]
foreach mydict in (mydicts) {
  pp test_ (mydict)
  setvar mydict.d = 0
}

pp test_ (mydicts)

## STDOUT:
(Dict)   {"a":1}
(Dict)   {"b":2}
(Dict)   {"c":3}
(List)   [{"a":1,"d":0},{"b":2,"d":0},{"c":3,"d":0}]
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
eval (^(var bar = 321), vars=vars)
pp test_ (vars)

## STDOUT:
(Dict)   {"foo":123}
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
