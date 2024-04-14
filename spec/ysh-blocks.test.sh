#### cd with block
shopt -s ysh:all

const saved = "$PWD"

# OLDPWD is NOT defined
cd / { echo $PWD; echo OLDPWD=${OLDPWD:-} }; echo done

if ! test "$saved" = $PWD; then
  echo FAIL
fi

cd /tmp {
  write PWD=$PWD
  write --sep ' ' pwd builtin: $(pwd)
}

if ! test "$saved" = $PWD; then
  echo FAIL
fi

## STDOUT:
/
OLDPWD=
done
PWD=/tmp
pwd builtin: /tmp
## END

#### cd with block: fatal error in block
shopt -s oil:all
cd / {
  echo one
  false
  echo two
}
## status: 1
## STDOUT:
one
## END


#### cd with block: return in block
shopt -s oil:all
f() {
  cd / {
    echo one
    return
    echo two
  }
  echo 'end func'
}
f
## STDOUT:
one
end func
## END

#### cd with block: break in block
shopt -s oil:all
f() {
  cd / {
    echo one
    for i in 1 2; do
      echo $i
      break  # break out of loop
    done

    break  # break out of block isn't valid
    echo two
  }
  echo end func
}
f
## status: 1
## STDOUT:
one
1
## END

#### cd with block exits with status 0
shopt -s ysh:all
cd / {
  echo block

  # This return value is ignored.
  # Or maybe this should be a runtime error?
  return 1
}
echo status=$?
## STDOUT:
block
status=0
## END

#### block doesn't have its own scope
shopt -s ysh:all
var x = 1
echo "x=$x"
cd / {
  #set y = 5  # This would be an error because set doesn't do dynamic lookup
  var x = 42
  echo "x=$x"
}
echo "x=$x"
## STDOUT:
x=1
x=42
x=42
## END

#### redirects allowed in words, typed args, and after block
shopt -s ysh:upgrade

rm -f out
touch out

cd /tmp >>out {
  echo 1 $PWD
}

cd /tmp >>out (; ; ^(echo 2 $PWD))

cd /tmp (; ; ^(echo 3 $PWD)) >>out

cd /tmp {
  echo 4 $PWD
} >> out

cat out

## STDOUT:
1 /tmp
2 /tmp
3 /tmp
4 /tmp
## END

#### block literal in expression mode: ^(echo $PWD)
shopt -s oil:all

const myblock = ^(echo $PWD | wc -l)
eval (myblock)

const b2 = ^(echo one; echo two)
eval (b2)

## STDOUT:
1
one
two
## END

#### block arg as typed expression

shopt -s oil:all

# literal
cd /tmp (; ; ^(echo $PWD))

const myblock = ^(echo $PWD)
cd /tmp (; ; myblock)

## STDOUT:
/tmp
/tmp
## END

#### Pass invalid typed args

cd /tmp (42)  # should be a block
## status: 3

#### Pass too many typed args

cd /tmp (1, 2)
## status: 3

#### 'builtin' and 'command' with block
shopt --set oil:upgrade
builtin cd / {
  echo "builtin $PWD"
}
command cd / {
  echo "command $PWD"
}
## STDOUT:
builtin /
command /
## END


#### Consistency: Control Flow and Blocks
shopt --set parse_brace

# "Invalid control flow at top level"
eval '
  cd / {
    echo cd
    break
  }
'
echo cd no loop $?

# warning: "Unexpected control flow in block" (strict_control_flow)
eval '
while true {
  cd / {
    echo cd
    break
  }
}
'
echo cd loop $?

eval '
while true {
  shopt --unset errexit {
    echo shopt
    continue
  }
}
'
echo shopt continue $?

eval '
while true {
  shvar FOO=foo {
    echo shvar
    continue
  }
}
'
echo shvar continue $?


eval '
while true {
  try {
    echo try
    break
  }
}
'
echo try break $?

## STDOUT:
cd
cd no loop 0
cd
cd loop 1
shopt
shopt continue 1
shvar
shvar continue 1
try
try break 1
## END

#### Consistency: Exit Status and Blocks
shopt --set parse_brace

cd / {
  false 
}
echo cd=$?

shopt --unset errexit {
  false
}
echo shopt=$?

shvar FOO=foo {
  echo "  FOO=$FOO"
  false
}
echo shvar=$?

try {
  false
}
echo try=$?

## STDOUT:
cd=0
shopt=0
  FOO=foo
shvar=0
try=0
## END

#### Consistency: Unwanted Blocks Are Errors
shopt --set parse_brace

true { echo BAD }
echo true $?

false ( 42, 43 )
echo false $?

echo { echo BAD }
echo echo block $?

echo ( 42, 43 )
echo echo args $?

command echo 'command block' { echo BAD }
echo command echo $?

builtin echo 'builtin block' { echo BAD }
echo builtin echo $?

pushd $TMP { echo BAD }
echo pushd $?

## STDOUT:
true 2
false 2
echo block 2
echo args 2
command echo 2
builtin echo 2
pushd 2
## END

#### Block with Bare Assignments

# oil:all has parse_equals
# is there any way to turn on parse_equals only in config blocks?
# but we don't know what's a block ahead of time
# I think we would have to check at runtime.  Look at VarChecker

shopt --set oil:all

proc Rule(s ; ; ; b) {
  echo "rule $s"
}

proc myrules(name) { 
  Rule $name-python { 
    kind = 'python'
  }

  Rule $name-cc {
    kind = 'cc'  # should NOT conflict
  }
}

myrules foo
myrules bar

## STDOUT:
rule foo-python
rule foo-cc
rule bar-python
rule bar-cc
## END

#### Proc that doesn't take a block
shopt --set parse_brace parse_proc parse_paren

proc task(name ; ; ; b = null) {
  echo "task name=$name"
  if (b) {
    eval (b)
    return 33
  } else {
    echo 'no block'
    return 44
  }
}

task spam
echo status=$?

echo

task foo {
  echo 'running'
  echo 'block'
}
echo status=$?

## STDOUT:
task name=spam
no block
status=44

task name=foo
running
block
status=33
## END

