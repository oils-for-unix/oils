# YSH specific features of eval

## our_shell: ysh
## oils_failures_allowed: 6

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
eval ^[echo "$@"] (argv=:| foo bar baz |)
eval ^[pp line (:| $1 $2 $3 |)] (argv=:| foo bar baz |)

## status: 0
## STDOUT:
foo bar baz
(List)   ["foo","bar","baz"]
## END

#### eval with vars bindings
var myVar = "abc"
eval (^(pp line (myVar)))
eval (^(pp line (myVar)), vars={ 'myVar': '123' })

# eval doesn't modify it's environment
eval (^(pp line (myVar)))

## status: 0
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
  pp line (mydict)
  setvar mydict.d = 0
}

pp line (mydicts)

## status: 0
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

## status: 0
## STDOUT:
flag -h --help
arg file
## END

#### vars initializes the variable frame, but does not remember it
var vars = { 'foo': 123 }
eval (^(var bar = 321), vars=vars)
pp line (vars)

## status: 0
## STDOUT:
(Dict)   {"foo":123}
## END
