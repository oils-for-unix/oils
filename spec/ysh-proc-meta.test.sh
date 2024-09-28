## oils_failures_allowed: 1
## our_shell: ysh

# dynamically generate procs

#### with eval builtin command, in global scope

for param in a b {
  eval """
  proc echo_$param(prefix) {
    echo \$prefix $param
  }
  """
}

echo_a prefix
echo_b prefix

## STDOUT:
prefix a
prefix b
## END

#### with eval builtin command, in local scope

proc p {
  for param in a b {
    eval """
    proc echo_$param(prefix) {
      echo \$prefix $param
    }
    """
  }

  echo_a prefix
  echo_b prefix
}

p

echo_a prefix  # not available here!

## status: 127
## STDOUT:
prefix a
prefix b
## END

#### with eval builtin command, making them global with names() and setVar()

func genProcs() {
  var result = {}
  for param in a b {
    eval """
    proc echo_$param(prefix) {
      echo \$prefix $param
    }
    """
    setvar result["echo_$param"] = getVar("echo_$param")
  }

  echo 'local'
  echo_a prefix
  echo_b prefix
  echo

  return (result)
}

var procs = genProcs()

# bind to global scope
for name in (procs) {
  call setVar("my_$name", procs[name])
}

echo 'global'
my_echo_a prefix
my_echo_b prefix

## STDOUT:
local
prefix a
prefix b

global
prefix a
prefix b
## END

#### with parseCommand() then io->eval(), in local scope

proc p {
  var result = {}
  for param in a b {
    var s = """
    proc echo_$param(prefix) {
      echo \$prefix $param
    }
    """
    var cmd = parseCommand(s)
    call io->eval(cmd)
  }

  echo_a prefix
  echo_b prefix
}

p

echo_a prefix

## status: 127
## STDOUT:
prefix a
prefix b
## END

#### with parseCommand() then io->eval(cmd, vars={out_dict: {}})

# This could take the place of evalToDict()?  But evalToDict() is useful in
# Hay?

func genProcs() {
  var vars = {out_dict: {}}
  for param in a b {
    var s = """
    proc echo_$param(prefix) {
      echo \$prefix $param
    }
    setvar out_dict.echo_$param = echo_$param
    """
    var cmd = parseCommand(s)
    call io->eval(cmd, vars=vars)
  }
  return (vars.out_dict)
}

var procs = genProcs()

var my_echo_a = procs.echo_a
var my_echo_b = procs.echo_b

my_echo_a prefix
my_echo_b prefix

## STDOUT:
prefix a
prefix b
## END

#### with evalToDict()

func genProcs() {
  var result = {}
  for param in a b {
    var s = """
    # This is defined locally
    proc echo_$param(prefix) {
      echo \$prefix $param
    }
    if false {
      = echo_$param
      var a = 42
      pp frame_vars_
    }
    """
    var cmd = parseCommand(s)

    var d = io->evalToDict(cmd)

    # accumulate
    setvar result["echo_$param"] = d["echo_$param"]
  }
  return (result)
}

var procs = genProcs()

var my_echo_a = procs.echo_a
var my_echo_b = procs.echo_b

my_echo_a prefix
my_echo_b prefix

## STDOUT:
prefix a
prefix b
## END


#### with runtime REFLECTION via __invoke__ - no parsing

# self is the first typed arg
proc p (prefix; self) {
  echo $prefix $[self.param]
}

# p is invoked with "self", which has self.param
var methods = Object(null, {__invoke__: p})

var procs = {}
for param in a b {
  setvar procs["echo_$param"] = Object(methods, {param: param})
}

var my_echo_a = procs.echo_a
var my_echo_b = procs.echo_b

if false {
  = my_echo_a
  = my_echo_b
  type -t my_echo_a
  type -t my_echo_b
}

# Maybe show an error if this is not value.Obj?
my_echo_a prefix
my_echo_b prefix

## STDOUT:
prefix a
prefix b
## END
