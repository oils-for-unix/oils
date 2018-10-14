#!/usr/bin/env bash

#### implicit for loop
# This is like "for i in $@".
func() {
  for i; do
    echo $i
  done
}
func 1 2 3
## stdout-json: "1\n2\n3\n"

#### empty for loop (has "in")
set -- 1 2 3
for i in ; do
  echo $i
done
## stdout-json: ""

#### for loop with invalid identifier
# should be compile time error, but runtime error is OK too
for - in a b c; do
  echo hi
done
## stdout-json: ""
## status: 2
## OK bash/mksh status: 1
## BUG zsh stdout: hi
## BUG zsh status: 1

#### Tilde expansion within for loop
HOME=/home/bob
for name in ~/src ~/git; do
  echo $name
done
## stdout-json: "/home/bob/src\n/home/bob/git\n"

#### Brace Expansion within Array
for i in -{a,b} {c,d}-; do
  echo $i
  done
## stdout-json: "-a\n-b\nc-\nd-\n"
## N-I dash stdout-json: "-{a,b}\n{c,d}-\n"

#### using loop var outside loop
func() {
  for i in a b c; do
    echo $i
  done
  echo $i
}
func
## status: 0
## stdout-json: "a\nb\nc\nc\n"

#### continue
for i in a b c; do
  echo $i
  if test $i = b; then
    continue
  fi
  echo $i
done
## status: 0
## stdout-json: "a\na\nb\nc\nc\n"

#### break
for i in a b c; do
  echo $i
  if test $i = b; then
    break
  fi
done
## status: 0
## stdout-json: "a\nb\n"

#### while in while condition
# This is a consequence of the grammar
while while true; do echo cond; break; done
do
  echo body
  break
done
## stdout-json: "cond\nbody\n"

#### while in pipe
x=$(find spec/ | wc -l)
y=$(find spec/ | while read path; do
  echo $path
done | wc -l
)
test $x -eq $y
echo status=$?
## stdout: status=0

#### while in pipe with subshell
i=0
find . -maxdepth 1 -name INSTALL.txt -o -name LICENSE.txt | ( while read path; do
  i=$((i+1))
  #echo $i
done
echo $i )
## stdout: 2

#### until loop
# This is just the opposite of while?  while ! cond?
until false; do
  echo hi
  break
done
## stdout: hi

#### continue at top level
# zsh behaves with strict-control-flow!
if true; then
  echo one
  continue
  echo two
fi
## status: 0
## STDOUT:
one
two
## END
## OK zsh status: 1
## OK zsh STDOUT:
one
## END

#### continue in subshell
for i in $(seq 3); do
  echo "> $i"
  ( if true; then continue; fi; echo "Should not print" )
  echo ". $i"
done
## STDOUT:
> 1
. 1
> 2
. 2
> 3
. 3
## END
## BUG mksh STDOUT:
> 1
Should not print
. 1
> 2
Should not print
. 2
> 3
Should not print
. 3
## END
