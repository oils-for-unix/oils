#!/bin/bash

### implicit for loop
# This is like "for i in $@".
func() {
  for i; do
    echo $i
  done
}
func 1 2 3
# stdout-json: "1\n2\n3\n"

### empty for loop (has "in")
set -- 1 2 3
for i in ; do
  echo $i
done
# stdout-json: ""
# BUG mksh stdout-json: "1\n2\n3\n"

### for loop with invalid identifier
# should be compile time error, but runtime error is OK too
for - in a b c; do
  echo hi
done
# stdout-json: ""
# status: 2
# OK bash/mksh status: 1

### Tilde expansion within for loop
HOME=/home/bob
for name in ~/src ~/git; do
  echo $name
done
# stdout-json: "/home/bob/src\n/home/bob/git\n"

### Brace Expansion within Array
for i in -{a,b} {c,d}-; do
  echo $i
  done
# stdout-json: "-a\n-b\nc-\nd-\n"
# N-I dash stdout-json: "-{a,b}\n{c,d}-\n"

### using loop var outside loop
func() {
  for i in a b c; do
    echo $i
  done
  echo $i
}
func
# status: 0
# stdout-json: "a\nb\nc\nc\n"

### continue
for i in a b c; do
  echo $i
  if test $i = b; then
    continue
  fi
  echo $i
done
# status: 0
# stdout-json: "a\na\nb\nc\nc\n"

### break
for i in a b c; do
  echo $i
  if test $i = b; then
    break
  fi
done
# status: 0
# stdout-json: "a\nb\n"

### continue at top level is error
# NOTE: bash and mksh both print warnings, but don't exit with an error.
continue
echo bad
# N-I bash/dash/mksh status: 0
# N-I bash/dash/mksh stdout: bad
# stdout-json: ""
# status: 1

### break at top level is error
break
echo bad
# N-I bash/dash/mksh status: 0
# N-I bash/dash/mksh stdout: bad
# stdout-json: ""
# status: 1

### while in while condition
# This is a consequence of the grammar
while while true; do echo cond; break; done
do
  echo body
  break
done
# stdout-json: "cond\nbody\n"

### while in pipe
i=0
find tests/ | while read $path; do
  i=$((i+1))
  #echo $i
done
# This Because while loop was in a subshell
echo $i
# stdout: 0

### while in pipe with subshell
i=0
find bin/ -type l | ( while read path; do
  i=$((i+1))
  #echo $i
done
echo $i )
# stdout: 5

### until loop
# This is just the opposite of while?  while ! cond?
until false; do
  echo hi
  break
done
# stdout: hi
