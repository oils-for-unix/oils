
#### Locals don't leak
f() {
  local f_var=f_var
}
f
echo $f_var
## stdout:

#### Globals leak
f() {
  f_var=f_var
}
f
echo $f_var
## stdout: f_var

#### Return statement
f() {
  echo one
  return 42
  echo two
}
f
## stdout: one
## status: 42

#### Dynamic Scope
f() {
  echo $g_var
}
g() {
  local g_var=g_var
  f
}
g
## stdout: g_var

#### Dynamic Scope Mutation (wow this is bad)
f() {
  g_var=f_mutation
}
g() {
  local g_var=g_var
  echo "g_var=$g_var"
  f
  echo "g_var=$g_var"
}
g
echo g_var=$g_var
## STDOUT:
g_var=g_var
g_var=f_mutation
g_var=
## END

#### Assign local separately
f() {
  local f
  f='new-value'
  echo "[$f]"
}
f
## stdout: [new-value]
## status: 0

#### Assign a local and global on same line
myglobal=
f() {
  local mylocal
  mylocal=L myglobal=G
  echo "[$mylocal $myglobal]"
}
f
echo "[$mylocal $myglobal]"
## stdout-json: "[L G]\n[ G]\n"
## status: 0

#### Return without args gives previous
f() {
  ( exit 42 )
  return
}
f
echo status=$?
## STDOUT:
status=42
## END

#### return "" (a lot of disagreement)
f() {
  echo f
  return ""
}

f
echo status=$?
## STDOUT:
f
status=0
## END
## status: 0

## OK dash status: 2
## OK dash STDOUT:
f
## END

## BUG mksh STDOUT:
f
status=1
## END

## BUG bash STDOUT:
f
status=2
## END

#### return $empty
f() {
  echo f
  empty=
  return $empty
}

f
echo status=$?
## STDOUT:
f
status=0
## END

#### Subshell function

f() ( return 42; )
# BUG: OSH raises invalid control flow!  I think we should just allow 'return'
# but maybe not 'break' etc.
g() ( return 42 )
# bash warns here but doesn't cause an error
# g() ( break )

f
echo status=$?
g
echo status=$?

## STDOUT:
status=42
status=42
## END

#### Functions can be named func or proc
func() { echo f; }
proc() { echo p; }

func
proc
## STDOUT:
f
p
## END
