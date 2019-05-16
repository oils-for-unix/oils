#!/usr/bin/env bash

#### implicit for loop
# This is like "for i in $@".
func() {
  for i; do
    echo $i
  done
}
func 1 2 3
## STDOUT:
1
2
3
## END

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
## STDOUT: 
/home/bob/src
/home/bob/git
## END

#### Brace Expansion within Array
for i in -{a,b} {c,d}-; do
  echo $i
  done
## STDOUT: 
-a
-b
c-
d-
## END
## N-I dash STDOUT:
-{a,b}
{c,d}-
## END

#### using loop var outside loop
func() {
  for i in a b c; do
    echo $i
  done
  echo $i
}
func
## status: 0
## STDOUT:
a
b
c
c
## END

#### continue
for i in a b c; do
  echo $i
  if test $i = b; then
    continue
  fi
  echo $i
done
## status: 0
## STDOUT:
a
a
b
c
c
## END

#### break
for i in a b c; do
  echo $i
  if test $i = b; then
    break
  fi
done
## status: 0
## STDOUT:
a
b
## END

#### dynamic control flow (KNOWN INCOMPATIBILITY)
# hm would it be saner to make FATAL builtins called break/continue/etc.?
# On the other hand, this spits out errors loudly.
b=break
for i in 1 2 3; do
  echo $i
  $b
done
## STDOUT:
1
## END
## OK osh STDOUT:
1
2
3
## END
## OK osh status: 127

#### while in while condition
# This is a consequence of the grammar
while while true; do echo cond; break; done
do
  echo body
  break
done
## STDOUT:
cond
body
## END

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

#### bad arg to break
x=oops
while true; do 
  echo hi
  break $x
  sleep 0.1
done
## stdout: hi
## status: 1
## OK dash status: 2
## OK bash status: 128

#### too many args to continue
# OSH treats this as a parse error
for x in a b c; do
  echo $x
  # bash breaks rather than continue or fatal error!!!
  continue 1 2 3
done
echo --
## stdout-json: ""
## status: 2
## BUG bash STDOUT:
a
--
## END
## OK bash status: 0
## BUG dash/mksh/zsh STDOUT:
a
b
c
--
## END
## BUG dash/mksh/zsh status: 0
