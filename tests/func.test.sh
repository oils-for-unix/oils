#!/bin/bash

### Locals don't leak
f() {
  local f_var=f_var
}
f
echo $f_var
# stdout:

### Globals leak
f() {
  f_var=f_var
}
f
echo $f_var
# stdout: f_var

### Return statement
f() {
  echo one
  return 42
  echo two
}
f
# stdout: one
# status: 42

### Return at top level is error
return
echo bad
# N-I dash/mksh status: 0
# N-I bash status: 0
# N-I bash stdout: bad
# status: 1
# stdout-json: ""

### Dynamic Scope
f() {
  echo $g_var
}
g() {
  local g_var=g_var
  f
}
g
# stdout: g_var


