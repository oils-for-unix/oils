#!/usr/bin/env bash
#
# Constructs borrowed from ksh.  Hm I didn't realize zsh also implements these!
# mksh implements most too.

#### C-style for loop
n=10
for ((a=1; a <= n ; a++))  # Double parentheses, and naked 'n'
do
  if test $a = 3; then
    continue
  fi
  if test $a = 6; then
    break
  fi
  echo $a
done
## status: 0
## STDOUT:
1
2
4
5
## END

#### For loop with and without semicolon
for ((a=1; a <= 3; a++)); do
  echo $a
done
for ((a=1; a <= 3; a++)) do
  echo $a
done
## status: 0
## STDOUT:
1
2
3
1
2
3
## END

#### Accepts { } syntax too
for ((a=1; a <= 3; a++)) {
  echo $a
}
## STDOUT:
1
2
3
## END

#### Empty init
i=1
for ((  ;i < 4;  i++ )); do
  echo $i
done
## status: 0
## STDOUT:
1
2
3
## END

#### Empty init and cond
i=1
for ((  ; ;  i++ )); do
  if test $i = 4; then
    break
  fi
  echo $i
done
## status: 0
## STDOUT:
1
2
3
## END

#### Infinite loop with ((;;))
a=1
for ((  ;  ;  )); do
  if test $a = 4; then
    break
  fi
  echo $((a++))
done
## status: 0
## STDOUT:
1
2
3
## END
