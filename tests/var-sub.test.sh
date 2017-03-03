#!/bin/bash

### String length
v=foo
echo ${#v}
# stdout: 3

### Substring
v=abcde
echo ${v:1:3}
# stdout: bcd
# N-I dash status: 2
# N-I dash stdout-json: ""

### Cannot take length of substring
# These are runtime errors, but we could make them parse time errors.
v=abcde
echo ${#v:1:3}
# status: 1
# N-I dash status: 0
# N-I dash stdout: 5

### Pattern replacement
v=abcde
echo ${v/c*/XX}
# stdout: abXX
# N-I dash status: 2
# N-I dash stdout-json: ""

### Remove smallest suffix
v=aabbccdd
echo ${v%c*}
# stdout: aabbc

### Remove longest suffix
v=aabbccdd
echo ${v%%c*}
# stdout: aabb

### Remove smallest prefix
v=aabbccdd
echo ${v#*b}
# stdout: bccdd

### Remove longest prefix
v=aabbccdd
echo ${v##*b}
# stdout: ccdd

### Default value when empty
empty=''
echo ${empty:-is empty}
# stdout: is empty

### Default value when unset
echo ${unset-is unset}
# stdout: is unset

### Assign default value when empty
empty=''
${empty:=is empty}
echo $empty
# stdout: is empty

### Assign default value when unset
${unset=is unset}
echo $unset
# stdout: is unset

### Alternative value when empty
v=foo
empty=''
echo ${v:+v is not empty} ${empty:+is not empty}
# stdout: v is not empty

### Alternative value when unset
v=foo
echo ${v+v is not unset} ${unset:+is not unset}
# stdout: v is not unset

### Error when empty
empty=''
${empty:?is empty}
# status: 1
# OK dash status: 2

### Error when unset
${unset?is empty}
# status: 1
# OK dash status: 2

### Error when unset
v=foo
echo ${v+v is not unset} ${unset:+is not unset}
# stdout: v is not unset

### String slice
foo=abcdefg
echo ${foo:1:3}
# stdout: bcd
# N-I dash status: 2
# N-I dash stdout-json: ""

### Negative string slice
foo=abcdefg
echo ${foo: -4:3}
# stdout: def
# N-I dash status: 2
# N-I dash stdout-json: ""

### String slice with math
# I think this is the $(()) language inside?
i=1
foo=abcdefg
echo ${foo: i-3-2 : i + 2}
# stdout: def
# N-I dash status: 2
# N-I dash stdout-json: ""

### Var ref with ${!a}
a=b
b=c
echo ref ${!a}
# Woah mksh has a completely different behavior -- var name, not var ref.
# stdout: ref c
# BUG mksh stdout: ref a
# N-I dash/zsh stdout-json: ""

### Bad var ref with ${!a}
#set -o nounset
a='bad var name'
echo ref ${!a}
# Woah even dash implements this!
# stdout-json: "ref\n"
# BUG mksh stdout: ref a
# N-I dash/zsh stdout-json: ""

### Local Var
# Oh this is interesting.  Local vars in a function are visible to the function
# it calls.  That is not how functions work!  Functions are supposed to take
# params.
f() {
  local f_var=5
  g
}
g() {
  local g_var=6
  echo INNER $f_var $g_var
}
f
echo "OUTER" $f_var $g_var
# stdout-json: "INNER 5 6\nOUTER\n"

### Nested ${} 
bar=ZZ
echo ${foo:-${bar}}
# stdout: ZZ

### Braced block inside ${}
# NOTE: This doesn't work in bash.  The nested {} aren't parsed.  It works in
# dash though!
# bash - line 1: syntax error near unexpected token `)'
# bash - line 1: `echo ${foo:-$({ which ls; })}'
# tag: bash-bug
echo ${foo:-$({ which ls; })}
# stdout: /bin/ls
# BUG bash stdout-json: ""
# BUG bash status: 2

### Assigning $@ to var
# dash doesn't like this -- says '2' bad variable name.
# NOTE: bash and mksh support array variables!  This is probably the
# difference.  Need to test array semantics!
func() {
  local v=$@
  argv.py $v
}
func 1 2 3
# stdout: ['1', '2', '3']
# BUG dash status: 2
# BUG dash stdout-json: ""

### Assigning "$@" to var
# dash doesn't like this -- says '2 3' bad variable name.
func() {
  local v="$@"
  argv.py $v
}
func 1 '2 3'
# stdout: ['1', '2', '3']
# BUG dash status: 2
# BUG dash stdout-json: ""

### Assigning "$@" to var, then showing it quoted
# dash doesn't like this -- says '2 3' bad variable name.
func() {
  local v="$@"
  argv.py "$v"
}
func 1 '2 3'
# stdout: ['1 2 3']
# BUG dash status: 2
# BUG dash stdout-json: ""

### Filename redirect with "$@" 
# bash - ambiguous redirect -- yeah I want this error
#   - But I want it at PARSE time?  So is there a special DollarAtPart?
#     MultipleArgsPart?
# mksh - tries to create '_tmp/var-sub1 _tmp/var-sub2'
# dash - tries to create '_tmp/var-sub1 _tmp/var-sub2'
func() {
  echo hi > "$@"
}
func _tmp/var-sub1 _tmp/var-sub2
# status: 1
# OK dash status: 2

### Filename redirect with split word
# bash - runtime error, ambiguous redirect
# mksh and dash - they will NOT apply word splitting after redirect, and write
# to '_tmp/1 2'
# Stricter behavior seems fine.
foo='_tmp/1 2'
rm '_tmp/1 2'
echo hi > $foo
test -f '_tmp/1 2' && cat '_tmp/1 2'
# status: 1
# OK dash/mksh status: 0
# OK dash/mksh stdout: hi

### Descriptor redirect to bad "$@"
# All of them give errors:
# dash - bad fd number, parse error?
# bash - ambiguous redirect
# mksh - illegal file scriptor name
set -- '2 3' 'c d'
echo hi 1>& "$@"
# status: 2
# OK bash/mksh status: 1

### Here doc with bad "$@" delimiter
# bash - syntax error
# dash - syntax error: end of file unexpected
# mksh - runtime error: here document unclosed
#
# What I want is syntax error: bad delimiter!
#
# This means that "$@" should be part of the parse tree then?  Anything that
# involves more than one token.
func() {
  cat << "$@"
hi
1 2
}
func 1 2
# status: 2
# stdout-json: ""
# OK mksh status: 1


