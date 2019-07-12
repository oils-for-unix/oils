#!/usr/bin/env bash

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
  f
  echo "g: $g_var"
}
g
## stdout: g: f_mutation

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
